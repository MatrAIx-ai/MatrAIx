"""End-to-end sampling behavior for PersonaSynthesisService (needs numpy)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

np = pytest.importorskip("numpy")

from backend.service.persona_synthesis_service import (  # noqa: E402
    PersonaSynthesisService,
    SynthesisValidationError,
)
from backend.tests.test_synthesis_sampling_contract import (  # noqa: E402
    DIMS_FIXTURE,
    SAMPLER_GRAPH,
)


@pytest.fixture()
def service(tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(SAMPLER_GRAPH), encoding="utf-8")
    dims_path = tmp_path / "dims.json"
    dims_path.write_text(json.dumps(DIMS_FIXTURE), encoding="utf-8")
    return PersonaSynthesisService(graph_path, dims_path=dims_path)


@pytest.fixture()
def synthesis_client(client, app, service):
    app.state.services.persona_synthesis = service
    return client


def test_pin_clamps_and_shifts_downstream(service):
    body = service.sample(n=200, seed=1, pins={"a": "a1"})
    assert all(p["a"] == "a1" for p in body["personas"])
    freq_b1 = body["marginals"]["b"]["freqs"][1]
    assert freq_b1 == pytest.approx(0.95, abs=0.06)
    assert body["flags"]["helperPins"] == []


def test_marginals_shape_and_normalization(service):
    body = service.sample(n=50, seed=2, compare_baseline=False)
    assert body["baselinePersonas"] is None
    assert body["baselineMarginals"] is None
    marginal = body["marginals"]["a"]
    assert marginal["label"] == "A"
    assert marginal["values"] == ["a0", "a1"]
    assert sum(marginal["freqs"]) == pytest.approx(1.0, abs=1e-6)
    assert "h" not in body["marginals"]  # emit-only
    assert "h" not in body["personas"][0]


def test_baseline_ignores_pins_and_overrides(service):
    body = service.sample(
        n=200,
        seed=3,
        pins={"a": "a1"},
        overrides={"categoryScales": {"Demo": 0.0}},
    )
    assert body["baselineMarginals"]["a"]["freqs"][1] == pytest.approx(0.2, abs=0.08)
    plain = service.sample(n=200, seed=3, compare_baseline=False)
    assert body["baselinePersonas"] == plain["personas"]


def test_category_scale_alone_shifts_downstream_marginal(service):
    body = service.sample(
        n=200,
        seed=13,
        overrides={"categoryScales": {"Demo": 0.0}},
    )
    assert body["marginals"]["b"]["freqs"][1] == pytest.approx(0.5, abs=0.08)
    assert body["baselineMarginals"]["b"]["freqs"][1] == pytest.approx(0.23, abs=0.08)


def test_same_seed_is_deterministic(service):
    first = service.sample(n=20, seed=9, pins={"a": "a1"})
    second = service.sample(n=20, seed=9, pins={"a": "a1"})
    assert first["personas"] == second["personas"]


def test_helper_pin_is_flagged(service):
    body = service.sample(n=5, seed=1, pins={"h": "v1"})
    assert body["flags"]["helperPins"] == ["h"]


def test_sampler_cache_reuses_compiled_plans(service):
    service.sample(n=5, seed=1, overrides={"categoryScales": {"Demo": 2.0}})
    assert len(service._sampler_cache) == 2  # baseline + adjusted
    service.sample(n=5, seed=2, overrides={"categoryScales": {"Demo": 2.0}})
    assert len(service._sampler_cache) == 2  # cache hit, no rebuild


def test_sampler_cache_single_flights_same_key(service, monkeypatch):
    started = Event()
    release = Event()
    sentinel = object()
    calls = 0

    def fake_build(*args, **kwargs):
        nonlocal calls
        calls += 1
        started.set()
        assert release.wait(timeout=2)
        return sentinel

    monkeypatch.setattr(service, "_build_sampler", fake_build)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service._sampler_for, 1.0, {}, {}, {})
        assert started.wait(timeout=2)
        second = pool.submit(service._sampler_for, 1.0, {}, {}, {})
        release.set()
        assert first.result(timeout=2) is sentinel
        assert second.result(timeout=2) is sentinel
    assert calls == 1


def test_effective_config_echo(service):
    body = service.sample(n=5, seed=4, gamma_scale=1.5, pins={"a": "a0"})
    config = body["effectiveConfig"]
    assert config["n"] == 5 and config["seed"] == 4
    assert config["gammaScale"] == 1.5
    assert config["pins"] == {"a": "a0"}


@pytest.mark.parametrize(
    ("kwargs", "key"),
    [
        ({"gamma_scale": True}, "gammaScale"),
        (
            {"overrides": {"edgeWeights": {"a->b": True}}},
            "overrides.edgeWeights.a->b",
        ),
        (
            {"overrides": {"nodePriors": {"a": [True, 0.0]}}},
            "overrides.nodePriors.a",
        ),
        (
            {"overrides": {"categoryScales": {"Demo": True}}},
            "overrides.categoryScales.Demo",
        ),
        ({"overrides": {"unknown": {}}}, "overrides.unknown"),
        ({"overrides": []}, "overrides"),
        ({"compare_baseline": "false"}, "compareBaseline"),
    ],
)
def test_sample_rejects_malformed_recipe_inputs(service, kwargs, key):
    with pytest.raises(SynthesisValidationError) as exc_info:
        service.sample(n=1, seed=7, **kwargs)

    assert exc_info.value.key == key


PAIRWISE_FLOAT32_MESSAGE = (
    "scaled pairwise evidence for a->b cannot be represented in float32"
)


@pytest.mark.parametrize(
    ("payload", "key"),
    [
        (
            {"overrides": {"edgeWeights": {"a->b": 1e100}}},
            "overrides.edgeWeights.a->b",
        ),
        (
            {"overrides": {"categoryScales": {"Demo": 1e100}}},
            "overrides.categoryScales.Demo",
        ),
        (
            {
                "overrides": {
                    "edgeWeights": {"a->b": 1e200},
                    "categoryScales": {"Demo": 1e200},
                }
            },
            "overrides.edgeWeights.a->b",
        ),
        ({"gammaScale": 1e100}, "gammaScale"),
    ],
)
def test_unrepresentable_evidence_maps_to_exact_422(synthesis_client, payload, key):
    response = synthesis_client.post(
        "/api/synthesis/sample",
        json={"n": 1, "compareBaseline": False, **payload},
    )

    assert response.status_code == 422
    assert response.json() == {"message": PAIRWISE_FLOAT32_MESSAGE, "key": key}


@pytest.mark.parametrize(
    ("overrides", "key"),
    [
        (
            {"edgeWeights": {"a->b": 1e100}},
            "overrides.edgeWeights.a->b",
        ),
        (
            {"categoryScales": {"Demo": 1e100}},
            "overrides.categoryScales.Demo",
        ),
    ],
)
def test_unrepresentable_pairwise_evidence_reports_explicit_field(
    service, overrides, key
):
    with pytest.raises(SynthesisValidationError) as exc_info:
        service.sample(
            n=1,
            seed=7,
            overrides=overrides,
            compare_baseline=False,
        )

    assert {"message": str(exc_info.value), "key": exc_info.value.key} == {
        "message": PAIRWISE_FLOAT32_MESSAGE,
        "key": key,
    }


def test_edge_key_precedes_category_key_for_composite_overflow(service):
    with pytest.raises(SynthesisValidationError) as exc_info:
        service.sample(
            n=1,
            seed=7,
            overrides={
                "edgeWeights": {"a->b": 1e200},
                "categoryScales": {"Demo": 1e200},
            },
            compare_baseline=False,
        )

    assert {"message": str(exc_info.value), "key": exc_info.value.key} == {
        "message": PAIRWISE_FLOAT32_MESSAGE,
        "key": "overrides.edgeWeights.a->b",
    }


def test_gamma_overflow_in_full_cpt_reports_gamma_key(tmp_path):
    graph = json.loads(json.dumps(SAMPLER_GRAPH))
    graph["full_cpts"] = [
        {
            "target": "b",
            "parents": ["a"],
            "cpt_weight": 1.0,
            "replace_pairwise_parent_edges": True,
            "rows": [
                {
                    "parent_assignment": {"a": "a0"},
                    "distribution": {"b0": 0.95, "b1": 0.05},
                },
                {
                    "parent_assignment": {"a": "a1"},
                    "distribution": {"b0": 0.05, "b1": 0.95},
                },
            ],
        }
    ]
    graph_path = tmp_path / "full-cpt-graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    full_cpt_service = PersonaSynthesisService(graph_path)

    with pytest.raises(SynthesisValidationError) as exc_info:
        full_cpt_service.sample(
            n=1,
            seed=7,
            gamma_scale=1e100,
            compare_baseline=False,
        )

    assert {"message": str(exc_info.value), "key": exc_info.value.key} == {
        "message": (
            "scaled full-CPT evidence for b cannot be represented in float32"
        ),
        "key": "gammaScale",
    }


def test_failed_compilation_is_not_cached_and_safe_retry_succeeds(service):
    overrides = {"edgeWeights": {"a->b": 1e100}}
    for _ in range(2):
        with pytest.raises(SynthesisValidationError):
            service.sample(
                n=1,
                seed=7,
                overrides=overrides,
                compare_baseline=False,
            )
        assert service._sampler_cache == {}
        assert service._sampler_inflight == {}

    body = service.sample(
        n=1,
        seed=7,
        overrides={"edgeWeights": {"a->b": 1.0}},
        compare_baseline=False,
    )
    assert len(body["personas"]) == 1
    assert len(service._sampler_cache) == 1
    assert service._sampler_inflight == {}

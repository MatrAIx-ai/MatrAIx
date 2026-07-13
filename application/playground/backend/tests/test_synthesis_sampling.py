"""End-to-end sampling behavior for PersonaSynthesisService (needs numpy)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

np = pytest.importorskip("numpy")

from backend.service.persona_synthesis_service import PersonaSynthesisService  # noqa: E402
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

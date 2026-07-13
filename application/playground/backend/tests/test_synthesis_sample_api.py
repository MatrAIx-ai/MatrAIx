"""Route contracts for POST /api/synthesis/sample and /render (no numpy)."""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from backend.service.persona_synthesis_service import (
    PersonaSynthesisService,
    SamplerUnavailableError,
)
from backend.tests.test_synthesis_sampling_contract import DIMS_FIXTURE, SAMPLER_GRAPH


@pytest.fixture()
def synthesis_client(client, app, tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(SAMPLER_GRAPH), encoding="utf-8")
    dims_path = tmp_path / "dims.json"
    dims_path.write_text(json.dumps(DIMS_FIXTURE), encoding="utf-8")
    app.state.services.persona_synthesis = PersonaSynthesisService(
        graph_path, dims_path=dims_path
    )
    return client


def _sample_payload() -> Dict[str, Any]:
    return {
        "personas": [{"a": "a1"}],
        "marginals": {
            "a": {
                "label": "A",
                "values": ["a0", "a1"],
                "freqs": [0.0, 1.0],
            }
        },
        "baselinePersonas": None,
        "baselineMarginals": None,
        "effectiveConfig": {
            "n": 1,
            "seed": 42,
            "gammaScale": 1.0,
            "pins": {},
            "overrides": {},
        },
        "flags": {"helperPins": []},
    }


def test_sample_validation_maps_to_422_with_key(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/sample", json={"n": 5, "pins": {"zz": "a0"}}
    )

    assert response.status_code == 422
    assert response.json() == {
        "message": "unknown pinned node: zz",
        "key": "pins.zz",
    }


def test_sample_n_bounds_enforced_by_schema(synthesis_client):
    response = synthesis_client.post("/api/synthesis/sample", json={"n": 500})

    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == "n"


@pytest.mark.parametrize("seed", [-1, 9_007_199_254_740_992])
def test_seed_bounds_map_to_named_schema_error(synthesis_client, seed):
    response = synthesis_client.post(
        "/api/synthesis/sample", json={"n": 5, "seed": seed}
    )

    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == "seed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n", True),
        ("n", 1.0),
        ("n", "1"),
        ("seed", True),
        ("seed", 1.0),
        ("seed", "1"),
    ],
)
def test_sample_integer_fields_reject_coercion(
    synthesis_client, monkeypatch, field, value
):
    monkeypatch.setattr(
        PersonaSynthesisService,
        "sample",
        lambda self, **kwargs: _sample_payload(),
    )

    response = synthesis_client.post("/api/synthesis/sample", json={field: value})

    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == field


def test_nested_schema_error_maps_to_owning_override_key(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/sample",
        json={"overrides": {"nodePriors": {"a": [0.5, "bad"]}}},
    )

    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == "overrides.nodePriors.a"


def test_nested_schema_key_preserves_recipe_entry_named_body(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/sample",
        json={"overrides": {"nodePriors": {"body": [0.5, "bad"]}}},
    )

    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == "overrides.nodePriors.body"


def test_malformed_json_maps_to_body_validation_key(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/sample",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == "body"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n", 1),
        ("n", 200),
        ("seed", 0),
        ("seed", 9_007_199_254_740_991),
    ],
)
def test_sample_integer_boundaries_are_inclusive(
    synthesis_client, monkeypatch, field, value
):
    captured = {}

    def fake_sample(self, **kwargs):
        captured.update(kwargs)
        return _sample_payload()

    monkeypatch.setattr(PersonaSynthesisService, "sample", fake_sample)

    response = synthesis_client.post("/api/synthesis/sample", json={field: value})

    assert response.status_code == 200
    assert captured[field] == value


def test_sample_route_wiring(synthesis_client, monkeypatch):
    captured = {}

    def fake_sample(self, **kwargs):
        captured.update(kwargs)
        return _sample_payload()

    monkeypatch.setattr(PersonaSynthesisService, "sample", fake_sample)
    response = synthesis_client.post(
        "/api/synthesis/sample",
        json={
            "n": 1,
            "overrides": {"categoryScales": {"Demo": 2.0}},
            "compareBaseline": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["personas"] == [{"a": "a1"}]
    assert captured["overrides"]["categoryScales"] == {"Demo": 2.0}
    assert captured["compare_baseline"] is False


def test_sampler_unavailable_maps_to_503(synthesis_client, monkeypatch):
    def raise_unavailable(self, *args, **kwargs):
        raise SamplerUnavailableError("sampling requires numpy")

    monkeypatch.setattr(PersonaSynthesisService, "_build_sampler", raise_unavailable)
    response = synthesis_client.post("/api/synthesis/sample", json={"n": 1})

    assert response.status_code == 503
    assert response.json() == {"detail": "sampling requires numpy"}


def test_render_endpoint(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/render", json={"attributes": {"b": "b0"}}
    )

    assert response.status_code == 200
    assert response.json() == {"text": "Interests: their b is b0."}


def test_render_schema_error_uses_synthesis_validation_envelope(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/render", json={"attributes": []}
    )

    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == "attributes"


def test_existing_synthesis_browse_validation_keeps_default_envelope(
    synthesis_client,
):
    response = synthesis_client.get(
        "/api/synthesis/graph/subgraph", params={"node": "a", "up": 9}
    )

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}

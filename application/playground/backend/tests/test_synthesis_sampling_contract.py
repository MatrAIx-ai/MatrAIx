"""Validation + render contracts for PersonaSynthesisService.sample/render_text.

Everything here runs WITHOUT numpy: validation raises before the sampler is
imported, and the renderer is stdlib-only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

import pytest

from backend.service.persona_synthesis_service import (
    PersonaSynthesisService,
    SynthesisValidationError,
)

SAMPLER_GRAPH = {
    "nodes": [
        {"id": "a", "label": "A", "category": "Demo", "values": ["a0", "a1"], "prior": [0.8, 0.2]},
        {"id": "b", "label": "B", "category": "Demo", "values": ["b0", "b1"], "prior": [0.5, 0.5]},
        {"id": "h", "label": "Helper", "category": "Latent", "emit": False, "values": ["v0", "v1"], "prior": [0.5, 0.5]},
    ],
    "directed_proposal_edges": [
        {
            "source": "a",
            "target": "b",
            "edge_weight": 1.0,
            "cpd": {
                "type": "pairwise_conditional_matrix",
                "source_values": ["a0", "a1"],
                "target_values": ["b0", "b1"],
                "P_target_given_source": [[0.95, 0.05], [0.05, 0.95]],
            },
        },
    ],
    "proposal_view": {"topological_order": ["a", "h", "b"]},
}

DIMS_FIXTURE = {
    "dimensions": [
        {"id": "a", "label": "A", "category": "Demographic: Core", "values": ["a0", "a1"]},
        {"id": "b", "label": "B", "category": "Interests: Food", "values": ["b0", "b1"]},
    ]
}


@pytest.fixture()
def service(tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(SAMPLER_GRAPH), encoding="utf-8")
    dims_path = tmp_path / "dims.json"
    dims_path.write_text(json.dumps(DIMS_FIXTURE), encoding="utf-8")
    return PersonaSynthesisService(graph_path, dims_path=dims_path)


def expect_key(callable_, key):
    with pytest.raises(SynthesisValidationError) as excinfo:
        callable_()
    assert excinfo.value.key == key


def test_unknown_pin_node(service):
    expect_key(lambda: service.sample(n=5, seed=1, pins={"zz": "a0"}), "pins.zz")


def test_unknown_pin_value(service):
    expect_key(lambda: service.sample(n=5, seed=1, pins={"a": "nope"}), "pins.a")


def test_bad_edge_key_format(service):
    expect_key(
        lambda: service.sample(n=5, seed=1, overrides={"edgeWeights": {"a=>b": 1.5}}),
        "overrides.edgeWeights.a=>b",
    )


def test_unknown_edge(service):
    expect_key(
        lambda: service.sample(n=5, seed=1, overrides={"edgeWeights": {"b->a": 1.5}}),
        "overrides.edgeWeights.b->a",
    )


def test_negative_edge_factor(service):
    expect_key(
        lambda: service.sample(n=5, seed=1, overrides={"edgeWeights": {"a->b": -2}}),
        "overrides.edgeWeights.a->b",
    )


def test_unknown_category(service):
    expect_key(
        lambda: service.sample(n=5, seed=1, overrides={"categoryScales": {"Nope": 2.0}}),
        "overrides.categoryScales.Nope",
    )


def test_prior_length_mismatch(service):
    expect_key(
        lambda: service.sample(n=5, seed=1, overrides={"nodePriors": {"a": [1.0]}}),
        "overrides.nodePriors.a",
    )


def test_prior_all_zero_mass(service):
    expect_key(
        lambda: service.sample(n=5, seed=1, overrides={"nodePriors": {"a": [0.0, 0.0]}}),
        "overrides.nodePriors.a",
    )


def test_n_out_of_bounds(service):
    expect_key(lambda: service.sample(n=0, seed=1), "n")
    expect_key(lambda: service.sample(n=201, seed=1), "n")


@pytest.mark.parametrize(
    "n",
    [True, 1.9, "5", object(), float("inf")],
    ids=["bool", "float", "string", "object", "infinity"],
)
def test_n_requires_a_strict_integer(service, n):
    expect_key(lambda: service.sample(n=n, seed=1), "n")


def test_seed_out_of_bounds(service):
    expect_key(lambda: service.sample(n=5, seed=-1), "seed")
    expect_key(
        lambda: service.sample(n=5, seed=9_007_199_254_740_992),
        "seed",
    )


def test_render_text_uses_dims(service):
    body = service.render_text({"b": "b0"})
    assert body == {"text": "Interests: their b is b0."}


def test_huge_edge_factor_reports_field_key(service):
    expect_key(
        lambda: service.sample(
            n=5,
            seed=1,
            overrides={"edgeWeights": {"a->b": 10**400}},
        ),
        "overrides.edgeWeights.a->b",
    )


def test_huge_category_scale_reports_field_key(service):
    expect_key(
        lambda: service.sample(
            n=5,
            seed=1,
            overrides={"categoryScales": {"Demo": 10**400}},
        ),
        "overrides.categoryScales.Demo",
    )


def test_huge_prior_weight_reports_field_key(service):
    expect_key(
        lambda: service.sample(
            n=5,
            seed=1,
            overrides={"nodePriors": {"a": [10**400, 1]}},
        ),
        "overrides.nodePriors.a",
    )


def test_overflowing_prior_total_reports_field_key(service):
    expect_key(
        lambda: service.sample(
            n=5,
            seed=1,
            overrides={"nodePriors": {"a": [1.5e308, 1e308]}},
        ),
        "overrides.nodePriors.a",
    )


def test_backend_and_renderer_import_when_numpy_is_blocked():
    code = textwrap.dedent(
        """
        import builtins
        real_import = builtins.__import__
        def blocked(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "numpy" or name.startswith("numpy."):
                raise ModuleNotFoundError("numpy blocked by contract test")
            return real_import(name, globals, locals, fromlist, level)
        builtins.__import__ = blocked
        import backend.api.app
        from backend.service.persona_synthesis_service import PersonaSynthesisService
        from persona.synthesis.render import render
        assert render({}, {}) == ""
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

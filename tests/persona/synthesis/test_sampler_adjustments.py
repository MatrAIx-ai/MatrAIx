"""Pins and overrides for PersonaForwardSampler (Synthesis Studio Phase 2)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from persona.synthesis.sampler import PersonaForwardSampler, SamplerOverrides, SamplingConfig

SAMPLER_GRAPH = {
    "nodes": [
        {"id": "a", "label": "A", "category": "Demo", "values": ["a0", "a1"], "prior": [0.5, 0.5]},
        {"id": "b", "label": "B", "category": "Demo", "values": ["b0", "b1"], "prior": [0.5, 0.5]},
        {"id": "c", "label": "C", "category": "Health", "values": ["c0", "c1"], "prior": [0.5, 0.5]},
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
        {
            "source": "b",
            "target": "c",
            "edge_weight": 1.0,
            "cpd": {
                "type": "pairwise_conditional_matrix",
                "source_values": ["b0", "b1"],
                "target_values": ["c0", "c1"],
                "P_target_given_source": [[0.9, 0.1], [0.1, 0.9]],
            },
        },
    ],
    "proposal_view": {"topological_order": ["a", "b", "c"]},
}


def write_graph(tmp_path: Path, graph: dict | None = None) -> Path:
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph or SAMPLER_GRAPH), encoding="utf-8")
    return path


def build(tmp_path: Path, seed: int = 7, **kwargs) -> PersonaForwardSampler:
    return PersonaForwardSampler(
        write_graph(tmp_path), SamplingConfig(seed=seed), **kwargs
    )


def frequency(codes: np.ndarray, value_index: int) -> float:
    return float(np.mean(codes == value_index))


PRE_PHASE2_GOLDEN_SEED_11_N16 = {
    "a": [0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1],
    "b": [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1],
    "c": [0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0],
}


def test_default_output_matches_pre_phase2_golden(tmp_path):
    """Protect the exact output captured from the sampler before Phase 2 edits."""
    actual = build(tmp_path, seed=11).sample_indices(16)
    assert {nid: codes.tolist() for nid, codes in actual.items()} == (
        PRE_PHASE2_GOLDEN_SEED_11_N16
    )


def test_pins_clamp_every_sample(tmp_path):
    sampler = build(tmp_path)
    idx = sampler.sample_indices(512, pins={"a": 1})
    assert (idx["a"] == 1).all()


def test_pin_shifts_downstream_marginal(tmp_path):
    sampler = build(tmp_path)
    idx = sampler.sample_indices(4000, pins={"a": 1})
    # b | a=a1 follows the CPD row [0.05, 0.95].
    assert frequency(idx["b"], 1) == pytest.approx(0.95, abs=0.03)


def test_no_pin_marginal_stays_symmetric(tmp_path):
    sampler = build(tmp_path)
    idx = sampler.sample_indices(4000)
    assert frequency(idx["b"], 1) == pytest.approx(0.5, abs=0.03)


def test_empty_pins_bit_identical_to_default(tmp_path):
    plain = build(tmp_path, seed=11).sample_indices(64)
    with_kwarg = build(tmp_path, seed=11).sample_indices(64, pins={})
    for nid in plain:
        np.testing.assert_array_equal(plain[nid], with_kwarg[nid])


def test_request_rng_is_stateless_and_deterministic(tmp_path):
    sampler = build(tmp_path)
    first = sampler.sample_indices(64, rng=np.random.default_rng(3))
    second = sampler.sample_indices(64, rng=np.random.default_rng(3))
    for nid in first:
        np.testing.assert_array_equal(first[nid], second[nid])


def test_unknown_pin_node_raises(tmp_path):
    sampler = build(tmp_path)
    with pytest.raises(ValueError, match="unknown pinned node"):
        sampler.sample_indices(8, pins={"zz": 0})


def test_out_of_range_pin_raises(tmp_path):
    sampler = build(tmp_path)
    with pytest.raises(ValueError, match="out of range"):
        sampler.sample_indices(8, pins={"a": 5})


def sample_all(sampler: PersonaForwardSampler, n: int = 64) -> dict:
    return sampler.sample_indices(n, rng=np.random.default_rng(123))


def assert_bit_identical(left: dict, right: dict) -> None:
    assert left.keys() == right.keys()
    for nid in left:
        np.testing.assert_array_equal(left[nid], right[nid])


def test_noop_overrides_bit_identical(tmp_path):
    plain = sample_all(build(tmp_path))
    noop = sample_all(build(tmp_path, overrides=SamplerOverrides()))
    assert_bit_identical(plain, noop)


def test_preparsed_graph_bit_identical(tmp_path):
    path = write_graph(tmp_path)
    graph = json.loads(path.read_text(encoding="utf-8"))
    plain = sample_all(PersonaForwardSampler(path, SamplingConfig(seed=7)))
    shared = sample_all(
        PersonaForwardSampler(path, SamplingConfig(seed=7), graph=graph)
    )
    assert_bit_identical(plain, shared)


def test_prior_override_renormalizes(tmp_path):
    # [2, 2] normalizes to the baseline [0.5, 0.5]: identical tables.
    plain = sample_all(build(tmp_path))
    scaled = sample_all(
        build(tmp_path, overrides=SamplerOverrides(node_priors={"a": (2.0, 2.0)}))
    )
    assert_bit_identical(plain, scaled)


def test_prior_override_shifts_node(tmp_path):
    sampler = build(tmp_path, overrides=SamplerOverrides(node_priors={"a": (0.0, 1.0)}))
    idx = sampler.sample_indices(256, rng=np.random.default_rng(5))
    assert (idx["a"] == 1).all()


def test_prior_override_shifts_child_with_incoming_edge(tmp_path):
    sampler = build(
        tmp_path,
        overrides=SamplerOverrides(node_priors={"b": (0.9, 0.1)}),
    )
    idx = sampler.sample_indices(
        8000, pins={"a": 1}, rng=np.random.default_rng(5)
    )
    # Evidence ratios remain anchored to the graph prior [0.5, 0.5]:
    # q(b1) ∝ 0.1 * (0.95 / 0.5), q(b0) ∝ 0.9 * (0.05 / 0.5).
    assert frequency(idx["b"], 1) == pytest.approx(0.6786, abs=0.025)


def test_category_scale_expands_to_per_edge_factors(tmp_path):
    # Both a->b and b->c have source category "Demo".
    by_category = sample_all(
        build(tmp_path, overrides=SamplerOverrides(category_scales={"Demo": 0.0}))
    )
    by_edges = sample_all(
        build(
            tmp_path,
            overrides=SamplerOverrides(
                edge_weight_factors={("a", "b"): 0.0, ("b", "c"): 0.0}
            ),
        )
    )
    assert_bit_identical(by_category, by_edges)


def test_category_scale_composes_with_edge_factor(tmp_path):
    # 2.0 (category) * 0.5 (edge) == 1.0 on a->b; b->c keeps the 2.0 scale.
    composed = build(
        tmp_path,
        overrides=SamplerOverrides(
            category_scales={"Demo": 2.0}, edge_weight_factors={("a", "b"): 0.5}
        ),
    )
    explicit = build(
        tmp_path,
        overrides=SamplerOverrides(
            edge_weight_factors={("a", "b"): 1.0, ("b", "c"): 2.0}
        ),
    )
    assert_bit_identical(sample_all(composed), sample_all(explicit))


def test_category_scale_two_changes_downstream_marginal(tmp_path):
    baseline = build(tmp_path)
    scaled = build(
        tmp_path,
        overrides=SamplerOverrides(category_scales={"Demo": 2.0}),
    )
    baseline_idx = baseline.sample_indices(
        8000, pins={"a": 1}, rng=np.random.default_rng(17)
    )
    scaled_idx = scaled.sample_indices(
        8000, pins={"a": 1}, rng=np.random.default_rng(17)
    )
    assert frequency(baseline_idx["b"], 1) == pytest.approx(0.95, abs=0.02)
    assert frequency(scaled_idx["b"], 1) > 0.99


def test_edge_factor_zero_decouples(tmp_path):
    sampler = build(tmp_path, overrides=SamplerOverrides(edge_weight_factors={("a", "b"): 0.0}))
    idx = sampler.sample_indices(4000, pins={"a": 1}, rng=np.random.default_rng(9))
    assert frequency(idx["b"], 1) == pytest.approx(0.5, abs=0.03)


def test_gamma_scale_zero_reverts_to_priors(tmp_path):
    sampler = build(tmp_path, overrides=SamplerOverrides(gamma_scale=0.0))
    idx = sampler.sample_indices(4000, pins={"a": 1}, rng=np.random.default_rng(9))
    assert frequency(idx["b"], 1) == pytest.approx(0.5, abs=0.03)


def test_prior_override_validation(tmp_path):
    with pytest.raises(ValueError, match="unknown node"):
        build(tmp_path, overrides=SamplerOverrides(node_priors={"zz": (1.0,)}))
    with pytest.raises(ValueError, match="must have 2 entries"):
        build(tmp_path, overrides=SamplerOverrides(node_priors={"a": (1.0,)}))


def test_negative_edge_factor_rejected(tmp_path):
    with pytest.raises(ValueError, match="must be >= 0"):
        build(tmp_path, overrides=SamplerOverrides(edge_weight_factors={("a", "b"): -1.0}))

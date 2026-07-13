"""Pins and overrides for PersonaForwardSampler (Synthesis Studio Phase 2)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from persona.synthesis.sampler import PersonaForwardSampler, SamplingConfig

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

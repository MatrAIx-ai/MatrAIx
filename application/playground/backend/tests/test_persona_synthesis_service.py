"""Unit tests for PersonaSynthesisService over a small synthetic graph."""

from __future__ import annotations

import json

import pytest

from backend.service.persona_synthesis_service import PersonaSynthesisService

SYNTH_GRAPH = {
    "nodes": [
        {
            "id": "a",
            "label": "Age",
            "category": "Demographics",
            "values": ["young", "old"],
            "prior": [0.5, 0.5],
        },
        {
            "id": "b",
            "label": "Job",
            "category": "Demographics",
            "values": ["dev", "chef"],
            "prior": [0.6, 0.4],
        },
        {
            "id": "h",
            "label": "Latent H",
            "category": "Latent",
            "emit": False,
            "values": ["v"],
            "prior": [1.0],
        },
        {
            "id": "c",
            "label": "Condition",
            "category": "Health",
            "values": ["p", "q"],
            "prior": [0.3, 0.7],
            "description": "a health condition",
        },
        {
            "id": "d",
            "label": "Diet",
            "category": "Health",
            "values": ["m", "n"],
            "prior": [0.5, 0.5],
        },
    ],
    "directed_proposal_edges": [
        {
            "source": "a",
            "target": "b",
            "edge_weight": 0.8,
            "relation": "influences",
        },
        {
            "source": "b",
            "target": "c",
            "edge_weight": 0.5,
            "relation": "influences",
        },
        {
            "source": "h",
            "target": "c",
            "edge_weight": 0.2,
            "relation": "latent",
        },
        {
            "source": "c",
            "target": "d",
            "edge_weight": 0.9,
            "relation": "influences",
        },
    ],
    "proposal_view": {"topological_order": ["a", "h", "b", "c", "d"]},
}


@pytest.fixture()
def service(tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(SYNTH_GRAPH), encoding="utf-8")
    return PersonaSynthesisService(graph_path)


def test_overview_categories_sorted_by_avg_topo(service):
    overview = service.overview()
    names = [cat["name"] for cat in overview["categories"]]
    # Demographics avg topo = (0+2)/2 = 1.0, Latent = 1.0, Health = (3+4)/2 = 3.5.
    # Ties break alphabetically: Demographics before Latent.
    assert names == ["Demographics", "Latent", "Health"]


def test_overview_category_counts_and_attributes(service):
    overview = service.overview()
    by_name = {cat["name"]: cat for cat in overview["categories"]}
    demo = by_name["Demographics"]
    assert demo["nodeCount"] == 2
    assert demo["attributeCount"] == 2
    assert demo["helperCount"] == 0
    assert [a["id"] for a in demo["attributes"]] == ["a", "b"]  # topo order
    latent = by_name["Latent"]
    assert latent["attributeCount"] == 0
    assert latent["helperCount"] == 1


def test_overview_category_edges_aggregate_cross_category(service):
    overview = service.overview()
    edges = {(e["source"], e["target"]): e for e in overview["edges"]}
    # b->c and h->c cross into Health; a->b is internal to Demographics.
    assert ("Demographics", "Health") in edges
    assert edges[("Demographics", "Health")]["count"] == 1
    assert edges[("Latent", "Health")]["count"] == 1
    assert ("Demographics", "Demographics") not in edges
    by_name = {cat["name"]: cat for cat in overview["categories"]}
    assert by_name["Demographics"]["internalEdgeCount"] == 1
    assert by_name["Health"]["internalEdgeCount"] == 1  # c->d


def test_overview_counts(service):
    counts = service.overview()["counts"]
    assert counts == {
        "graphNodes": 5,
        "attributes": 4,
        "helpers": 1,
        "directedEdges": 4,
        "categories": 3,
    }


def test_subgraph_layers_and_edges(service):
    result = service.subgraph("c", up=1, down=1)
    assert result["center"] == "c"
    layers = {n["id"]: n["layer"] for n in result["nodes"]}
    assert layers == {"b": -1, "h": -1, "c": 0, "d": 1}
    edge_pairs = {(e["source"], e["target"]) for e in result["edges"]}
    assert edge_pairs == {("b", "c"), ("h", "c"), ("c", "d")}
    assert result["truncated"] is False


def test_subgraph_zero_hops_is_center_only(service):
    result = service.subgraph("c", up=0, down=0)
    assert [n["id"] for n in result["nodes"]] == ["c"]
    assert result["edges"] == []


def test_subgraph_two_hops_upstream(service):
    result = service.subgraph("c", up=2, down=0)
    layers = {n["id"]: n["layer"] for n in result["nodes"]}
    assert layers == {"a": -2, "b": -1, "h": -1, "c": 0}
    # a->b is between included nodes, so it appears.
    edge_pairs = {(e["source"], e["target"]) for e in result["edges"]}
    assert ("a", "b") in edge_pairs


def test_subgraph_unknown_node_raises(service):
    with pytest.raises(KeyError):
        service.subgraph("nope")


def test_node_detail_fields(service):
    detail = service.node_detail("c")
    assert detail["id"] == "c"
    assert detail["label"] == "Condition"
    assert detail["category"] == "Health"
    assert detail["description"] == "a health condition"
    assert detail["type"] == "attribute"
    assert detail["values"] == ["p", "q"]
    assert detail["prior"] == [0.3, 0.7]
    assert detail["inDegree"] == 2
    assert detail["outDegree"] == 1
    assert {e["id"] for e in detail["inEdges"]} == {"b", "h"}
    assert [e["id"] for e in detail["outEdges"]] == ["d"]


def test_node_detail_mapping_prior_follows_values_order(tmp_path):
    graph = {
        **SYNTH_GRAPH,
        "nodes": [dict(node) for node in SYNTH_GRAPH["nodes"]],
    }
    condition = next(node for node in graph["nodes"] if node["id"] == "c")
    condition["prior"] = {"q": 0.7, "p": 0.3}
    graph_path = tmp_path / "mapping-prior-graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    detail = PersonaSynthesisService(graph_path).node_detail("c")

    assert detail["prior"] == [0.3, 0.7]


def test_node_detail_helper_type(service):
    assert service.node_detail("h")["type"] == "latent/helper"


def test_node_detail_unknown_raises(service):
    with pytest.raises(KeyError):
        service.node_detail("nope")

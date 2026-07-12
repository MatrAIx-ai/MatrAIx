"""Read-only browsing service for the Persona Full DAG (Synthesis Studio).

Loads ``persona/synthesis/graph/full_dag.json`` lazily (23 MB, once per
process) and serves camelCase view dicts for the overview, subgraph, and
node-detail endpoints. Stdlib-only on purpose: importing
``persona.synthesis.sampler`` would pull in numpy, which the backend test
suite runs without. Phase 2 (sampling) will lazy-import the sampler inside
request handlers instead.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "PersonaSynthesisService",
    "DEFAULT_GRAPH_RELPATH",
    "MAX_SUBGRAPH_NODES_PER_DIRECTION",
]

DEFAULT_GRAPH_RELPATH = Path("persona") / "synthesis" / "graph" / "full_dag.json"

#: Per-direction node cap so drill-down views stay readable (closest-first).
MAX_SUBGRAPH_NODES_PER_DIRECTION = 60

#: Cap on the per-node edge lists in node detail payloads.
MAX_DETAIL_EDGES = 20


def _category(node: Dict[str, Any]) -> str:
    return node.get("category") or "Uncategorized"


def _is_attribute(node: Dict[str, Any]) -> bool:
    return node.get("emit", True) is not False


class PersonaSynthesisService:
    """Lazy, cached, thread-safe views over the Full DAG graph JSON."""

    def __init__(self, graph_path: Path) -> None:
        self._graph_path = Path(graph_path)
        self._lock = threading.Lock()
        self._loaded = False
        self._nodes_by_id: Dict[str, Dict[str, Any]] = {}
        self._out_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._in_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._topo_index: Dict[str, int] = {}
        self._edge_count = 0
        self._overview: Optional[Dict[str, Any]] = None

    @classmethod
    def from_repo(cls, repo_root: Path) -> "PersonaSynthesisService":
        return cls(Path(repo_root) / DEFAULT_GRAPH_RELPATH)

    # ------------------------------------------------------------------ load
    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            graph = json.loads(self._graph_path.read_text(encoding="utf-8"))
            nodes = graph.get("nodes", [])
            edges = graph.get("directed_proposal_edges", [])
            order = graph.get("proposal_view", {}).get("topological_order", [])

            self._nodes_by_id = {node["id"]: node for node in nodes}
            self._topo_index = {node_id: i for i, node_id in enumerate(order)}
            self._out_edges = {node["id"]: [] for node in nodes}
            self._in_edges = {node["id"]: [] for node in nodes}
            kept = 0
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                if source in self._nodes_by_id and target in self._nodes_by_id:
                    self._out_edges[source].append(edge)
                    self._in_edges[target].append(edge)
                    kept += 1
            self._edge_count = kept
            self._overview = self._build_overview()
            self._loaded = True

    def _topo(self, node_id: str) -> int:
        return self._topo_index.get(node_id, len(self._topo_index))

    # -------------------------------------------------------------- overview
    def _build_overview(self) -> Dict[str, Any]:
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for node in self._nodes_by_id.values():
            by_category.setdefault(_category(node), []).append(node)

        cross_edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        internal_counts: Dict[str, int] = {}
        for node_id, edges in self._out_edges.items():
            source_cat = _category(self._nodes_by_id[node_id])
            for edge in edges:
                target_cat = _category(self._nodes_by_id[edge["target"]])
                weight = float(edge.get("edge_weight", 1.0))
                if source_cat == target_cat:
                    internal_counts[source_cat] = internal_counts.get(source_cat, 0) + 1
                    continue
                key = (source_cat, target_cat)
                agg = cross_edges.setdefault(
                    key,
                    {
                        "source": source_cat,
                        "target": target_cat,
                        "count": 0,
                        "weightSum": 0.0,
                    },
                )
                agg["count"] += 1
                agg["weightSum"] += weight

        categories: List[Dict[str, Any]] = []
        for name, cat_nodes in by_category.items():
            topo_positions = [self._topo(n["id"]) for n in cat_nodes]
            avg_topo = (
                sum(topo_positions) / len(topo_positions) if topo_positions else 0.0
            )
            attributes = sorted(
                (n for n in cat_nodes if _is_attribute(n)),
                key=lambda n: (self._topo(n["id"]), n["id"]),
            )
            categories.append(
                {
                    "name": name,
                    "nodeCount": len(cat_nodes),
                    "attributeCount": len(attributes),
                    "helperCount": len(cat_nodes) - len(attributes),
                    "avgTopo": round(avg_topo, 2),
                    "internalEdgeCount": internal_counts.get(name, 0),
                    "attributes": [
                        {
                            "id": n["id"],
                            "label": n.get("label", n["id"]),
                            "valuesCount": len(n.get("values", [])),
                            "degree": len(self._in_edges[n["id"]])
                            + len(self._out_edges[n["id"]]),
                        }
                        for n in attributes
                    ],
                }
            )
        categories.sort(key=lambda cat: (cat["avgTopo"], cat["name"]))

        attribute_total = sum(cat["attributeCount"] for cat in categories)
        for agg in cross_edges.values():
            agg["weightSum"] = round(agg["weightSum"], 4)
        return {
            "categories": categories,
            "edges": sorted(
                cross_edges.values(),
                key=lambda e: (-e["count"], e["source"], e["target"]),
            ),
            "counts": {
                "graphNodes": len(self._nodes_by_id),
                "attributes": attribute_total,
                "helpers": len(self._nodes_by_id) - attribute_total,
                "directedEdges": self._edge_count,
                "categories": len(categories),
            },
        }

    def overview(self) -> Dict[str, Any]:
        self._ensure_loaded()
        assert self._overview is not None
        return self._overview

    # -------------------------------------------------------------- subgraph
    def _walk(
        self, start: str, *, downstream: bool, max_hops: int
    ) -> Tuple[Dict[str, int], bool]:
        """BFS hop distances from ``start`` (exclusive), closest-first, capped."""
        adjacency = self._out_edges if downstream else self._in_edges
        key = "target" if downstream else "source"
        distances: Dict[str, int] = {}
        truncated = False
        queue: deque[Tuple[str, int]] = deque([(start, 0)])
        seen = {start}
        while queue:
            node_id, hops = queue.popleft()
            if hops >= max_hops:
                continue
            for edge in adjacency[node_id]:
                neighbor = edge[key]
                if neighbor in seen:
                    continue
                if len(distances) >= MAX_SUBGRAPH_NODES_PER_DIRECTION:
                    truncated = True
                    return distances, truncated
                seen.add(neighbor)
                distances[neighbor] = hops + 1
                queue.append((neighbor, hops + 1))
        return distances, truncated

    def subgraph(
        self, node_id: str, *, up: int = 1, down: int = 1
    ) -> Dict[str, Any]:
        self._ensure_loaded()
        if node_id not in self._nodes_by_id:
            raise KeyError(node_id)
        upstream, up_truncated = self._walk(
            node_id, downstream=False, max_hops=up
        )
        downstream, down_truncated = self._walk(
            node_id, downstream=True, max_hops=down
        )

        layer_by_id: Dict[str, int] = {node_id: 0}
        for other, hops in upstream.items():
            layer_by_id[other] = -hops
        for other, hops in downstream.items():
            # A node reachable both ways keeps its upstream (negative) layer.
            layer_by_id.setdefault(other, hops)

        included = set(layer_by_id)
        node_payload = [
            {
                "id": nid,
                "label": self._nodes_by_id[nid].get("label", nid),
                "category": _category(self._nodes_by_id[nid]),
                "layer": layer_by_id[nid],
                "valuesCount": len(self._nodes_by_id[nid].get("values", [])),
                "emit": _is_attribute(self._nodes_by_id[nid]),
                "inDegree": len(self._in_edges[nid]),
                "outDegree": len(self._out_edges[nid]),
            }
            for nid in sorted(
                included, key=lambda n: (layer_by_id[n], self._topo(n), n)
            )
        ]
        edge_payload = []
        for nid in included:
            for edge in self._out_edges[nid]:
                if edge["target"] in included:
                    edge_payload.append(
                        {
                            "source": nid,
                            "target": edge["target"],
                            "weight": round(float(edge.get("edge_weight", 1.0)), 4),
                            "relation": edge.get("relation", ""),
                        }
                    )
        edge_payload.sort(key=lambda e: (e["source"], e["target"]))
        return {
            "center": node_id,
            "up": up,
            "down": down,
            "truncated": up_truncated or down_truncated,
            "nodes": node_payload,
            "edges": edge_payload,
        }

    # ----------------------------------------------------------- node detail
    def node_detail(self, node_id: str) -> Dict[str, Any]:
        self._ensure_loaded()
        node = self._nodes_by_id.get(node_id)
        if node is None:
            raise KeyError(node_id)

        def edge_view(edge: Dict[str, Any], other_key: str) -> Dict[str, Any]:
            other = self._nodes_by_id[edge[other_key]]
            return {
                "id": other["id"],
                "label": other.get("label", other["id"]),
                "relation": edge.get("relation", ""),
                "weight": round(float(edge.get("edge_weight", 1.0)), 4),
            }

        in_edges = sorted(
            self._in_edges[node_id],
            key=lambda e: -float(e.get("edge_weight", 1.0)),
        )
        out_edges = sorted(
            self._out_edges[node_id],
            key=lambda e: -float(e.get("edge_weight", 1.0)),
        )
        prior = node.get("prior") or []
        if isinstance(prior, dict):
            prior = [prior[value] for value in node.get("values", [])]
        return {
            "id": node_id,
            "label": node.get("label", node_id),
            "category": _category(node),
            "description": node.get("description", ""),
            "type": "attribute" if _is_attribute(node) else "latent/helper",
            "values": list(node.get("values", [])),
            "prior": [round(float(p), 4) for p in prior],
            "parents": list(node.get("parents", [])),
            "inDegree": len(self._in_edges[node_id]),
            "outDegree": len(self._out_edges[node_id]),
            "inEdges": [
                edge_view(e, "source") for e in in_edges[:MAX_DETAIL_EDGES]
            ],
            "outEdges": [
                edge_view(e, "target") for e in out_edges[:MAX_DETAIL_EDGES]
            ],
        }

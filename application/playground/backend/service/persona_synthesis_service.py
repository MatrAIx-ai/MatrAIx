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
import math
import threading
from collections import OrderedDict, deque
from concurrent.futures import Future
from copy import deepcopy
from heapq import heappop, heappush
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

__all__ = [
    "PersonaSynthesisService",
    "SamplerUnavailableError",
    "SynthesisValidationError",
    "UnknownNodeError",
    "DEFAULT_GRAPH_RELPATH",
    "MAX_SUBGRAPH_NODES_PER_DIRECTION",
]

DEFAULT_GRAPH_RELPATH = Path("persona") / "synthesis" / "graph" / "full_dag.json"

#: Per-direction node cap so drill-down views stay readable (closest-first).
MAX_SUBGRAPH_NODES_PER_DIRECTION = 60

#: Cap on the per-node edge lists in node detail payloads.
MAX_DETAIL_EDGES = 20

#: Upper bound for one synchronous sampling request.
MAX_SAMPLE_N = 200

#: Compiled override plans kept alive (LRU).
_SAMPLER_CACHE_SIZE = 8

# JavaScript Number.isSafeInteger upper bound; shared with API + frontend.
MAX_SAFE_SEED = 9_007_199_254_740_991

DEFAULT_DIMS_RELPATH = Path("persona") / "schema" / "dimensions.json"


class SynthesisValidationError(ValueError):
    """Invalid pins/overrides; ``key`` names the offending request field."""

    def __init__(self, message: str, *, key: str) -> None:
        super().__init__(message)
        self.key = key


class SamplerUnavailableError(RuntimeError):
    """Sampling needs numpy + persona.synthesis.sampler in the server env."""


def _load_numpy():
    try:
        import numpy
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise SamplerUnavailableError(
            "sampling requires numpy in the server environment"
        ) from exc
    return numpy


def _finite_nonnegative(raw: Any, *, key: str, label: str) -> float:
    if isinstance(raw, bool):
        raise SynthesisValidationError(f"{label} must be a number", key=key)
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        raise SynthesisValidationError(f"{label} must be a number", key=key) from None
    if not (math.isfinite(value) and value >= 0.0):
        raise SynthesisValidationError(
            f"{label} must be a finite number >= 0", key=key
        )
    return value


class UnknownNodeError(KeyError):
    """Raised when a requested graph node does not exist."""


def _category(node: Dict[str, Any]) -> str:
    return node.get("category") or "Uncategorized"


def _is_attribute(node: Dict[str, Any]) -> bool:
    return node.get("emit", True) is not False


class PersonaSynthesisService:
    """Lazy, cached, thread-safe views over the Full DAG graph JSON."""

    def __init__(self, graph_path: Path, dims_path: Optional[Path] = None) -> None:
        self._graph_path = Path(graph_path)
        self._dims_path = Path(dims_path) if dims_path is not None else None
        self._lock = threading.Lock()
        self._loaded = False
        self._graph: Optional[Dict[str, Any]] = None
        self._nodes_by_id: Dict[str, Dict[str, Any]] = {}
        self._out_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._in_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._edge_pairs: set[Tuple[str, str]] = set()
        self._categories: set[str] = set()
        self._topo_index: Dict[str, int] = {}
        self._edge_count = 0
        self._overview: Optional[Dict[str, Any]] = None
        self._dims: Optional[Dict[str, Dict[str, Any]]] = None
        self._sampler_lock = threading.Lock()
        self._sampler_cache: "OrderedDict[str, Any]" = OrderedDict()
        self._sampler_inflight: Dict[str, Future] = {}

    @classmethod
    def from_repo(cls, repo_root: Path) -> "PersonaSynthesisService":
        root = Path(repo_root)
        return cls(root / DEFAULT_GRAPH_RELPATH, dims_path=root / DEFAULT_DIMS_RELPATH)

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
            self._graph = graph
            self._edge_pairs = {
                (edge.get("source"), edge.get("target"))
                for edges in self._out_edges.values()
                for edge in edges
            }
            self._categories = {_category(node) for node in nodes}
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
        return deepcopy(self._overview)

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

    def _topological_layers(
        self, included: set[str], *, center: str
    ) -> Dict[str, int]:
        """Rank an induced DAG by longest predecessor path, centered at zero.

        Parallel edges are collapsed for the Kahn pass only; the response still
        preserves every source edge. Ready-node and successor ordering use the
        graph's global topological order with node id as a stable tie-breaker.
        """
        successors: Dict[str, set[str]] = {node_id: set() for node_id in included}
        in_degree = {node_id: 0 for node_id in included}
        for source in included:
            for edge in self._out_edges[source]:
                target = edge["target"]
                if target not in included or target in successors[source]:
                    continue
                successors[source].add(target)
                in_degree[target] += 1

        ready: List[Tuple[int, str]] = []
        for node_id, degree in in_degree.items():
            if degree == 0:
                heappush(ready, (self._topo(node_id), node_id))

        ranks = {node_id: 0 for node_id in included}
        processed = 0
        while ready:
            _, source = heappop(ready)
            processed += 1
            for target in sorted(
                successors[source], key=lambda node_id: (self._topo(node_id), node_id)
            ):
                ranks[target] = max(ranks[target], ranks[source] + 1)
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    heappush(ready, (self._topo(target), target))

        if processed != len(included):
            cyclic = sorted(
                (node_id for node_id, degree in in_degree.items() if degree > 0),
                key=lambda node_id: (self._topo(node_id), node_id),
            )
            preview = ", ".join(cyclic[:5])
            raise ValueError(
                f"induced subgraph around {center!r} contains a cycle: {preview}"
            )

        center_rank = ranks[center]
        return {
            node_id: rank - center_rank for node_id, rank in ranks.items()
        }

    def subgraph(
        self, node_id: str, *, up: int = 1, down: int = 1
    ) -> Dict[str, Any]:
        self._ensure_loaded()
        if node_id not in self._nodes_by_id:
            raise UnknownNodeError(node_id)
        upstream, up_truncated = self._walk(
            node_id, downstream=False, max_hops=up
        )
        downstream, down_truncated = self._walk(
            node_id, downstream=True, max_hops=down
        )

        included = {node_id} | set(upstream) | set(downstream)
        layer_by_id = self._topological_layers(included, center=node_id)
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
            raise UnknownNodeError(node_id)

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

    # ----------------------------------------------------------- sampling
    def sample(
        self,
        *,
        n: int,
        seed: int,
        gamma_scale: float = 1.0,
        pins: Optional[Mapping[str, str]] = None,
        overrides: Optional[Mapping[str, Any]] = None,
        compare_baseline: bool = True,
    ) -> Dict[str, Any]:
        """Sample personas under pins/overrides, with an optional same-seed baseline."""
        self._ensure_loaded()
        pins = dict(pins or {})
        if overrides is None:
            overrides = {}
        elif not isinstance(overrides, Mapping):
            raise SynthesisValidationError(
                "overrides must be an object", key="overrides"
            )
        else:
            overrides = dict(overrides)
        allowed_override_sections = {"edgeWeights", "nodePriors", "categoryScales"}
        for section in overrides:
            if section not in allowed_override_sections:
                raise SynthesisValidationError(
                    f"unknown override section: {section}",
                    key=f"overrides.{section}",
                )
        edge_weights = dict(overrides.get("edgeWeights") or {})
        raw_node_priors = dict(overrides.get("nodePriors") or {})
        raw_category_scales = dict(overrides.get("categoryScales") or {})

        if (
            not isinstance(n, int)
            or isinstance(n, bool)
            or not 1 <= n <= MAX_SAMPLE_N
        ):
            raise SynthesisValidationError(
                f"n must be an integer between 1 and {MAX_SAMPLE_N}", key="n"
            )
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= MAX_SAFE_SEED:
            raise SynthesisValidationError(
                f"seed must be an integer between 0 and {MAX_SAFE_SEED}", key="seed"
            )
        if not isinstance(compare_baseline, bool):
            raise SynthesisValidationError(
                "compareBaseline must be a boolean", key="compareBaseline"
            )
        gamma_scale = _finite_nonnegative(
            gamma_scale, key="gammaScale", label="gammaScale"
        )
        pin_indices, helper_pins = self._validate_pins(pins)
        edge_factors = self._validate_edge_weights(edge_weights)
        node_priors = self._validate_node_priors(raw_node_priors)
        category_scales = self._validate_category_scales(raw_category_scales)

        adjusted = self._sampler_for(gamma_scale, edge_factors, node_priors, category_scales)
        numpy = _load_numpy()
        idx = adjusted.sample_indices(
            n, pins=pin_indices, rng=numpy.random.default_rng(seed)
        )
        payload: Dict[str, Any] = {
            "personas": [adjusted.decode_row(idx, i) for i in range(n)],
            "marginals": self._marginals(adjusted, idx, n),
            "baselinePersonas": None,
            "baselineMarginals": None,
            "effectiveConfig": {
                "n": n,
                "seed": seed,
                "gammaScale": gamma_scale,
                "pins": pins,
                "overrides": {
                    "edgeWeights": {
                        f"{source}->{target}": factor
                        for (source, target), factor in edge_factors.items()
                    },
                    "nodePriors": node_priors,
                    "categoryScales": category_scales,
                },
            },
            "flags": {"helperPins": helper_pins},
        }
        if compare_baseline:
            baseline = self._sampler_for(1.0, {}, {}, {})
            baseline_idx = baseline.sample_indices(
                n, rng=numpy.random.default_rng(seed)
            )
            payload["baselinePersonas"] = [
                baseline.decode_row(baseline_idx, i) for i in range(n)
            ]
            payload["baselineMarginals"] = self._marginals(baseline, baseline_idx, n)
        return payload

    def _validate_pins(
        self, pins: Mapping[str, str]
    ) -> Tuple[Dict[str, int], List[str]]:
        pin_indices: Dict[str, int] = {}
        helper_pins: List[str] = []
        for nid, value in pins.items():
            node = self._nodes_by_id.get(nid)
            if node is None:
                raise SynthesisValidationError(
                    f"unknown pinned node: {nid}", key=f"pins.{nid}"
                )
            values = list(node.get("values", []))
            if value not in values:
                raise SynthesisValidationError(
                    f"unknown value {value!r} for {nid}", key=f"pins.{nid}"
                )
            pin_indices[nid] = values.index(value)
            if not _is_attribute(node):
                helper_pins.append(nid)
        return pin_indices, sorted(helper_pins)

    def _validate_edge_weights(
        self, edge_weights: Mapping[str, Any]
    ) -> Dict[Tuple[str, str], float]:
        factors: Dict[Tuple[str, str], float] = {}
        for key, raw in edge_weights.items():
            error_key = f"overrides.edgeWeights.{key}"
            source, sep, target = key.partition("->")
            if not sep or not source or not target:
                raise SynthesisValidationError(
                    f"edge key must look like 'source->target': {key}", key=error_key
                )
            if (source, target) not in self._edge_pairs:
                raise SynthesisValidationError(
                    f"unknown edge: {key}", key=error_key
                )
            factor = _finite_nonnegative(
                raw, key=error_key, label=f"edge factor for {key}"
            )
            factors[(source, target)] = factor
        return factors

    def _validate_node_priors(
        self, node_priors: Mapping[str, Any]
    ) -> Dict[str, List[float]]:
        validated: Dict[str, List[float]] = {}
        for nid, raw_dist in node_priors.items():
            error_key = f"overrides.nodePriors.{nid}"
            node = self._nodes_by_id.get(nid)
            if node is None:
                raise SynthesisValidationError(
                    f"unknown node in prior override: {nid}", key=error_key
                )
            if not isinstance(raw_dist, (list, tuple)):
                raise SynthesisValidationError(
                    f"prior for {nid} must be an array", key=error_key
                )
            if any(isinstance(p, bool) for p in raw_dist):
                raise SynthesisValidationError(
                    f"prior weights for {nid} must be numbers", key=error_key
                )
            try:
                dist = [float(p) for p in raw_dist]
            except (TypeError, ValueError, OverflowError):
                raise SynthesisValidationError(
                    f"prior weights for {nid} must be numbers", key=error_key
                ) from None
            expected = len(node.get("values", []))
            if len(dist) != expected:
                raise SynthesisValidationError(
                    f"prior for {nid} must have {expected} entries", key=error_key
                )
            if not all(math.isfinite(p) and p >= 0.0 for p in dist):
                raise SynthesisValidationError(
                    f"prior weights for {nid} must be finite numbers >= 0",
                    key=error_key,
                )
            total = sum(dist)
            if not math.isfinite(total) or total <= 0.0:
                raise SynthesisValidationError(
                    f"prior for {nid} must have finite positive total mass",
                    key=error_key,
                )
            validated[nid] = dist
        return validated

    def _validate_category_scales(
        self, category_scales: Mapping[str, Any]
    ) -> Dict[str, float]:
        validated: Dict[str, float] = {}
        for name, raw in category_scales.items():
            error_key = f"overrides.categoryScales.{name}"
            if name not in self._categories:
                raise SynthesisValidationError(
                    f"unknown category: {name}", key=error_key
                )
            validated[name] = _finite_nonnegative(
                raw, key=error_key, label=f"category scale for {name}"
            )
        return validated

    def _sampler_for(
        self,
        gamma_scale: float,
        edge_factors: Mapping[Tuple[str, str], float],
        node_priors: Mapping[str, List[float]],
        category_scales: Mapping[str, Any],
    ):
        key = json.dumps(
            {
                "gammaScale": gamma_scale,
                "edgeWeights": {f"{s}->{t}": f for (s, t), f in edge_factors.items()},
                "nodePriors": node_priors,
                "categoryScales": category_scales,
            },
            sort_keys=True,
        )
        with self._sampler_lock:
            cached = self._sampler_cache.get(key)
            if cached is not None:
                self._sampler_cache.move_to_end(key)
                return cached
            future = self._sampler_inflight.get(key)
            owner = future is None
            if owner:
                future = Future()
                self._sampler_inflight[key] = future
        assert future is not None
        if not owner:
            return future.result()
        try:
            sampler = self._build_sampler(
                gamma_scale, edge_factors, node_priors, category_scales
            )
        except BaseException as exc:
            with self._sampler_lock:
                self._sampler_inflight.pop(key, None)
                future.set_exception(exc)
            raise
        with self._sampler_lock:
            self._sampler_cache[key] = sampler
            while len(self._sampler_cache) > _SAMPLER_CACHE_SIZE:
                self._sampler_cache.popitem(last=False)
            self._sampler_inflight.pop(key, None)
            future.set_result(sampler)
        return sampler

    def _build_sampler(self, gamma_scale, edge_factors, node_priors, category_scales):
        try:
            from persona.synthesis.sampler import (
                PersonaForwardSampler,
                SamplerOverrides,
                SamplingConfig,
            )
        except ImportError as exc:  # numpy (or the persona package) missing
            raise SamplerUnavailableError(
                "sampling requires numpy and persona.synthesis.sampler in the server environment"
            ) from exc
        overrides = SamplerOverrides(
            edge_weight_factors=dict(edge_factors),
            node_priors={nid: tuple(dist) for nid, dist in node_priors.items()},
            category_scales={name: float(f) for name, f in category_scales.items()},
            gamma_scale=float(gamma_scale),
        )
        return PersonaForwardSampler(
            self._graph_path,
            SamplingConfig(seed=0),
            graph=self._graph,
            overrides=overrides,
        )

    def _marginals(self, sampler, idx, n: int) -> Dict[str, Any]:
        numpy = _load_numpy()
        out: Dict[str, Any] = {}
        for nid in sampler.emit_nodes:
            codes = idx.get(nid)
            if codes is None:
                continue
            values = sampler.values[nid]
            freqs = numpy.bincount(codes, minlength=len(values)) / float(n)
            out[nid] = {
                "label": sampler.nodes[nid].get("label", nid),
                "values": list(values),
                "freqs": [round(float(f), 4) for f in freqs],
            }
        return out

    # ------------------------------------------------------------- render
    def render_text(self, attributes: Mapping[str, str]) -> Dict[str, str]:
        """Render one persona attribute map to natural-language text."""
        from persona.synthesis.render import DEFAULT_DIMS_PATH, load_dims, render

        with self._lock:
            if self._dims is None:
                self._dims = load_dims(self._dims_path or DEFAULT_DIMS_PATH)
            dims = self._dims
        return {"text": render(dict(attributes), dims)}

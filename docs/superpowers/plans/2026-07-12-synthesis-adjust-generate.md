# Synthesis Studio Adjust + Generate (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users pin attribute values, adjust priors, scale category/edge influence, then sample personas and preview them (cards + text, baseline-vs-adjusted distributions, graph overlay) in the Synthesis Studio.

**Architecture:** The sampler gains runtime `pins` (clamped in the hot loop) and compile-time `SamplerOverrides`. Prior replacements change the proposal base prior while CPD likelihood ratios stay anchored to the graph's original prior; pairwise edge/category factors multiply compiled pairwise evidence **after** the graph's baseline shrinkage gamma is calculated, so a requested 2× factor is observable and full-CPT evidence is unchanged. `PersonaSynthesisService` validates requests stdlib-only, single-flight compiles override-keyed cached samplers, and serves `/api/synthesis/sample` + `/api/synthesis/render`. The frontend accumulates adjustments into a recipe, snapshots the effective request with each result, and renders paginated/lazy results in two new stacked panels.

**Tech Stack:** Python 3.12 + FastAPI + pydantic v2 + numpy (lazy), React 18 + TypeScript + @tanstack/react-query + Tailwind tokens, SVG graphs (no new runtime dependencies), `@playwright/test` 1.61.0 for dev-only acceptance tests.

**Spec:** `docs/superpowers/specs/2026-07-12-synthesis-adjust-generate-design.md`

## Global Constraints

- Branch: create `feature/synthesis-adjust-generate` off `feature/persona-dag-studio-phase1` (Phase 1 is in PR #206; rebase onto `main` once it merges).
- With no pins and no overrides, sampler output must stay **bit-identical** to current behavior for a fixed seed (guarded by test).
- The Playground backend test suite must keep passing **without numpy installed** (see `application/playground/backend/tests/conftest.py`); numpy-dependent tests use `pytest.importorskip("numpy")`, and the service lazy-imports the sampler inside request paths.
- `n` is 1–200; sampling is synchronous.
- API JSON is camelCase. Every synthesis 422 response, including Pydantic request-validation failures, has the single top-level shape `{"message": str, "key": str}`; `key` is a dot path such as `pins.age_bracket` or `n`.
- Seeds are integers in `0..9_007_199_254_740_991` (JavaScript's safe-integer range); invalid seeds return the synthesis 422 shape with `key="seed"`.
- Overrides apply to **pairwise proposal evidence** only (what the UI shows); full-CPT weights/contributions are untouched by edge/category factors. Category scales multiply every pairwise edge whose **source** node is in the category and compose multiplicatively with per-edge factors. Factors are applied after baseline node shrinkage is compiled; they do not participate in recomputing gamma.
- Frontend: no new runtime dependencies; `@playwright/test` is allowed as a dev-only verification dependency. Use dark-first tokens per `application/playground/frontend/DESIGN.md`; `FOCUS_RING` on all interactive elements; honor `prefers-reduced-motion` in both CSS and JS scrolling; `.glow` is reserved for the single Generate CTA; typecheck (`npm run build`) stays green.
- Results are tied to `effectiveConfig`, never the live recipe. Persona text is cached by a stable persona key. Render at most 10 persona cards per page and do not mount an attribute group's rows until that group is expanded (the full graph currently emits 1,290 attributes per persona).
- Run backend/sampler tests from the repo root with `PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground` and `.venv/bin/python -m pytest`.
- Environment prep (once): `.venv/bin/pip install numpy` (runtime dep for sampling; suites still pass without it).

---

### Task 0: Branch, plan tracking, and environment prep

**Files:** none (setup only)

- [ ] **Step 1: Create the working branch**

```bash
cd /data2/zonglin/MatrAIx
git checkout feature/persona-dag-studio-phase1
git checkout -b feature/synthesis-adjust-generate
```

- [ ] **Step 2: Track this revised implementation plan on the feature branch**

```bash
git add docs/superpowers/plans/2026-07-12-synthesis-adjust-generate.md
git commit -m "Add implementation plan for synthesis adjust and generate"
```

Expected: the plan is no longer an untracked file; unrelated `.claude/` files
remain untouched.

- [ ] **Step 3: Install numpy into the repo venv (runtime dep for sampling)**

```bash
.venv/bin/pip install numpy
.venv/bin/python -c "import numpy; print(numpy.__version__)"
```

Expected: a version prints (any modern numpy).

---

### Task 1: Extract stdlib-only persona renderer module

The backend must render persona text without importing numpy.
`persona/synthesis/scripts/render_personas.py` already has a pure `render()`
function, but the script module imports numpy at the top. Move the pure parts
into `persona/synthesis/render.py`; the script imports them back.

**Files:**
- Create: `persona/synthesis/render.py`
- Modify: `persona/synthesis/scripts/render_personas.py`
- Test: `tests/persona/synthesis/test_render_module.py`

**Interfaces:**
- Produces: `persona.synthesis.render.render(assignment: dict[str, Any], dims: dict[str, dict[str, Any]], *, max_clauses_per_bucket: int | None = 30) -> str`; `persona.synthesis.render.load_dims(path: str | Path = DEFAULT_DIMS_PATH) -> dict[str, dict[str, Any]]`; `persona.synthesis.render.DEFAULT_DIMS_PATH: Path` (→ `persona/schema/dimensions.json`). Module imports **stdlib only** (`json`, `re`, `pathlib`, `typing`).

- [ ] **Step 1: Write the failing test**

```python
# tests/persona/synthesis/test_render_module.py
"""The renderer must be importable without numpy and render deterministically."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DIMS_FIXTURE = {
    "dimensions": [
        {
            "id": "age_bracket",
            "label": "Age bracket",
            "category": "Demographic: Core",
            "values": ["18-24", "25-34"],
            "phrase": "aged {value}",
        },
        {
            "id": "hobby",
            "label": "Hobby",
            "category": "Interests: Food",
            "values": ["baking", "none"],
            "defaultValue": "none",
        },
    ]
}


def test_render_module_imports_stdlib_only():
    from persona.synthesis import render as render_module

    source = Path(render_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.partition(".")[0])
    assert imported_roots <= {"__future__", "json", "re", "pathlib", "typing"}


def test_render_core_bucket_and_default_suppression(tmp_path):
    from persona.synthesis.render import load_dims, render

    dims_path = tmp_path / "dims.json"
    dims_path.write_text(json.dumps(DIMS_FIXTURE), encoding="utf-8")
    dims = load_dims(dims_path)

    text = render({"age_bracket": "18-24", "hobby": "baking"}, dims)
    assert text == "A persona aged 18-24.\nInterests: their hobby is baking."

    # Default values and unknown attribute ids are silently omitted.
    text = render({"age_bracket": "18-24", "hobby": "none", "mystery": "x"}, dims)
    assert text == "A persona aged 18-24."


def test_script_reuses_the_module():
    from persona.synthesis.render import render

    path = REPO_ROOT / "persona" / "synthesis" / "scripts" / "render_personas.py"
    spec = importlib.util.spec_from_file_location("render_personas_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.render is render
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /data2/zonglin/MatrAIx
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/test_render_module.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'persona.synthesis.render'`.

- [ ] **Step 3: Create the module**

Create `persona/synthesis/render.py`. Move the following **verbatim** from
`persona/synthesis/scripts/render_personas.py` (they are pure stdlib):
`CORE_ORDER`, `BUCKETS`, `EXCLUDE_PREFIX`, `EXCLUDE_CATEGORY`, `STATE_IDS`,
`_fix_articles`, `load_dims`, `_is_default`, `_clause`, `render`. Add this
header:

```python
"""Stdlib-only natural-language rendering for persona attribute maps.

Extracted from ``persona/synthesis/scripts/render_personas.py`` so the
Playground backend can render personas without importing numpy. The script
keeps its CLI and re-imports these symbols.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIMS_PATH = REPO_ROOT / "persona" / "schema" / "dimensions.json"
```

(`parents[2]` because the module sits at `persona/synthesis/render.py`.)

- [ ] **Step 4: Point the script at the module**

In `persona/synthesis/scripts/render_personas.py`, delete the moved
definitions (`CORE_ORDER`, `BUCKETS`, `EXCLUDE_PREFIX`, `EXCLUDE_CATEGORY`,
`STATE_IDS`, `_fix_articles`, `load_dims`, `_is_default`, `_clause`,
`render`, and the local `DEFAULT_DIMS_PATH` assignment) and import them after
the existing sys.path setup block:

```python
from persona.synthesis.render import (  # noqa: E402,F401
    BUCKETS,
    CORE_ORDER,
    DEFAULT_DIMS_PATH,
    EXCLUDE_CATEGORY,
    EXCLUDE_PREFIX,
    STATE_IDS,
    _clause,
    _fix_articles,
    _is_default,
    load_dims,
    render,
)
```

(Keep the re-exports so any external caller of the script module keeps
working.)

- [ ] **Step 5: Run tests to verify they pass**

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/test_render_module.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Verify the script CLI still works**

```bash
.venv/bin/python persona/synthesis/scripts/render_personas.py --help | head -3
```

Expected: usage text, no traceback.

- [ ] **Step 7: Commit**

```bash
git add persona/synthesis/render.py persona/synthesis/scripts/render_personas.py tests/persona/synthesis/test_render_module.py
git commit -m "Extract stdlib-only persona renderer module"
```

---

### Task 2: Sampler pins + per-request rng

**Files:**
- Modify: `persona/synthesis/sampler/sampler.py` (method `sample_indices`, currently lines 387–473)
- Test: `tests/persona/synthesis/test_sampler_adjustments.py` (new)

**Interfaces:**
- Produces: `PersonaForwardSampler.sample_indices(n: int, *, pins: Mapping[str, int] | None = None, rng: np.random.Generator | None = None) -> Dict[str, np.ndarray]`. `pins` maps node id → **value index**; pinned nodes are clamped (do()-intervention). `rng` overrides `self.rng` for stateless per-request draws. Both default to current behavior.

- [ ] **Step 1: Write the failing tests**

```python
# tests/persona/synthesis/test_sampler_adjustments.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/test_sampler_adjustments.py -v
```

Expected: FAIL — `TypeError: sample_indices() got an unexpected keyword argument 'pins'`.

- [ ] **Step 3: Implement pins in `sample_indices`**

In `persona/synthesis/sampler/sampler.py`, change the signature and the first
lines of `sample_indices` (currently `def sample_indices(self, n: int) -> ...`
followed by `idx: Dict[str, np.ndarray] = {}` and `rng = self.rng`):

```python
    def sample_indices(
        self,
        n: int,
        *,
        pins: Mapping[str, int] | None = None,
        rng: "np.random.Generator | None" = None,
    ) -> Dict[str, np.ndarray]:
        """Sample N personas and return integer-coded node values.

        ``pins`` maps node id -> value index; pinned nodes skip sampling and
        are clamped to that index (do()-intervention), so downstream nodes
        condition on the pin while upstream distributions are untouched.
        ``rng`` overrides ``self.rng`` for stateless per-request draws.
        """
        idx: Dict[str, np.ndarray] = {}
        if rng is None:
            rng = self.rng
        pinned: Dict[str, int] = {}
        for nid, value_index in (pins or {}).items():
            if nid not in self.nodes:
                raise ValueError(f"unknown pinned node: {nid!r}")
            if not 0 <= int(value_index) < len(self.values[nid]):
                raise ValueError(
                    f"pin index out of range for {nid!r}: {value_index}"
                )
            pinned[nid] = int(value_index)
```

Then inside the plan loop, immediately after `for plan in self._plan:` and
before `k = plan.k`:

```python
        for plan in self._plan:
            if plan.nid in pinned:
                idx[plan.nid] = np.full(n, pinned[plan.nid], dtype=out_dtype)
                continue
            k = plan.k
            rng.random(out=u)
```

And in the prior-only tail loop, replace the body of
`for nid in self._prior_only_nodes:` with:

```python
        for nid in self._prior_only_nodes:
            if nid in pinned:
                idx[nid] = np.full(n, pinned[nid], dtype=out_dtype)
                continue
            idx[nid] = rng.choice(len(self.values[nid]), size=n, p=self.prior[nid]).astype(out_dtype)
```

(`Mapping` is already imported at the top of the file.)

- [ ] **Step 4: Run the new tests**

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/test_sampler_adjustments.py -v
```

Expected: 8 passed, including the pre-Phase-2 golden-output guard.

- [ ] **Step 5: Run the existing sampler regression suite**

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/ -v
```

Expected: all pass (parallel-sampling tests exercise the unchanged default path).

- [ ] **Step 6: Commit**

```bash
git add persona/synthesis/sampler/sampler.py tests/persona/synthesis/test_sampler_adjustments.py
git commit -m "Add pins and per-request rng to the persona sampler"
```

---

### Task 3: SamplerOverrides (edge factors, priors, category scales, gamma scale)

**Files:**
- Modify: `persona/synthesis/sampler/sampler.py` (`__init__`, `_compile_pairwise_edges`, `_compile_plan`), `persona/synthesis/sampler/__init__.py`
- Test: `tests/persona/synthesis/test_sampler_adjustments.py` (extend)

**Interfaces:**
- Produces: frozen dataclass `SamplerOverrides(edge_weight_factors: Mapping[tuple[str, str], float] = {}, node_priors: Mapping[str, tuple[float, ...]] = {}, category_scales: Mapping[str, float] = {}, gamma_scale: float = 1.0)` exported from `persona.synthesis.sampler`; `PersonaForwardSampler(graph_path, config=None, *, graph: Dict[str, Any] | None = None, overrides: SamplerOverrides | None = None)` — `graph` skips re-reading the JSON, `overrides` folds adjustments in at compile time. Uncategorized source nodes match category key `"Uncategorized"`.
- Semantics: CPD log-ratios and baseline shrinkage gamma are compiled from the unmodified graph. A node-prior replacement changes the base `plan.logprior` but does not change the CPD likelihood-ratio denominator. Edge/category factors multiply only pairwise `gamma * weight * logratio` tables after baseline gamma is known. `gamma_scale` multiplies all evidence, including full-CPT evidence. This prevents edge factors from being cancelled by gamma recomputation and prevents pairwise overrides from indirectly rescaling full-CPT contributions.

- [ ] **Step 1: Write the failing tests (append to the Task 2 test file)**

```python
from persona.synthesis.sampler import SamplerOverrides


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/test_sampler_adjustments.py -v
```

Expected: FAIL — `ImportError: cannot import name 'SamplerOverrides'`.

- [ ] **Step 3: Implement overrides in the sampler**

In `persona/synthesis/sampler/sampler.py`, add after the `SamplingConfig`
dataclass:

```python
@dataclass(frozen=True)
class SamplerOverrides:
    """Compile-time graph adjustments, folded in during plan compilation.

    ``edge_weight_factors`` multiplies individual pairwise-edge weights;
    ``category_scales`` multiplies every pairwise edge whose source node is in
    the category (composing with per-edge factors); ``node_priors`` replaces a
    node's base prior (renormalized); ``gamma_scale`` multiplies every node's
    compiled shrinkage gamma. Full-CPT weights are intentionally untouched.
    """

    edge_weight_factors: Mapping[tuple, float] = field(default_factory=dict)
    node_priors: Mapping[str, tuple] = field(default_factory=dict)
    category_scales: Mapping[str, float] = field(default_factory=dict)
    gamma_scale: float = 1.0
```

Change `__init__` (currently `def __init__(self, graph_path, config=None):` up
to `self.logprior = ...`):

```python
    def __init__(
        self,
        graph_path: str | Path,
        config: SamplingConfig | None = None,
        *,
        graph: Dict[str, Any] | None = None,
        overrides: "SamplerOverrides | None" = None,
    ):
        self.graph_path = Path(graph_path)
        self.config = config or SamplingConfig()
        self.overrides = overrides
        self._gamma_scale = float(overrides.gamma_scale) if overrides is not None else 1.0
        if self._gamma_scale < 0:
            raise ValueError("gamma_scale must be >= 0")
        if graph is None:
            with self.graph_path.open("r", encoding="utf-8") as f:
                graph = json.load(f)
        self.graph: Dict[str, Any] = graph
        self.rng = np.random.default_rng(self.config.seed)
        self.nodes = {n["id"]: n for n in self.graph.get("nodes", [])}
        self.values = {nid: list(n.get("values", [])) for nid, n in self.nodes.items()}
        self.vtoi = {nid: {v: i for i, v in enumerate(vals)} for nid, vals in self.values.items()}
        self.prior = {nid: _align_dist(n.get("prior", {}), self.values[nid]) for nid, n in self.nodes.items()}
        self.logprior = {nid: np.log(np.maximum(self.prior[nid], self.config.eps)) for nid in self.nodes}
```

(the rest of `__init__` — `topological_order` onward — is unchanged except for
this exact ordering):

```python
        self.in_edges = self._compile_pairwise_edges()
        self.full_cpts = self._compile_full_cpts()
        # Ratios above are anchored to the graph prior; plans below use replacements.
        self._apply_prior_overrides()
        self.masks = self._compile_masks()
        self.replaced_parents, self.gamma = self._compile_node_shrinkage()
        self.required_nodes = self._compile_required_nodes()
        self._compile_plan()
```

Add the two helper methods right after `__init__`:

```python
    def _apply_prior_overrides(self) -> None:
        """Replace proposal base priors after graph CPD ratios are compiled."""
        if self.overrides is None:
            return
        for nid, dist in self.overrides.node_priors.items():
            if nid not in self.nodes:
                raise ValueError(f"prior override for unknown node: {nid!r}")
            expected = len(self.values[nid])
            if len(dist) != expected:
                raise ValueError(
                    f"prior override for {nid!r} must have {expected} entries"
                )
            self.prior[nid] = _normalize([float(p) for p in dist])
            self.logprior[nid] = np.log(np.maximum(self.prior[nid], self.config.eps))

    def _edge_override_factor(self, source: str, target: str) -> float:
        overrides = self.overrides
        factor = float(overrides.edge_weight_factors.get((source, target), 1.0))
        category = self.nodes[source].get("category") or "Uncategorized"
        factor *= float(overrides.category_scales.get(category, 1.0))
        if not (factor >= 0.0):
            raise ValueError(
                f"edge weight factor for {source!r}->{target!r} must be >= 0"
            )
        return factor
```

Do **not** modify weights in `_compile_pairwise_edges`; baseline gamma must be
compiled from the original graph weights. In `_compile_plan`, change
`gamma = self.gamma[nid]` to:

```python
            gamma = self.gamma[nid] * self._gamma_scale
```

(Multiplying by the default `1.0` is IEEE-exact, preserving bit-identical
output on the no-override path.) Then replace the pairwise edge scaling line:

```python
                factor = (
                    self._edge_override_factor(edge["source"], nid)
                    if self.overrides is not None
                    else 1.0
                )
                scaled = (
                    (gamma * edge["weight"] * factor) * edge["logratio"]
                ).astype(np.float32)
```

Full-CPT scaling remains `gamma * cpt["weight"]`; pairwise factors never enter
`_compile_node_shrinkage` and never change full-CPT tables.

Finally, export the dataclass in `persona/synthesis/sampler/__init__.py`:

```python
from .sampler import PersonaForwardSampler, SamplerOverrides, SamplingConfig, codes_schema_path, sample_to_file_parallel
```

and add `"SamplerOverrides",` to `__all__`.

- [ ] **Step 4: Run the sampler test file**

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/test_sampler_adjustments.py -v
```

Expected: 20 passed (8 pin/RNG/golden tests plus 12 override tests).

- [ ] **Step 5: Run the full sampler suite (bit-identical regression)**

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add persona/synthesis/sampler/sampler.py persona/synthesis/sampler/__init__.py tests/persona/synthesis/test_sampler_adjustments.py
git commit -m "Add compile-time SamplerOverrides to the persona sampler"
```

---

### Task 4: Service sampling — validation, cached samplers, marginals, render

**Files:**
- Modify: `application/playground/backend/service/persona_synthesis_service.py`
- Test: `application/playground/backend/tests/test_synthesis_sampling_contract.py` (new, numpy-free)
- Test: `application/playground/backend/tests/test_synthesis_sampling.py` (new, `pytest.importorskip("numpy")`)

**Interfaces:**
- Consumes: `SamplerOverrides`, `PersonaForwardSampler(graph_path, config, *, graph, overrides)`, `sample_indices(n, pins=..., rng=...)` (Tasks 2–3); `persona.synthesis.render.render/load_dims` (Task 1).
- Produces:
  - `PersonaSynthesisService(graph_path, dims_path: Optional[Path] = None)`; `from_repo` passes `repo_root / "persona/schema/dimensions.json"`.
  - `sample(*, n: int, seed: int, gamma_scale: float = 1.0, pins: Optional[Mapping[str, str]] = None, overrides: Optional[Mapping[str, Any]] = None, compare_baseline: bool = True) -> Dict[str, Any]` — overrides dict uses camelCase keys `edgeWeights` (`"src->dst"` → factor), `nodePriors`, `categoryScales`. Returns the camelCase payload from the spec (`personas`, `marginals`, `baselinePersonas`, `baselineMarginals`, `effectiveConfig`, `flags`).
  - `render_text(attributes: Mapping[str, str]) -> Dict[str, str]` (`{"text": ...}`).
  - `SynthesisValidationError(message, *, key)` (a `ValueError` with `.key`), `SamplerUnavailableError(RuntimeError)`, both importable from the service module.
  - Marginal shape: `{nodeId: {"label": str, "values": [str], "freqs": [float]}}` for emit nodes.

- [ ] **Step 1: Write the failing numpy-free contract tests**

```python
# application/playground/backend/tests/test_synthesis_sampling_contract.py
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


def test_seed_out_of_bounds(service):
    expect_key(lambda: service.sample(n=5, seed=-1), "seed")
    expect_key(
        lambda: service.sample(n=5, seed=9_007_199_254_740_992),
        "seed",
    )


def test_render_text_uses_dims(service):
    body = service.render_text({"b": "b0"})
    assert body == {"text": "Interests: their b is b0."}


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
```

- [ ] **Step 2: Write the failing numpy-backed tests**

```python
# application/playground/backend/tests/test_synthesis_sampling.py
"""End-to-end sampling behavior for PersonaSynthesisService (needs numpy)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

np = pytest.importorskip("numpy")

from backend.service.persona_synthesis_service import PersonaSynthesisService
from backend.tests.test_synthesis_sampling_contract import DIMS_FIXTURE, SAMPLER_GRAPH


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
```

- [ ] **Step 3: Run both files to verify they fail**

```bash
cd /data2/zonglin/MatrAIx/application/playground && PYTHONPATH=/data2/zonglin/MatrAIx:/data2/zonglin/MatrAIx/environment/runtime:/data2/zonglin/MatrAIx/packages/playground/src:. \
  /data2/zonglin/MatrAIx/.venv/bin/python -m pytest backend/tests/test_synthesis_sampling_contract.py backend/tests/test_synthesis_sampling.py -v
```

Expected: FAIL with `ImportError: cannot import name 'SynthesisValidationError'`.

- [ ] **Step 4: Implement the service layer**

In `application/playground/backend/service/persona_synthesis_service.py`:

Add to the imports: `import math`, `from collections import OrderedDict, deque`
(extend the existing `deque` import), `from concurrent.futures import Future`,
and `Mapping` to the `typing` import.
Extend `__all__` with `"SynthesisValidationError"`, `"SamplerUnavailableError"`.
Add module constants below `MAX_DETAIL_EDGES`:

```python
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
```

Extend `__init__` / `from_repo` / `_ensure_loaded`:

```python
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
```

and inside `_ensure_loaded`, right after `self._edge_count = kept`:

```python
            self._graph = graph
            self._edge_pairs = {
                (edge.get("source"), edge.get("target"))
                for edges in self._out_edges.values()
                for edge in edges
            }
            self._categories = {_category(node) for node in nodes}
```

Append a new section at the end of the class:

```python
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
        overrides = dict(overrides or {})
        edge_weights = dict(overrides.get("edgeWeights") or {})
        raw_node_priors = dict(overrides.get("nodePriors") or {})
        raw_category_scales = dict(overrides.get("categoryScales") or {})

        if not 1 <= int(n) <= MAX_SAMPLE_N:
            raise SynthesisValidationError(
                f"n must be between 1 and {MAX_SAMPLE_N}", key="n"
            )
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= MAX_SAFE_SEED:
            raise SynthesisValidationError(
                f"seed must be an integer between 0 and {MAX_SAFE_SEED}", key="seed"
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
            int(n), pins=pin_indices, rng=numpy.random.default_rng(seed)
        )
        payload: Dict[str, Any] = {
            "personas": [adjusted.decode_row(idx, i) for i in range(int(n))],
            "marginals": self._marginals(adjusted, idx, int(n)),
            "baselinePersonas": None,
            "baselineMarginals": None,
            "effectiveConfig": {
                "n": int(n),
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
                int(n), rng=numpy.random.default_rng(seed)
            )
            payload["baselinePersonas"] = [
                baseline.decode_row(baseline_idx, i) for i in range(int(n))
            ]
            payload["baselineMarginals"] = self._marginals(baseline, baseline_idx, int(n))
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
            try:
                dist = [float(p) for p in raw_dist]
            except (TypeError, ValueError):
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
            if sum(dist) <= 0.0:
                raise SynthesisValidationError(
                    f"prior for {nid} must have positive total mass", key=error_key
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
```

Add the tiny lazy-numpy helper at module level (below the exception classes):

```python
def _load_numpy():
    try:
        import numpy
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise SamplerUnavailableError(
            "sampling requires numpy in the server environment"
        ) from exc
    return numpy


def _finite_nonnegative(raw: Any, *, key: str, label: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise SynthesisValidationError(f"{label} must be a number", key=key) from None
    if not (math.isfinite(value) and value >= 0.0):
        raise SynthesisValidationError(
            f"{label} must be a finite number >= 0", key=key
        )
    return value
```

- [ ] **Step 5: Run both new test files**

```bash
cd /data2/zonglin/MatrAIx/application/playground && PYTHONPATH=/data2/zonglin/MatrAIx:/data2/zonglin/MatrAIx/environment/runtime:/data2/zonglin/MatrAIx/packages/playground/src:. \
  /data2/zonglin/MatrAIx/.venv/bin/python -m pytest backend/tests/test_synthesis_sampling_contract.py backend/tests/test_synthesis_sampling.py -v
```

Expected: all pass (contract: 12, sampling: 9). The contract suite includes a
fresh subprocess that forcibly blocks every `numpy` import.

- [ ] **Step 6: Run the whole backend suite (regressions + no-numpy safety)**

```bash
cd /data2/zonglin/MatrAIx/application/playground && PYTHONPATH=/data2/zonglin/MatrAIx:/data2/zonglin/MatrAIx/environment/runtime:/data2/zonglin/MatrAIx/packages/playground/src:. \
  /data2/zonglin/MatrAIx/.venv/bin/python -m pytest backend/tests/ -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add application/playground/backend/service/persona_synthesis_service.py application/playground/backend/tests/test_synthesis_sampling_contract.py application/playground/backend/tests/test_synthesis_sampling.py
git commit -m "Add sampling, overrides validation, and render to PersonaSynthesisService"
```

---

### Task 5: API schemas + /sample and /render routes

**Files:**
- Modify: `application/playground/backend/api/schemas.py` (append after `SynthesisNodeDetail`), `application/playground/backend/api/app.py` (synthesis section, after `synthesis_node_detail`)
- Test: `application/playground/backend/tests/test_synthesis_sample_api.py` (new, numpy-free)

**Interfaces:**
- Consumes: `PersonaSynthesisService.sample/render_text`, `SynthesisValidationError`, `SamplerUnavailableError` (Task 4).
- Produces REST contracts consumed by the frontend (Task 6):
  - `POST /api/synthesis/sample` body `{n, seed, gammaScale, pins, overrides{edgeWeights,nodePriors,categoryScales}, compareBaseline}` → 200 spec payload; every semantic or schema 422 is the top-level `{"message", "key"}` envelope; 503 when the sampler is unavailable.
  - `POST /api/synthesis/render` body `{attributes: {id: value}}` → `{"text": str}`.

- [ ] **Step 1: Write the failing endpoint tests**

```python
# application/playground/backend/tests/test_synthesis_sample_api.py
"""Route contracts for POST /api/synthesis/sample and /render (no numpy)."""

from __future__ import annotations

import json

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


def test_negative_seed_maps_to_named_schema_error(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/sample", json={"n": 5, "seed": -1}
    )
    assert response.status_code == 422
    assert set(response.json()) == {"message", "key"}
    assert response.json()["key"] == "seed"


def test_sample_route_wiring(synthesis_client, monkeypatch):
    captured = {}

    def fake_sample(self, **kwargs):
        captured.update(kwargs)
        return {
            "personas": [{"a": "a1"}],
            "marginals": {"a": {"label": "A", "values": ["a0", "a1"], "freqs": [0.0, 1.0]}},
            "baselinePersonas": None,
            "baselineMarginals": None,
            "effectiveConfig": {"n": 1, "seed": 42, "gammaScale": 1.0, "pins": {}, "overrides": {}},
            "flags": {"helperPins": []},
        }

    monkeypatch.setattr(PersonaSynthesisService, "sample", fake_sample)
    response = synthesis_client.post(
        "/api/synthesis/sample",
        json={"n": 1, "overrides": {"categoryScales": {"Demo": 2.0}}, "compareBaseline": False},
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


def test_render_endpoint(synthesis_client):
    response = synthesis_client.post(
        "/api/synthesis/render", json={"attributes": {"b": "b0"}}
    )
    assert response.status_code == 200
    assert response.json() == {"text": "Interests: their b is b0."}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /data2/zonglin/MatrAIx/application/playground && PYTHONPATH=/data2/zonglin/MatrAIx:/data2/zonglin/MatrAIx/environment/runtime:/data2/zonglin/MatrAIx/packages/playground/src:. \
  /data2/zonglin/MatrAIx/.venv/bin/python -m pytest backend/tests/test_synthesis_sample_api.py -v
```

Expected: FAIL — 404 (`Not Found`) on the POST routes.

- [ ] **Step 3: Add the schemas**

Append to `application/playground/backend/api/schemas.py` after
`SynthesisNodeDetail` (the file already imports `BaseModel`, `ConfigDict`,
`Field`, `Dict`, `List`, `Optional`, `Any`):

```python
class SynthesisSampleOverrides(BaseModel):
    edgeWeights: Dict[str, float] = Field(default_factory=dict)
    nodePriors: Dict[str, List[float]] = Field(default_factory=dict)
    categoryScales: Dict[str, float] = Field(default_factory=dict)


class SynthesisSampleRequest(BaseModel):
    n: int = Field(20, ge=1, le=200)
    seed: int = Field(42, ge=0, le=9_007_199_254_740_991)
    gammaScale: float = Field(1.0, ge=0.0)
    pins: Dict[str, str] = Field(default_factory=dict)
    overrides: SynthesisSampleOverrides = Field(default_factory=SynthesisSampleOverrides)
    compareBaseline: bool = True


class SynthesisMarginal(BaseModel):
    model_config = ConfigDict(extra="allow")
    label: str
    values: List[str]
    freqs: List[float]


class SynthesisSampleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    personas: List[Dict[str, str]]
    baselinePersonas: Optional[List[Dict[str, str]]] = None
    marginals: Dict[str, SynthesisMarginal]
    baselineMarginals: Optional[Dict[str, SynthesisMarginal]] = None
    effectiveConfig: Dict[str, Any]
    flags: Dict[str, Any]


class SynthesisRenderRequest(BaseModel):
    attributes: Dict[str, str] = Field(default_factory=dict)


class SynthesisRenderResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: str
```

Add the six new names to the `__all__` list next to the existing
`"SynthesisNodeDetail"` entry.

- [ ] **Step 4: Add the routes**

In `application/playground/backend/api/app.py`, import
`RequestValidationError`, `request_validation_exception_handler`, and
`JSONResponse`:

```python
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import FileResponse, JSONResponse
```

Add this module helper above `create_app`; it collapses element-level Pydantic
locations back to the owning recipe entry so the frontend can highlight it:

```python
def _synthesis_validation_key(error: Dict[str, Any]) -> str:
    parts = [str(part) for part in error.get("loc", ()) if part != "body"]
    if parts[:2] == ["overrides", "nodePriors"] and len(parts) >= 3:
        parts = parts[:3]
    elif parts[:2] in [
        ["overrides", "edgeWeights"],
        ["overrides", "categoryScales"],
    ] and len(parts) >= 3:
        parts = parts[:3]
    elif parts[:1] == ["pins"] and len(parts) >= 2:
        parts = parts[:2]
    return ".".join(parts) or "body"
```

Immediately after `app = FastAPI(...)` inside `create_app`, register the scoped
handler. Existing non-synthesis validation responses retain FastAPI's default:

```python
    @app.exception_handler(RequestValidationError)
    async def synthesis_request_validation(request: Request, exc: RequestValidationError):
        if request.url.path not in {
            "/api/synthesis/sample",
            "/api/synthesis/render",
        }:
            return await request_validation_exception_handler(request, exc)
        error = exc.errors()[0]
        return JSONResponse(
            status_code=422,
            content={
                "message": str(error.get("msg") or "Invalid request"),
                "key": _synthesis_validation_key(error),
            },
        )
```

Then extend the existing service import:

```python
from backend.service.persona_synthesis_service import (
    SamplerUnavailableError,
    SynthesisValidationError,
    UnknownNodeError,
)
```

and append after the `synthesis_node_detail` route, inside the same section:

```python
    @app.post(
        "/api/synthesis/sample",
        response_model=schemas.SynthesisSampleResponse,
        tags=["synthesis"],
    )
    def synthesis_sample(
        body: schemas.SynthesisSampleRequest,
        services: AppState = Depends(get_services),
    ):
        """Sample personas under pins/overrides, plus an optional same-seed baseline."""
        try:
            return services.persona_synthesis.sample(
                n=body.n,
                seed=body.seed,
                gamma_scale=body.gammaScale,
                pins=body.pins,
                overrides=body.overrides.model_dump(),
                compare_baseline=body.compareBaseline,
            )
        except SynthesisValidationError as exc:
            return JSONResponse(
                status_code=422,
                content={"message": str(exc), "key": exc.key},
            )
        except SamplerUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    @app.post(
        "/api/synthesis/render",
        response_model=schemas.SynthesisRenderResponse,
        tags=["synthesis"],
    )
    def synthesis_render(
        body: schemas.SynthesisRenderRequest,
        services: AppState = Depends(get_services),
    ):
        """Render one persona attribute map to natural-language text."""
        return services.persona_synthesis.render_text(body.attributes)
```

- [ ] **Step 5: Run the endpoint tests, then the whole backend suite**

```bash
cd /data2/zonglin/MatrAIx/application/playground && PYTHONPATH=/data2/zonglin/MatrAIx:/data2/zonglin/MatrAIx/environment/runtime:/data2/zonglin/MatrAIx/packages/playground/src:. \
  /data2/zonglin/MatrAIx/.venv/bin/python -m pytest backend/tests/test_synthesis_sample_api.py -v && \
  /data2/zonglin/MatrAIx/.venv/bin/python -m pytest backend/tests/ -q
```

Expected: 6 passed, then full suite green. Both service-generated and
Pydantic-generated 422 bodies have exactly the top-level keys `message` and
`key`.

- [ ] **Step 6: Commit**

```bash
git add application/playground/backend/api/schemas.py application/playground/backend/api/app.py application/playground/backend/tests/test_synthesis_sample_api.py
git commit -m "Add /api/synthesis/sample and /render endpoints"
```

---

### Task 6: Frontend types + API client

**Files:**
- Modify: `application/playground/frontend/src/lib/types.ts` (append to the Synthesis section), `application/playground/frontend/src/lib/api.ts`

**Interfaces:**
- Produces (used by Tasks 7–11): the TS types below, plus `api.sampleSynthesis(body: SynthesisSampleRequest)` and `api.renderSynthesisPersona(attributes: Record<string, string>)`.

- [ ] **Step 1: Append types to `types.ts`**

```ts
export interface SynthesisSampleOverrides {
  edgeWeights: Record<string, number>;
  nodePriors: Record<string, number[]>;
  categoryScales: Record<string, number>;
}

export interface SynthesisSampleRequest {
  n: number;
  seed: number;
  gammaScale: number;
  pins: Record<string, string>;
  overrides: SynthesisSampleOverrides;
  compareBaseline: boolean;
}

export interface SynthesisMarginal {
  label: string;
  values: string[];
  freqs: number[];
}

export interface SynthesisSampleResponse {
  personas: Record<string, string>[];
  baselinePersonas?: Record<string, string>[] | null;
  marginals: Record<string, SynthesisMarginal>;
  baselineMarginals?: Record<string, SynthesisMarginal> | null;
  effectiveConfig: {
    n: number;
    seed: number;
    gammaScale: number;
    pins: Record<string, string>;
    overrides: SynthesisSampleOverrides;
  };
  flags: { helperPins: string[] };
}

export interface SynthesisRenderResponse {
  text: string;
}
```

- [ ] **Step 2: Add the API functions**

First update the shared `request()` error extraction so the top-level synthesis
422 envelope produces a useful `ApiError.message` while existing `detail`
responses keep working:

```ts
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : data;
    const objectMessage =
      detail && typeof detail === "object" && "message" in detail
        ? String(detail.message)
        : null;
    const message =
      typeof detail === "string" ? detail : objectMessage ?? response.statusText;
    throw new ApiError(response.status, message || "Request failed", detail);
  }
```

Then extend the type-import list with `SynthesisSampleRequest`,
`SynthesisSampleResponse`, `SynthesisRenderResponse`, and add next to the
existing synthesis getters:

```ts
  sampleSynthesis: (body: SynthesisSampleRequest) =>
    request<SynthesisSampleResponse>("/api/synthesis/sample", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  renderSynthesisPersona: (attributes: Record<string, string>) =>
    request<SynthesisRenderResponse>("/api/synthesis/render", {
      method: "POST",
      body: JSON.stringify({ attributes }),
    }),
```

- [ ] **Step 3: Typecheck**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend && npm run typecheck
```

Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add application/playground/frontend/src/lib/types.ts application/playground/frontend/src/lib/api.ts
git commit -m "Add synthesis sample/render API client"
```

---

### Task 7: Recipe model + Adjust & Generate panel

**Files:**
- Create: `application/playground/frontend/src/components/synthesis/recipe.ts`
- Create: `application/playground/frontend/src/components/synthesis/AdjustGeneratePanel.tsx`

**Interfaces:**
- Produces (consumed by Tasks 8–11):

```ts
// recipe.ts
export type RecipeEntry =
  | { kind: "pin"; nodeId: string; label: string; value: string }
  | { kind: "prior"; nodeId: string; label: string; values: string[]; weights: number[] }
  | { kind: "category"; category: string; factor: number }
  | { kind: "edge"; source: string; target: string; sourceLabel: string; targetLabel: string; factor: number };
export interface SamplingControls { n: number; seed: number; gammaScale: number; compareBaseline: boolean; }
export const DEFAULT_CONTROLS: SamplingControls;
export const MAX_SAFE_SEED: number;
export function validateSamplingControls(controls: SamplingControls): string | null;
export function recipeKey(entry: RecipeEntry): string; // "pin:<id>" | "prior:<id>" | "category:<name>" | "edge:<s>-><t>"
export function upsertEntry(recipe: RecipeEntry[], entry: RecipeEntry): RecipeEntry[];
export function buildSampleRequest(recipe: RecipeEntry[], controls: SamplingControls): SynthesisSampleRequest;
export function recipeKeyForErrorKey(errorKey: string): string | null;
// AdjustGeneratePanel.tsx
export function AdjustGeneratePanel(props: {
  recipe: RecipeEntry[];
  onUpsert: (entry: RecipeEntry) => void;
  onRemove: (key: string) => void;
  controls: SamplingControls;
  onControlsChange: (controls: SamplingControls) => void;
  onGenerate: () => void;
  generating: boolean;
  error: { message: string; key: string | null } | null;
  helperPins: string[];
}): JSX.Element;
```

- [ ] **Step 1: Create `recipe.ts`**

```ts
/**
 * The "recipe": accumulated adjustments (pins, prior edits, category scales,
 * edge factors) that compile into one /api/synthesis/sample request.
 */
import type { SynthesisSampleRequest } from "@/lib/types";

export type RecipeEntry =
  | { kind: "pin"; nodeId: string; label: string; value: string }
  | { kind: "prior"; nodeId: string; label: string; values: string[]; weights: number[] }
  | { kind: "category"; category: string; factor: number }
  | {
      kind: "edge";
      source: string;
      target: string;
      sourceLabel: string;
      targetLabel: string;
      factor: number;
    };

export interface SamplingControls {
  n: number;
  seed: number;
  gammaScale: number;
  compareBaseline: boolean;
}

export const DEFAULT_CONTROLS: SamplingControls = {
  n: 50,
  seed: 42,
  gammaScale: 1,
  compareBaseline: true,
};

export const MAX_SAFE_SEED = 9_007_199_254_740_991;

export function validateSamplingControls(controls: SamplingControls): string | null {
  if (!Number.isInteger(controls.n) || controls.n < 1 || controls.n > 200) {
    return "Personas must be an integer between 1 and 200.";
  }
  if (
    !Number.isSafeInteger(controls.seed) ||
    controls.seed < 0 ||
    controls.seed > MAX_SAFE_SEED
  ) {
    return `Seed must be a safe integer between 0 and ${MAX_SAFE_SEED}.`;
  }
  if (!Number.isFinite(controls.gammaScale) || controls.gammaScale < 0) {
    return "Gamma must be a finite number greater than or equal to 0.";
  }
  return null;
}

export function recipeKey(entry: RecipeEntry): string {
  switch (entry.kind) {
    case "pin":
      return `pin:${entry.nodeId}`;
    case "prior":
      return `prior:${entry.nodeId}`;
    case "category":
      return `category:${entry.category}`;
    case "edge":
      return `edge:${entry.source}->${entry.target}`;
  }
}

/** Insert or replace the entry occupying the same recipe key. */
export function upsertEntry(recipe: RecipeEntry[], entry: RecipeEntry): RecipeEntry[] {
  const key = recipeKey(entry);
  const index = recipe.findIndex((existing) => recipeKey(existing) === key);
  if (index === -1) return [...recipe, entry];
  const next = [...recipe];
  next[index] = entry;
  return next;
}

export function buildSampleRequest(
  recipe: RecipeEntry[],
  controls: SamplingControls,
): SynthesisSampleRequest {
  const request: SynthesisSampleRequest = {
    n: controls.n,
    seed: controls.seed,
    gammaScale: controls.gammaScale,
    pins: {},
    overrides: { edgeWeights: {}, nodePriors: {}, categoryScales: {} },
    compareBaseline: controls.compareBaseline,
  };
  for (const entry of recipe) {
    if (entry.kind === "pin") request.pins[entry.nodeId] = entry.value;
    else if (entry.kind === "prior") request.overrides.nodePriors[entry.nodeId] = entry.weights;
    else if (entry.kind === "category") request.overrides.categoryScales[entry.category] = entry.factor;
    else request.overrides.edgeWeights[`${entry.source}->${entry.target}`] = entry.factor;
  }
  return request;
}

/** Map a 422 payload key (e.g. "pins.age_bracket") back to a recipe key. */
export function recipeKeyForErrorKey(errorKey: string): string | null {
  const pin = /^pins\.(.+)$/.exec(errorKey);
  if (pin) return `pin:${pin[1]}`;
  const prior = /^overrides\.nodePriors\.(.+)$/.exec(errorKey);
  if (prior) return `prior:${prior[1]}`;
  const category = /^overrides\.categoryScales\.(.+)$/.exec(errorKey);
  if (category) return `category:${category[1]}`;
  const edge = /^overrides\.edgeWeights\.(.+)$/.exec(errorKey);
  if (edge) return `edge:${edge[1]}`;
  return null;
}
```

- [ ] **Step 2: Create `AdjustGeneratePanel.tsx`**

```tsx
/**
 * Panel 4 — "Adjust & Generate": editable recipe entries (pins, prior edits,
 * category scales, edge factors), sampling controls, and the Generate CTA.
 * Entries are appended from the graph/detail panels; editing happens here.
 */
import type { ReactNode } from "react";

import { FOCUS_RING, Sym } from "../cockpit/cockpitShared";
import type { RecipeEntry, SamplingControls } from "./recipe";
import { recipeKey, validateSamplingControls } from "./recipe";

const NUMBER_FIELD = `h-8 w-20 rounded border border-outline bg-field px-2 text-xs text-text-main ${FOCUS_RING}`;

function FactorSlider({
  value,
  onChange,
  label,
}: {
  value: number;
  onChange: (next: number) => void;
  label: string;
}) {
  return (
    <span className="flex min-w-0 flex-1 items-center gap-2">
      <input
        type="range"
        min={0}
        max={3}
        step={0.1}
        value={value}
        aria-label={label}
        onChange={(event) => onChange(Number(event.target.value))}
        className={`min-w-0 flex-1 accent-[rgb(var(--primary))] ${FOCUS_RING}`}
      />
      <span className="w-10 flex-none text-right font-mono text-[11px] text-text-variant">
        {value.toFixed(1)}×
      </span>
    </span>
  );
}

function EntryShell({
  invalid,
  helper,
  onRemove,
  removeLabel,
  children,
}: {
  invalid: boolean;
  helper: boolean;
  onRemove: () => void;
  removeLabel: string;
  children: ReactNode;
}) {
  return (
    <li
      data-testid="synthesis-recipe-entry"
      data-invalid={invalid ? "true" : "false"}
      className={`flex items-center gap-2 rounded-md border px-2.5 py-1.5 ${
        invalid ? "border-danger/70 bg-danger/5" : "border-outline-dim bg-surface-low/50"
      }`}
    >
      <div className="min-w-0 flex-1">{children}</div>
      {helper ? (
        <span className="hud flex-none text-warn" title="Pinned node is a latent helper (emit: false)">
          helper
        </span>
      ) : null}
      <button
        type="button"
        aria-label={removeLabel}
        onClick={onRemove}
        className={`grid h-6 w-6 flex-none place-items-center rounded text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
      >
        <Sym name="close" size={14} />
      </button>
    </li>
  );
}

export function AdjustGeneratePanel({
  recipe,
  onUpsert,
  onRemove,
  controls,
  onControlsChange,
  onGenerate,
  generating,
  error,
  helperPins,
}: {
  recipe: RecipeEntry[];
  onUpsert: (entry: RecipeEntry) => void;
  onRemove: (key: string) => void;
  controls: SamplingControls;
  onControlsChange: (controls: SamplingControls) => void;
  onGenerate: () => void;
  generating: boolean;
  error: { message: string; key: string | null } | null;
  helperPins: string[];
}) {
  const invalidKey = error?.key ?? null;
  const controlsError = validateSamplingControls(controls);
  return (
    <div className="custom-scrollbar flex h-full min-h-0 flex-col gap-4 overflow-y-auto p-4">
      <div>
        <div className="hud mb-1 text-text-dim">Recipe</div>
        {recipe.length === 0 ? (
          <p className="text-xs leading-relaxed text-text-dim">
            No adjustments yet — pin values, edit priors, or scale influence from the
            graph panels above. Generate works without a recipe (pure baseline).
          </p>
        ) : (
          <ul className="space-y-1.5">
            {recipe.map((entry) => {
              const key = recipeKey(entry);
              const invalid = invalidKey === key;
              if (entry.kind === "pin") {
                return (
                  <EntryShell
                    key={key}
                    invalid={invalid}
                    helper={helperPins.includes(entry.nodeId)}
                    onRemove={() => onRemove(key)}
                    removeLabel={`Remove pin on ${entry.label}`}
                  >
                    <span className="flex items-baseline gap-1.5 text-xs">
                      <Sym name="push_pin" size={13} className="translate-y-0.5 text-primary" />
                      <span className="truncate text-text-main">{entry.label}</span>
                      <span className="text-text-dim">=</span>
                      <span className="truncate font-mono text-[11px] text-text-variant">
                        {entry.value}
                      </span>
                    </span>
                  </EntryShell>
                );
              }
              if (entry.kind === "category") {
                return (
                  <EntryShell
                    key={key}
                    invalid={invalid}
                    helper={false}
                    onRemove={() => onRemove(key)}
                    removeLabel={`Remove influence scale for ${entry.category}`}
                  >
                    <span className="flex items-center gap-2 text-xs">
                      <span className="w-40 flex-none truncate text-text-main" title={entry.category}>
                        {entry.category}
                      </span>
                      <FactorSlider
                        value={entry.factor}
                        label={`Influence of ${entry.category}`}
                        onChange={(factor) => onUpsert({ ...entry, factor })}
                      />
                    </span>
                  </EntryShell>
                );
              }
              if (entry.kind === "edge") {
                return (
                  <EntryShell
                    key={key}
                    invalid={invalid}
                    helper={false}
                    onRemove={() => onRemove(key)}
                    removeLabel={`Remove weight factor for ${entry.sourceLabel} to ${entry.targetLabel}`}
                  >
                    <span className="flex items-center gap-2 text-xs">
                      <span
                        className="w-40 flex-none truncate text-text-main"
                        title={`${entry.sourceLabel} → ${entry.targetLabel}`}
                      >
                        {entry.sourceLabel} → {entry.targetLabel}
                      </span>
                      <FactorSlider
                        value={entry.factor}
                        label={`Weight factor for ${entry.sourceLabel} to ${entry.targetLabel}`}
                        onChange={(factor) => onUpsert({ ...entry, factor })}
                      />
                    </span>
                  </EntryShell>
                );
              }
              const total = entry.weights.reduce((sum, w) => sum + w, 0);
              return (
                <EntryShell
                  key={key}
                  invalid={invalid}
                  helper={false}
                  onRemove={() => onRemove(key)}
                  removeLabel={`Remove prior adjustment for ${entry.label}`}
                >
                  <div className="text-xs">
                    <div className="mb-1 flex items-baseline gap-1.5">
                      <Sym name="tune" size={13} className="translate-y-0.5 text-primary" />
                      <span className="truncate text-text-main">{entry.label}</span>
                      <span className="text-[10px] text-text-dim">prior</span>
                    </div>
                    <ul className="max-h-36 space-y-1 overflow-y-auto pr-1">
                      {entry.values.map((value, index) => {
                        const weight = entry.weights[index] ?? 0;
                        const share = total > 0 ? weight / total : 0;
                        return (
                          <li key={value} className="flex items-center gap-2">
                            <span
                              className="w-24 flex-none truncate text-[11px] text-text-variant"
                              title={value}
                            >
                              {value}
                            </span>
                            <input
                              type="number"
                              min={0}
                              step={0.1}
                              value={weight}
                              aria-label={`Prior weight for ${entry.label} = ${value}`}
                              onChange={(event) => {
                                const weights = [...entry.weights];
                                weights[index] = Math.max(0, Number(event.target.value) || 0);
                                onUpsert({ ...entry, weights });
                              }}
                              className={`h-7 w-16 flex-none rounded border border-outline bg-field px-1.5 text-[11px] text-text-main ${FOCUS_RING}`}
                            />
                            <span className="h-1.5 min-w-0 flex-1 rounded-sm bg-surface-high" aria-hidden="true">
                              <span
                                className="block h-full rounded-sm"
                                style={{
                                  width: `${Math.round(share * 100)}%`,
                                  background: "rgb(var(--primary) / 0.55)",
                                }}
                              />
                            </span>
                            <span className="w-10 flex-none text-right font-mono text-[10px] text-text-dim">
                              {(share * 100).toFixed(0)}%
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </EntryShell>
              );
            })}
          </ul>
        )}
      </div>

      <div className="border-t border-outline-dim pt-3">
        <div className="hud mb-2 text-text-dim">Sampling</div>
        <div className="flex flex-wrap items-end gap-3">
          {(
            [
              ["n", "Personas", 1, 200],
              ["seed", "Seed", 0, Number.MAX_SAFE_INTEGER],
              ["gammaScale", "Gamma ×", 0, 10],
            ] as const
          ).map(([field, label, min, max]) => (
            <label key={field} className="flex flex-col gap-1 text-[11px] text-text-variant">
              {label}
              <input
                type="number"
                min={min}
                max={max}
                step={field === "gammaScale" ? 0.1 : 1}
                value={controls[field]}
                onChange={(event) =>
                  onControlsChange({ ...controls, [field]: Number(event.target.value) })
                }
                className={NUMBER_FIELD}
              />
            </label>
          ))}
          <label className="flex items-center gap-1.5 pb-1.5 text-[11px] text-text-variant">
            <input
              type="checkbox"
              checked={controls.compareBaseline}
              onChange={(event) =>
                onControlsChange({ ...controls, compareBaseline: event.target.checked })
              }
              className={`accent-[rgb(var(--primary))] ${FOCUS_RING}`}
            />
            compare with baseline
          </label>
          <button
            type="button"
            onClick={onGenerate}
            disabled={generating || controlsError !== null}
            className={`glow ml-auto flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-[13px] font-semibold text-on-primary transition-[background-color,transform] duration-150 ease-out hover:bg-primary-dim active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none ${FOCUS_RING}`}
          >
            <Sym name={generating ? "hourglass_top" : "auto_awesome"} size={16} />
            {generating ? "Generating…" : "Generate"}
          </button>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-text-dim">
          Pins are do()-interventions: the pinned value is clamped and only downstream
          attributes react; upstream distributions do not update.
        </p>
        {controlsError ? (
          <p role="alert" className="mt-2 text-xs text-danger">
            {controlsError}
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="mt-2 text-xs text-danger">
            {error.message}
            {error.key ? <span className="font-mono"> ({error.key})</span> : null}
          </p>
        ) : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Typecheck**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend && npm run typecheck
```

Expected: clean (the component is not wired in yet; unused-export warnings do
not exist in this config).

- [ ] **Step 4: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/recipe.ts application/playground/frontend/src/components/synthesis/AdjustGeneratePanel.tsx
git commit -m "Add recipe model and Adjust & Generate panel"
```

---

### Task 8: Results panel — Personas tab with rendered text

**Files:**
- Create: `application/playground/frontend/src/components/synthesis/ResultsPanel.tsx`

**Interfaces:**
- Consumes: `SynthesisSampleResponse`, `api.renderSynthesisPersona` (Task 6); `SynthesisOverviewResponse` for id → label/category grouping.
- Produces:

```tsx
export function ResultsPanel(props: {
  result: SynthesisSampleResponse | null;
  overview: SynthesisOverviewResponse | null;
  pinnedIds: ReadonlySet<string>;             // pin icons on cards
  overlayIndex: number | null;                // Task 11 wires the graphs
  onOverlayIndexChange: (index: number | null) => void;
  overlayEnabled?: boolean;                   // false until Task 11 is complete
}): JSX.Element;
```

Tabs: `Personas` and `Distribution` (Distribution filled in Task 10 — this
task renders its placeholder). Each persona card shows category-grouped
attribute chips and lazily fetches its rendered text when expanded.

- [ ] **Step 1: Create `ResultsPanel.tsx`**

```tsx
/**
 * Panel 5 — "Results": sampled personas as category-grouped cards with
 * lazily rendered natural-language text, plus the baseline-vs-adjusted
 * distribution comparison tab and the graph-overlay selector.
 */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisOverviewResponse, SynthesisSampleResponse } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpit/cockpitShared";
import { DistributionCompare } from "./DistributionCompare";

type TabId = "personas" | "distribution";
const PERSONAS_PER_PAGE = 10;

function personaCacheKey(persona: Record<string, string>): string {
  return JSON.stringify(
    Object.entries(persona).sort(([left], [right]) => left.localeCompare(right)),
  );
}

/** id → {label, category} lookup built from the overview payload. */
function useAttributeIndex(overview: SynthesisOverviewResponse | null) {
  return useMemo(() => {
    const index = new Map<string, { label: string; category: string }>();
    for (const category of overview?.categories ?? []) {
      for (const attribute of category.attributes) {
        index.set(attribute.id, { label: attribute.label, category: category.name });
      }
    }
    return index;
  }, [overview]);
}

function PersonaCard({
  persona,
  index,
  attributeIndex,
  pinnedIds,
  overlayActive,
  onToggleOverlay,
  overlayEnabled,
}: {
  persona: Record<string, string>;
  index: number;
  attributeIndex: Map<string, { label: string; category: string }>;
  pinnedIds: ReadonlySet<string>;
  overlayActive: boolean;
  onToggleOverlay: () => void;
  overlayEnabled: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const cacheKey = useMemo(() => personaCacheKey(persona), [persona]);
  const textQuery = useQuery({
    queryKey: ["synthesis", "render", cacheKey],
    queryFn: () => api.renderSynthesisPersona(persona),
    enabled: expanded,
    staleTime: Infinity,
  });

  const grouped = useMemo(() => {
    const groups = new Map<string, { id: string; label: string; value: string }[]>();
    for (const [id, value] of Object.entries(persona)) {
      const meta = attributeIndex.get(id);
      const category = meta?.category ?? "Other";
      const bucket = groups.get(category) ?? [];
      bucket.push({ id, label: meta?.label ?? id, value });
      groups.set(category, bucket);
    }
    return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right));
  }, [persona, attributeIndex]);
  const [openCategories, setOpenCategories] = useState<Set<string>>(
    () =>
      new Set(
        grouped
          .filter(([, attributes]) => attributes.some((item) => pinnedIds.has(item.id)))
          .map(([category]) => category),
      ),
  );

  const toggleCategory = (category: string) => {
    setOpenCategories((previous) => {
      const next = new Set(previous);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  };

  return (
    <li
      data-testid="synthesis-persona-card"
      className="rounded-lg border border-outline-dim bg-surface-low/50"
      style={{ contentVisibility: "auto", containIntrinsicSize: "240px" }}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        <span className="hud text-text-dim">Persona #{index + 1}</span>
        <span className="min-w-0 flex-1" />
        {overlayEnabled ? (
          <button
            type="button"
            onClick={onToggleOverlay}
            aria-pressed={overlayActive}
            className={`flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors motion-reduce:transition-none ${
              overlayActive
                ? "bg-primary/15 text-primary"
                : "text-text-dim hover:bg-surface hover:text-text-main"
            } ${FOCUS_RING}`}
          >
            <Sym name="layers" size={13} />
            {overlayActive ? "Overlaying" : "Overlay"}
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => setExpanded((previous) => !previous)}
          aria-expanded={expanded}
          className={`flex items-center gap-1 rounded px-2 py-1 text-[11px] text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
        >
          <Sym name={expanded ? "expand_less" : "notes"} size={13} />
          {expanded ? "Hide text" : "Text"}
        </button>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-2 px-3 pb-3">
        {grouped.map(([category, attributes]) => (
          <div key={category} className="min-w-[180px] max-w-full flex-1">
            <button
              type="button"
              aria-expanded={openCategories.has(category)}
              onClick={() => toggleCategory(category)}
              className={`hud mb-0.5 flex w-full items-center justify-between rounded text-left text-[9px] text-text-dim ${FOCUS_RING}`}
            >
              <span>{category}</span>
              <span>{attributes.length}</span>
            </button>
            {openCategories.has(category) ? (
              <ul className="space-y-0.5">
                {attributes.map((attribute) => (
                  <li key={attribute.id} className="flex items-baseline gap-1.5 text-[11px]">
                    {pinnedIds.has(attribute.id) ? (
                      <>
                        <Sym name="push_pin" size={11} className="translate-y-0.5 text-warn" />
                        <span className="sr-only">Pinned.</span>
                      </>
                    ) : null}
                    <span className="truncate text-text-dim" title={attribute.id}>
                      {attribute.label}
                    </span>
                    <span className="truncate font-mono text-text-variant" title={attribute.value}>
                      {attribute.value}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ))}
      </div>
      {expanded ? (
        <div className="border-t border-outline-dim px-3 py-2 text-xs leading-relaxed text-text-variant">
          {textQuery.isError ? (
            <span className="text-danger">Failed to render text.</span>
          ) : !textQuery.data ? (
            "Rendering…"
          ) : (
            <span className="whitespace-pre-line">{textQuery.data.text}</span>
          )}
        </div>
      ) : null}
    </li>
  );
}

export function ResultsPanel({
  result,
  overview,
  pinnedIds,
  overlayIndex,
  onOverlayIndexChange,
  overlayEnabled = false,
}: {
  result: SynthesisSampleResponse | null;
  overview: SynthesisOverviewResponse | null;
  pinnedIds: ReadonlySet<string>;
  overlayIndex: number | null;
  onOverlayIndexChange: (index: number | null) => void;
  overlayEnabled?: boolean;
}) {
  const [tab, setTab] = useState<TabId>("personas");
  const [page, setPage] = useState(0);
  const attributeIndex = useAttributeIndex(overview);
  useEffect(() => {
    setTab("personas");
    setPage(0);
  }, [result]);

  if (!result) {
    return (
      <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
        Generate a batch in the panel above to see personas here.
      </div>
    );
  }

  const tabs: readonly (readonly [TabId, string])[] = result.baselineMarginals
    ? [
        ["personas", `Personas (${result.personas.length})`],
        ["distribution", "Distribution"],
      ]
    : [["personas", `Personas (${result.personas.length})`]];
  const activeTab = tab === "distribution" && !result.baselineMarginals ? "personas" : tab;
  const totalPages = Math.max(1, Math.ceil(result.personas.length / PERSONAS_PER_PAGE));
  const safePage = Math.min(page, totalPages - 1);
  const pageStart = safePage * PERSONAS_PER_PAGE;
  const visiblePersonas = result.personas.slice(
    pageStart,
    pageStart + PERSONAS_PER_PAGE,
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div role="tablist" className="flex flex-none items-center gap-1 border-b border-outline-dim px-3 py-2">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            id={`synthesis-results-tab-${id}`}
            type="button"
            role="tab"
            aria-selected={activeTab === id}
            aria-controls={`synthesis-results-panel-${id}`}
            onClick={() => setTab(id)}
            className={`rounded-md px-3 py-1.5 text-xs transition-colors motion-reduce:transition-none ${
              activeTab === id
                ? "bg-primary/15 text-primary"
                : "text-text-dim hover:bg-surface hover:text-text-main"
            } ${FOCUS_RING}`}
          >
            {label}
          </button>
        ))}
        {overlayEnabled && overlayIndex !== null ? (
          <button
            type="button"
            onClick={() => onOverlayIndexChange(null)}
            className={`ml-auto flex items-center gap-1 rounded px-2 py-1 text-[11px] text-primary transition-colors hover:bg-primary/10 motion-reduce:transition-none ${FOCUS_RING}`}
          >
            <Sym name="layers_clear" size={13} />
            Clear overlay (#{overlayIndex + 1})
          </button>
        ) : null}
      </div>
      <div
        id={`synthesis-results-panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`synthesis-results-tab-${activeTab}`}
        className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-3"
      >
        {activeTab === "personas" ? (
          <>
            <ul className="space-y-2">
              {visiblePersonas.map((persona, localIndex) => {
                const index = pageStart + localIndex;
                const cacheKey = personaCacheKey(persona);
                return (
                  <PersonaCard
                    key={`${index}:${cacheKey}`}
                    persona={persona}
                    index={index}
                    attributeIndex={attributeIndex}
                    pinnedIds={pinnedIds}
                    overlayActive={overlayIndex === index}
                    overlayEnabled={overlayEnabled}
                    onToggleOverlay={() =>
                      onOverlayIndexChange(overlayIndex === index ? null : index)
                    }
                  />
                );
              })}
            </ul>
            {totalPages > 1 ? (
              <nav aria-label="Persona result pages" className="mt-3 flex items-center justify-center gap-3">
                <button
                  type="button"
                  disabled={safePage === 0}
                  onClick={() => setPage(safePage - 1)}
                  className={`rounded px-2 py-1 text-xs disabled:opacity-40 ${FOCUS_RING}`}
                >
                  Previous
                </button>
                <span className="font-mono text-[11px] text-text-dim">
                  {pageStart + 1}–{Math.min(pageStart + PERSONAS_PER_PAGE, result.personas.length)} of {result.personas.length}
                </span>
                <button
                  type="button"
                  disabled={safePage >= totalPages - 1}
                  onClick={() => setPage(safePage + 1)}
                  className={`rounded px-2 py-1 text-xs disabled:opacity-40 ${FOCUS_RING}`}
                >
                  Next
                </button>
              </nav>
            ) : null}
          </>
        ) : (
          <DistributionCompare result={result} />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create the Distribution placeholder (completed in Task 10)**

Create `application/playground/frontend/src/components/synthesis/DistributionCompare.tsx`:

```tsx
/** Baseline-vs-adjusted marginal comparison (rows filled in by Task 10). */
import type { SynthesisSampleResponse } from "@/lib/types";

export function DistributionCompare({ result }: { result: SynthesisSampleResponse }) {
  if (!result.baselineMarginals) {
    return (
      <p className="px-3 py-4 text-sm text-text-dim">
        Enable “compare with baseline” before generating to see distribution shifts.
      </p>
    );
  }
  return (
    <p className="px-3 py-4 text-sm text-text-dim">
      Distribution comparison arrives with the next task.
    </p>
  );
}
```

- [ ] **Step 3: Typecheck**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend && npm run typecheck
```

Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/ResultsPanel.tsx application/playground/frontend/src/components/synthesis/DistributionCompare.tsx
git commit -m "Add Results panel with persona cards and lazy rendered text"
```

---

### Task 9: Wire panels + recipe entry points into the Studio view

**Files:**
- Modify: `application/playground/frontend/src/components/synthesis/SynthesisStudioView.tsx`
- Modify: `application/playground/frontend/src/components/synthesis/NodeDetailRail.tsx`
- Modify: `application/playground/frontend/src/components/synthesis/CategoryAttributeList.tsx`
- Modify: `application/playground/frontend/src/components/studio/StudioShell.tsx`

**Interfaces:**
- Consumes: everything from Tasks 6–8.
- Produces: `NodeDetailRail` gains optional props `onPinValue?: (nodeId: string, label: string, value: string) => void`, `onAdjustPrior?: (nodeId: string, label: string, values: string[], prior: number[]) => void`, `onAdjustEdge?: (source: string, target: string, sourceLabel: string, targetLabel: string) => void`; `CategoryAttributeList` gains `onAdjustCategory?: (name: string) => void`. All default to undefined (rail stays read-only where not wired).

- [ ] **Step 1: Add entry points to `NodeDetailRail.tsx`**

Extend the `EdgeList` helper and component props. Full replacement of the two
signatures and the relevant JSX:

```tsx
function EdgeList({
  title,
  edges,
  onJumpToNode,
  onAdjustEdge,
}: {
  title: string;
  edges: SynthesisNodeEdgeView[];
  onJumpToNode: (id: string) => void;
  onAdjustEdge?: (edgeId: string, edgeLabel: string) => void;
}) {
  if (edges.length === 0) return null;
  return (
    <div>
      <div className="hud mb-1 text-text-dim">{title}</div>
      <ul className="space-y-0.5">
        {edges.map((edge) => (
          <li key={edge.id} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onJumpToNode(edge.id)}
              className={`flex min-w-0 flex-1 items-baseline justify-between gap-2 rounded px-2 py-1 text-left transition-colors hover:bg-surface-low motion-reduce:transition-none ${FOCUS_RING}`}
            >
              <span className="min-w-0 truncate text-xs text-text-variant">{edge.label}</span>
              <span className="flex-none font-mono text-[10px] text-text-dim">
                w {edge.weight}
              </span>
            </button>
            {onAdjustEdge ? (
              <button
                type="button"
                aria-label={`Adjust weight for edge with ${edge.label}`}
                title="Adjust edge weight"
                onClick={() => onAdjustEdge(edge.id, edge.label)}
                className={`grid h-6 w-6 flex-none place-items-center rounded text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
              >
                <Sym name="tune" size={13} />
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

(`Sym` joins the existing `FOCUS_RING` import from `../cockpit/cockpitShared`.)

`NodeDetailRail` props gain the three optional callbacks:

```tsx
export function NodeDetailRail({
  nodeId,
  onJumpToNode,
  onPinValue,
  onAdjustPrior,
  onAdjustEdge,
}: {
  nodeId: string;
  onJumpToNode: (id: string) => void;
  onPinValue?: (nodeId: string, label: string, value: string) => void;
  onAdjustPrior?: (nodeId: string, label: string, values: string[], prior: number[]) => void;
  onAdjustEdge?: (source: string, target: string, sourceLabel: string, targetLabel: string) => void;
}) {
```

In the "Base prior" block: add a Pin button per value row (after the percent
span, only when `onPinValue` is set):

```tsx
                  {onPinValue ? (
                    <button
                      type="button"
                      aria-label={`Pin ${detail.label} to ${value}`}
                      title="Pin this value"
                      onClick={() => onPinValue(detail.id, detail.label, value)}
                      className={`grid h-6 w-6 flex-none place-items-center rounded text-text-dim transition-colors hover:bg-surface hover:text-primary motion-reduce:transition-none ${FOCUS_RING}`}
                    >
                      <Sym name="push_pin" size={13} />
                    </button>
                  ) : null}
```

and an "Adjust prior" button next to the "Base prior" heading:

```tsx
          <div className="mb-1 flex items-center justify-between">
            <div className="hud text-text-dim">Base prior</div>
            {onAdjustPrior ? (
              <button
                type="button"
                onClick={() =>
                  onAdjustPrior(detail.id, detail.label, detail.values, detail.prior)
                }
                className={`rounded px-1.5 py-0.5 text-[10px] text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
              >
                Adjust prior
              </button>
            ) : null}
          </div>
```

The two `EdgeList` call sites pass direction-correct adjust callbacks:

```tsx
      <EdgeList
        title="Strongest incoming"
        edges={detail.inEdges}
        onJumpToNode={onJumpToNode}
        onAdjustEdge={
          onAdjustEdge
            ? (edgeId, edgeLabel) => onAdjustEdge(edgeId, detail.id, edgeLabel, detail.label)
            : undefined
        }
      />
      <EdgeList
        title="Strongest outgoing"
        edges={detail.outEdges}
        onJumpToNode={onJumpToNode}
        onAdjustEdge={
          onAdjustEdge
            ? (edgeId, edgeLabel) => onAdjustEdge(detail.id, edgeId, detail.label, edgeLabel)
            : undefined
        }
      />
```

(Incoming rows are `other → this`; outgoing rows are `this → other`.)

- [ ] **Step 2: Add the category-influence entry point to `CategoryAttributeList.tsx`**

Props gain `onAdjustCategory?: (name: string) => void`; add a button in the
header block under the counts paragraph:

```tsx
        {onAdjustCategory ? (
          <button
            type="button"
            onClick={() => onAdjustCategory(category.name)}
            className={`mt-1.5 flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
          >
            <Sym name="tune" size={13} />
            Influence ×
          </button>
        ) : null}
```

(import `Sym` next to `FOCUS_RING`.)

- [ ] **Step 3: Wire everything in `SynthesisStudioView.tsx`**

Add imports:

```tsx
import { useMutation } from "@tanstack/react-query";
import { useMemo } from "react";
import type { SynthesisSampleResponse } from "@/lib/types";
import { ApiError } from "@/lib/api";
import { AdjustGeneratePanel } from "./AdjustGeneratePanel";
import { ResultsPanel } from "./ResultsPanel";
import {
  DEFAULT_CONTROLS,
  buildSampleRequest,
  recipeKey,
  recipeKeyForErrorKey,
  upsertEntry,
  type RecipeEntry,
  type SamplingControls,
} from "./recipe";
```

Add state + mutation inside the component (after the existing `useState`
block):

```tsx
  const [recipe, setRecipe] = useState<RecipeEntry[]>([]);
  const [controls, setControls] = useState<SamplingControls>(DEFAULT_CONTROLS);
  const [result, setResult] = useState<SynthesisSampleResponse | null>(null);
  const [overlayIndex, setOverlayIndex] = useState<number | null>(null);
  const sampleMutation = useMutation({
    mutationFn: () => api.sampleSynthesis(buildSampleRequest(recipe, controls)),
    onSuccess: (body) => {
      setResult(body);
      setOverlayIndex(null);
    },
  });
  const upsert = (entry: RecipeEntry) => setRecipe((previous) => upsertEntry(previous, entry));
  const removeEntry = (key: string) =>
    setRecipe((previous) => previous.filter((entry) => recipeKey(entry) !== key));
  const sampleError = (() => {
    const raw = sampleMutation.error;
    if (!raw) return null;
    if (raw instanceof ApiError && raw.detail && typeof raw.detail === "object") {
      const detail = raw.detail as { message?: string; key?: string };
      return {
        message: detail.message ?? raw.message,
        key: detail.key ? recipeKeyForErrorKey(detail.key) : null,
      };
    }
    return { message: raw instanceof Error ? raw.message : "Sampling failed", key: null };
  })();
  const resultPinnedIds = useMemo(
    () => new Set(Object.keys(result?.effectiveConfig.pins ?? {})),
    [result],
  );
```

Pass the entry points to the Details panel children:

- Compute whether the selected category has at least one outgoing pairwise edge:

```tsx
  const selectedCategoryHasOutgoing =
    selectedCategoryData !== null &&
    (selectedCategoryData.internalEdgeCount > 0 ||
      (overview?.edges.some((edge) => edge.source === selectedCategoryData.name) ?? false));
```

  `CategoryAttributeList` gains `onAdjustCategory` only when that boolean is
  true; categories with no outgoing proposal edge must not offer a no-op slider:

```tsx
onAdjustCategory={
  selectedCategoryHasOutgoing
    ? (name) => upsert({ kind: "category", category: name, factor: 1 })
    : undefined
}
```
- `NodeDetailRail` gains:

```tsx
                    onPinValue={(nodeId, label, value) =>
                      upsert({ kind: "pin", nodeId, label, value })
                    }
                    onAdjustPrior={(nodeId, label, values, prior) =>
                      upsert({ kind: "prior", nodeId, label, values, weights: [...prior] })
                    }
                    onAdjustEdge={(source, target, sourceLabel, targetLabel) =>
                      upsert({ kind: "edge", source, target, sourceLabel, targetLabel, factor: 1 })
                    }
```

Append the two panels after the Details `ExpandableStudioPanel` (inside the
same `flex flex-col gap-4` container):

```tsx
          <ExpandableStudioPanel title="Adjust & Generate">
            <AdjustGeneratePanel
              recipe={recipe}
              onUpsert={upsert}
              onRemove={removeEntry}
              controls={controls}
              onControlsChange={setControls}
              onGenerate={() => sampleMutation.mutate()}
              generating={sampleMutation.isPending}
              error={sampleError}
              helperPins={result?.flags.helperPins ?? []}
            />
          </ExpandableStudioPanel>
          <ExpandableStudioPanel title="Results">
            <ResultsPanel
              result={result}
              overview={overview}
              pinnedIds={resultPinnedIds}
              overlayIndex={overlayIndex}
              onOverlayIndexChange={setOverlayIndex}
            />
          </ExpandableStudioPanel>
```

Finally, update the existing `ExpandableStudioPanel` JS scroll so the global
reduced-motion requirement also covers `scrollIntoView`:

```tsx
                    const reduceMotion = window.matchMedia(
                      "(prefers-reduced-motion: reduce)",
                    ).matches;
                    rootRef.current?.scrollIntoView({
                      block: "nearest",
                      behavior: reduceMotion ? "auto" : "smooth",
                    });
```

(Replace the existing unconditional `behavior: "smooth"` call.)

- [ ] **Step 4: Build**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend && npm run build
```

Expected: typecheck + vite build succeed.

- [ ] **Step 5: Runtime smoke check**

Run the backend from the repo root with
`PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground .venv/bin/python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8766 --workers 1`,
then drive `http://127.0.0.1:8766/?view=synthesis`: click a category →
click an attribute → in Details press a Pin button → the recipe row appears →
press Generate → persona cards appear. Fix anything broken before committing.

- [ ] **Step 6: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/ application/playground/frontend/src/components/studio/StudioShell.tsx
git commit -m "Wire Adjust & Generate and Results panels into the Synthesis Studio"
```

---

### Task 10: Distribution comparison tab

**Files:**
- Modify: `application/playground/frontend/src/components/synthesis/DistributionCompare.tsx` (replace placeholder body)

**Interfaces:**
- Consumes: `SynthesisSampleResponse.marginals` / `baselineMarginals` (Task 6 types).
- Behavior per spec: only attributes with total variation distance (TVD) > 0.01 appear, sorted by TVD descending; each row shows per-value baseline vs adjusted bars.

- [ ] **Step 1: Implement the comparison**

Replace the file contents:

```tsx
/**
 * Baseline-vs-adjusted marginal comparison. TVD = 0.5 * Σ|p - q| per
 * attribute; rows with TVD > 0.01 render, sorted most-shifted first.
 */
import { useMemo } from "react";

import type { SynthesisSampleResponse } from "@/lib/types";

const TVD_THRESHOLD = 0.01;

interface ShiftRow {
  id: string;
  label: string;
  values: string[];
  baseline: number[];
  adjusted: number[];
  tvd: number;
}

function Bar({ share, muted }: { share: number; muted: boolean }) {
  return (
    <span className="h-1.5 min-w-0 flex-1 rounded-sm bg-surface-high" aria-hidden="true">
      <span
        className="block h-full rounded-sm"
        style={{
          width: `${Math.round(share * 100)}%`,
          background: muted ? "rgb(var(--outline))" : "rgb(var(--primary) / 0.65)",
        }}
      />
    </span>
  );
}

export function DistributionCompare({ result }: { result: SynthesisSampleResponse }) {
  const rows = useMemo<ShiftRow[]>(() => {
    const baseline = result.baselineMarginals;
    if (!baseline) return [];
    const shifted: ShiftRow[] = [];
    for (const [id, adjusted] of Object.entries(result.marginals)) {
      const base = baseline[id];
      if (!base) continue;
      const tvd =
        0.5 *
        adjusted.freqs.reduce(
          (sum, freq, index) => sum + Math.abs(freq - (base.freqs[index] ?? 0)),
          0,
        );
      if (tvd <= TVD_THRESHOLD) continue;
      shifted.push({
        id,
        label: adjusted.label,
        values: adjusted.values,
        baseline: base.freqs,
        adjusted: adjusted.freqs,
        tvd,
      });
    }
    return shifted.sort((left, right) => right.tvd - left.tvd);
  }, [result]);

  if (!result.baselineMarginals) {
    return (
      <p className="px-3 py-4 text-sm text-text-dim">
        Enable “compare with baseline” before generating to see distribution shifts.
      </p>
    );
  }
  if (rows.length === 0) {
    return (
      <p className="px-3 py-4 text-sm text-text-dim">
        No attribute shifted by more than {TVD_THRESHOLD} total variation distance.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-[11px] text-text-dim">
        {rows.length} attributes shifted (TVD &gt; {TVD_THRESHOLD}), most affected first.
        Grey bars: baseline · cyan bars: adjusted.
      </p>
      {rows.map((row) => (
        <section key={row.id} className="rounded-lg border border-outline-dim bg-surface-low/50 p-3">
          <div className="mb-1.5 flex items-baseline justify-between gap-2">
            <h4 className="min-w-0 truncate text-xs text-text-main" title={row.id}>
              {row.label}
            </h4>
            <span className="flex-none font-mono text-[10px] text-text-dim">
              TVD {row.tvd.toFixed(3)}
            </span>
          </div>
          <ul className="space-y-1">
            {row.values.map((value, index) => {
              const base = row.baseline[index] ?? 0;
              const adjusted = row.adjusted[index] ?? 0;
              const delta = adjusted - base;
              return (
                <li key={value} className="flex items-center gap-2 text-[11px]">
                  <span className="w-28 flex-none truncate text-text-variant" title={value}>
                    {value}
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <Bar share={base} muted />
                    <Bar share={adjusted} muted={false} />
                  </span>
                  <span className="w-24 flex-none text-right font-mono text-[10px] text-text-dim">
                    {(base * 100).toFixed(1)}% → {(adjusted * 100).toFixed(1)}%
                    {delta === 0 ? null : (
                      <span className={delta > 0 ? "text-primary" : "text-danger"}>
                        {" "}
                        {delta > 0 ? "↑" : "↓"}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

(`text-primary` and `text-danger` are existing Tailwind tokens; unchanged
values intentionally have no direction arrow.)

- [ ] **Step 2: Build + runtime check**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend && npm run build
```

Then in the running app: pin a value, Generate with baseline compare on, open
the Distribution tab — shifted attributes appear with paired bars.

- [ ] **Step 3: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/DistributionCompare.tsx
git commit -m "Add baseline-vs-adjusted distribution comparison tab"
```

---

### Task 11: Graph overlay

**Files:**
- Modify: `application/playground/frontend/src/components/synthesis/DrilldownGraph.tsx`
- Modify: `application/playground/frontend/src/components/synthesis/CategoryOverviewGraph.tsx`
- Modify: `application/playground/frontend/src/components/synthesis/SynthesisStudioView.tsx`

**Interfaces:**
- `DrilldownGraph` gains `overlay?: Record<string, string> | null` and `pinnedIds?: ReadonlySet<string>`: when `overlay` is set, each node box swaps its id line for the sampled value (primary color); pinned nodes get a warn-colored border.
- `CategoryOverviewGraph` gains `overlay?: Record<string, string> | null` and `pinnedCategories?: ReadonlySet<string>`: categories containing pinned attributes render a dashed warn-colored ring, and every category with sampled attributes shows a short `label: value` preview beside its category label. The SVG accessible label includes the full overlay count and pinned state.

- [ ] **Step 1: Extend `DrilldownGraph`**

Props:

```tsx
export function DrilldownGraph({
  subgraph,
  selectedNode,
  onSelectNode,
  onRecenter,
  overlay = null,
  pinnedIds,
}: {
  subgraph: SynthesisSubgraphResponse;
  selectedNode: string | null;
  onSelectNode: (id: string) => void;
  onRecenter: (id: string) => void;
  overlay?: Record<string, string> | null;
  pinnedIds?: ReadonlySet<string>;
}) {
```

In the node render block, before the `return`:

```tsx
          const overlayValue = overlay ? overlay[node.id] : undefined;
          const isPinned = pinnedIds?.has(node.id) ?? false;
          const accessibleLabel = `${node.label} (${node.category}) — in ${node.inDegree} / out ${node.outDegree}${node.emit ? "" : " · latent/helper"}${isCenter ? " · current center" : ""}${overlayValue !== undefined ? ` · sampled value ${overlayValue}` : ""}${isPinned ? " · pinned in this result" : ""}. Double-click or press Shift+Enter to recenter.`;
```

(This replaces the existing `accessibleLabel` declaration; do not leave both.)

Change the node `<rect>` `stroke` style value to:

```tsx
                  stroke: isPinned
                    ? "rgb(var(--warn))"
                    : isSelected || isCenter || isFocus
                      ? "rgb(var(--primary))"
                      : "rgb(var(--outline))",
```

and the second `<text>` (the id line) to:

```tsx
              <text
                x={position.x + 10}
                y={position.y + 31}
                className="font-mono"
                style={{
                  fontSize: 9.5,
                  fill:
                    overlayValue !== undefined
                      ? "rgb(var(--primary))"
                      : "rgb(var(--text-dim))",
                }}
              >
                {overlayValue !== undefined ? truncate(overlayValue) : truncate(node.id)}
              </text>
```

- [ ] **Step 2: Extend `CategoryOverviewGraph`**

Props gain `overlay?: Record<string, string> | null` (default `null`) and
`pinnedCategories?: ReadonlySet<string>`. In the category-node map, derive a
visible preview before the `return`:

```tsx
          const summary = overview.categories.find((item) => item.name === category.name);
          const overlayItems = overlay
            ? (summary?.attributes ?? []).flatMap((attribute) => {
                const value = overlay[attribute.id];
                return value === undefined ? [] : [`${attribute.label}: ${value}`];
              })
            : [];
          const fullOverlayPreview = overlayItems.join(" · ");
          const overlayPreview =
            fullOverlayPreview.length > 32
              ? `${fullOverlayPreview.slice(0, 31)}…`
              : fullOverlayPreview;
          const isPinnedCategory = pinnedCategories?.has(category.name) ?? false;
          const accessiblePreview = overlayItems.slice(0, 8).join(" · ");
          const accessibleLabel = `${category.name} — ${category.attributeCount} attributes / ${category.nodeCount} nodes${overlayItems.length ? ` · ${overlayItems.length} sampled values: ${accessiblePreview}${overlayItems.length > 8 ? " · more values omitted" : ""}` : ""}${isPinnedCategory ? " · contains pinned attributes" : ""}`;
```

(Replace the existing `accessibleLabel` declaration.) After the main visible
`<circle>` add:

```tsx
              {isPinnedCategory ? (
                <circle
                  cx={category.x}
                  cy={category.y}
                  r={category.r + 3.5}
                  fill="none"
                  pointerEvents="none"
                  style={{
                    stroke: "rgb(var(--warn))",
                    strokeWidth: 1.4,
                    strokeDasharray: "3 3",
                  }}
                />
              ) : null}
```

After the existing category-label `<text>`, render the actual sampled preview:

```tsx
              {overlayPreview ? (
                <text
                  x={category.labelX}
                  y={category.labelY + 12}
                  textAnchor={category.labelSide === "left" ? "start" : "end"}
                  className="font-mono"
                  pointerEvents="none"
                  style={{ fontSize: 8.5, fill: "rgb(var(--primary))" }}
                >
                  {overlayPreview}
                </text>
              ) : null}
```

- [ ] **Step 3: Wire overlay state through `SynthesisStudioView`**

Compute below the recipe helpers:

```tsx
  const overlayValues =
    overlayIndex !== null && result ? result.personas[overlayIndex] ?? null : null;
  const pinnedCategories = useMemo(() => {
    if (!overview) return new Set<string>();
    const byAttribute = new Map<string, string>();
    for (const category of overview.categories) {
      for (const attribute of category.attributes) byAttribute.set(attribute.id, category.name);
    }
    return new Set(
      [...resultPinnedIds].flatMap((id) => {
        const name = byAttribute.get(id);
        return name ? [name] : [];
      }),
    );
  }, [overview, resultPinnedIds]);
```

`resultPinnedIds` was defined in Task 9 from `result.effectiveConfig.pins`; do
not derive result decoration from the live recipe.

Pass `overlay={overlayValues}` and `pinnedIds={resultPinnedIds}` to
`DrilldownGraph`; pass `overlay={overlayValues}` and
`pinnedCategories={pinnedCategories}` to `CategoryOverviewGraph`; pass
`overlayEnabled` to `ResultsPanel` so its Overlay controls become visible only
in this independently mergeable stage.

- [ ] **Step 4: Build + runtime check**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend && npm run build
```

In the app: generate, press “Overlay” on a persona card → drill-down node
boxes show sampled values in cyan, pinned node border turns warn-colored,
overview shows sampled `label: value` previews plus dashed rings on pinned
categories; accessible SVG labels announce both states; “Clear overlay” restores.

- [ ] **Step 5: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/
git commit -m "Overlay sampled persona values onto the synthesis graphs"
```

---

### Task 12: Reproducible Playwright acceptance + full verification

**Files:**
- Modify: `application/playground/frontend/package.json`
- Modify: `application/playground/frontend/package-lock.json`
- Create: `application/playground/frontend/playwright.config.ts`
- Create: `application/playground/frontend/e2e/synthesis-adjust-generate.spec.ts`
- Create at test runtime: `docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate/*.png`

- [ ] **Step 1: Add the dev-only Playwright dependency and scripts**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend
npm install --save-dev @playwright/test@1.61.0
npx playwright install chromium
```

Add these scripts to `package.json`:

```json
"test:e2e:synthesis": "npm run build && playwright test e2e/synthesis-adjust-generate.spec.ts",
"test:e2e:synthesis:headed": "npm run build && playwright test e2e/synthesis-adjust-generate.spec.ts --headed"
```

Expected: the dependency is dev-only and does not enter the Vite production
bundle; `package-lock.json` records the exact resolved version.

- [ ] **Step 2: Create the Playwright config**

```ts
// application/playground/frontend/playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8766",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command:
      "PYTHONPATH=../../..:../../../environment/runtime:../../../packages/playground/src:.. ../../../.venv/bin/python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8766 --workers 1",
    url: "http://127.0.0.1:8766/api/health",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
  },
});
```

- [ ] **Step 3: Write the executable acceptance test**

```ts
// application/playground/frontend/e2e/synthesis-adjust-generate.spec.ts
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const shots = path.resolve(
  here,
  "../../../../docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate",
);

test("pin, scale, generate, compare, render, overlay, and preserve results on error", async ({
  page,
}) => {
  mkdirSync(shots, { recursive: true });
  await page.goto("/?view=synthesis");

  await page.getByRole("button", { name: /^Demographic: Core —/ }).click();
  await page.getByRole("button", { name: /^Region\b/ }).click();
  await page.getByRole("button", { name: "Pin Region to North America" }).click();
  await page.getByRole("button", { name: /back to category list/i }).click();

  await page.getByRole("button", { name: /^Age bracket\b/ }).click();
  await page.getByRole("button", { name: "Pin Age bracket to 25-34" }).click();
  await page.getByRole("button", { name: /back to category list/i }).click();
  await page.getByRole("button", { name: "Influence ×" }).click();
  const influence = page.getByRole("slider", {
    name: "Influence of Demographic: Core",
  });
  await influence.focus();
  await influence.press("Home");
  for (let step = 0; step < 20; step += 1) await influence.press("ArrowRight");
  await expect(
    page.getByTestId("synthesis-recipe-entry").filter({ hasText: "Demographic: Core" }),
  ).toContainText("2.0×");

  await page.getByRole("spinbutton", { name: "Personas" }).fill("50");
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("tab", { name: "Personas (50)" })).toBeVisible();
  await expect(page.getByText("1–10 of 50")).toBeVisible();
  await page.screenshot({ path: path.join(shots, "1-adjust-generate.png"), fullPage: true });

  for (let resultPage = 0; resultPage < 5; resultPage += 1) {
    const cards = page.getByTestId("synthesis-persona-card");
    await expect(cards).toHaveCount(10);
    for (let cardIndex = 0; cardIndex < 10; cardIndex += 1) {
      const card = cards.nth(cardIndex);
      await expect(card.getByTitle("North America", { exact: true })).toBeVisible();
      await expect(card.getByTitle("25-34", { exact: true })).toBeVisible();
    }
    if (resultPage < 4) await page.getByRole("button", { name: "Next" }).click();
  }

  await page.getByRole("tab", { name: "Distribution" }).click();
  const tvdLabels = page.getByText(/^TVD 0\./);
  await expect(tvdLabels.first()).toBeVisible();
  const tvds = await tvdLabels.allTextContents();
  const values = tvds.map((text) => Number(text.replace("TVD ", "")));
  expect(values).toEqual([...values].sort((left, right) => right - left));
  await page.screenshot({ path: path.join(shots, "2-distribution.png"), fullPage: true });

  await page.getByRole("tab", { name: "Personas (50)" }).click();
  for (let pageIndex = 0; pageIndex < 4; pageIndex += 1) {
    await page.getByRole("button", { name: "Previous" }).click();
  }
  const firstCard = page.getByTestId("synthesis-persona-card").first();
  await page.getByRole("button", { name: "Remove pin on Region" }).click();
  await expect(firstCard.getByText("Pinned.")).toHaveCount(2);
  await expect(firstCard.getByTitle("North America", { exact: true })).toBeVisible();
  await firstCard.getByRole("button", { name: "Text" }).click();
  await expect(firstCard.getByText(/^A persona /)).toBeVisible();
  await firstCard.getByRole("button", { name: "Overlay" }).click();
  await expect(
    page.getByRole("button", { name: /Age bracket.*sampled value 25-34/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Demographic: Core.*sampled values/ }),
  ).toBeVisible();
  await page.screenshot({ path: path.join(shots, "3-overlay.png"), fullPage: true });

  await page.route("**/api/synthesis/sample", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "sampling temporarily unavailable" }),
    });
  });
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("alert")).toContainText("sampling temporarily unavailable");
  await expect(page.getByRole("tab", { name: "Personas (50)" })).toBeVisible();

  await page.unroute("**/api/synthesis/sample");
  await page.route("**/api/synthesis/sample", async (route) => {
    await route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        message: "unknown category: Demographic: Core",
        key: "overrides.categoryScales.Demographic: Core",
      }),
    });
  });
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("alert")).toContainText("unknown category");
  await expect(
    page.getByTestId("synthesis-recipe-entry").filter({ hasText: "Demographic: Core" }),
  ).toHaveAttribute("data-invalid", "true");

  await page.unroute("**/api/synthesis/sample");
  await page.getByRole("spinbutton", { name: "Personas" }).fill("0");
  await expect(page.getByText("Personas must be an integer between 1 and 200.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate" })).toBeDisabled();
});
```

The test pages through all 50 results instead of mounting 50 × 1,290
attribute rows simultaneously. Pinned categories open by default; other
attribute groups stay lazy.

- [ ] **Step 4: Run the browser acceptance test**

```bash
cd /data2/zonglin/MatrAIx/application/playground/frontend
npm run test:e2e:synthesis
```

Expected: 1 passed; the three named screenshots exist under the spec assets
directory. If this host still needs the documented local `libasound` extracts,
run:

```bash
LD_LIBRARY_PATH=/tmp/pw-libs/usr/lib/x86_64-linux-gnu:/tmp/libasound-local/usr/lib/x86_64-linux-gnu \
  npm run test:e2e:synthesis
```

Do not replace the committed test with an untracked scratch script.

- [ ] **Step 5: Run every suite**

```bash
cd /data2/zonglin/MatrAIx
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/persona/synthesis/ -q
cd application/playground && PYTHONPATH=/data2/zonglin/MatrAIx:/data2/zonglin/MatrAIx/environment/runtime:/data2/zonglin/MatrAIx/packages/playground/src:. \
  /data2/zonglin/MatrAIx/.venv/bin/python -m pytest backend/tests/ -q
cd frontend && npm run build
npm run test:e2e:synthesis
```

Expected: all green.

- [ ] **Step 6: Manually spot-check the remaining recipe entry points**

With the built SPA and backend on port 8766, open `/?view=synthesis` in a
browser and spot-check:

1. Add a prior adjustment, change two weights, and verify its normalized bars.
2. Add an incoming and outgoing edge factor and verify direction-correct recipe keys.
3. Turn baseline comparison off, Generate, and verify the Distribution tab is hidden.
4. Enter an invalid local sampling control and verify Generate disables with a named error.
5. Confirm the automated 422 interception left the category recipe entry with
   `data-invalid="true"`; no graph file mutation is needed.

- [ ] **Step 7: Probe the remaining sad paths**

- Remove a pinned node from the recipe mid-flight? (Remove button → row gone,
  next Generate excludes it.)
- Generate with an empty recipe → pure baseline batch renders.
- A helper-node pin → warning chip appears, but the helper stays omitted from persona cards.

- [ ] **Step 8: Commit verification artifacts and any fixes, then push and open the PR**

Commit the Task 12 screenshots under
`docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate/`, then:

```bash
git add application/playground/frontend/package.json \
  application/playground/frontend/package-lock.json \
  application/playground/frontend/playwright.config.ts \
  application/playground/frontend/e2e/synthesis-adjust-generate.spec.ts \
  docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate/
git commit -m "Add reproducible synthesis Studio acceptance test"
git push -u origin feature/synthesis-adjust-generate
gh pr create --repo MatrAIx-ai/MatrAIx --base feature/persona-dag-studio-phase1 \
  --title "Synthesis Studio: adjust weights and generate personas (Phase 2)" \
  --body-file pr-body.md
```

`pr-body.md` structure (repo is private — embed images with the same-repo
`blob…?raw=true` pattern used in PR #206, not `raw.githubusercontent.com`):

```markdown
## Summary
- Sampler: runtime pins (do()-interventions) + compile-time SamplerOverrides
  (observable post-shrinkage pairwise factors, prior replacements anchored to
  original CPD ratios, gamma scale); no-override output matches a pre-Phase-2
  golden fixture index-for-index.
- API: POST /api/synthesis/sample (baseline compare + server-side marginals),
  POST /api/synthesis/render (stdlib renderer extracted to persona/synthesis/render.py).
- Studio: Adjust & Generate recipe panel, persona cards + rendered text,
  paginated/lazy attribute groups, TVD-sorted distribution comparison, and
  sampled-value overlays on both graphs.

## Screenshots
![Recipe + generate](https://github.com/MatrAIx-ai/MatrAIx/blob/feature/synthesis-adjust-generate/docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate/1-adjust-generate.png?raw=true)
![Distribution shift](https://github.com/MatrAIx-ai/MatrAIx/blob/feature/synthesis-adjust-generate/docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate/2-distribution.png?raw=true)
![Graph overlay](https://github.com/MatrAIx-ai/MatrAIx/blob/feature/synthesis-adjust-generate/docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate/3-overlay.png?raw=true)

## Test plan
- [ ] tests/persona/synthesis (sampler pins/overrides + bit-identical guard)
- [ ] backend/tests (named 422 contract, single-flight cache, category shift,
      and a subprocess that forcibly blocks numpy imports)
- [ ] npm run build
- [ ] npm run test:e2e:synthesis: pin region + age_bracket, scale a category to 2×,
      generate 50, verify cards / distribution / overlay

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

(If PR #206 has merged, use `--base main` and rebase first.)

---

## Self-review notes

- Spec coverage: pins (T2/T4), observable edge/category factors + child/root prior replacements + gamma (T3/T4), `/sample` + `/render` (T5), recipe UI with all four entry kinds (T7/T9), paginated persona cards + query-cached text (T8), TVD distribution compare hidden without a baseline (T10), value overlays on overview + drill-down with result-snapshot pin styling (T11), normalized schema/service 422 keys and recipe highlighting (T5/T7/T12), helper-pin flag chip (T7), forced no-numpy import safety (T4), pre-change golden guard (T2/T3), single-flight LRU cache (T4), executable acceptance scenario (T12).
- Types consistent: `SamplerOverrides` field names match between sampler and service; camelCase API keys match schemas ↔ TS types; `RecipeEntry` keys match `recipeKeyForErrorKey`; all result decorations use `effectiveConfig.pins`, not live recipe state.
- Out of scope (per spec): no persistence, no posterior conditioning, no async sampling, full-CPT weights untouched.

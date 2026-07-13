# Synthesis Studio Adjust + Generate (Phase 2) — Design

Date: 2026-07-12
Status: approved
Parent: docs/superpowers/specs/2026-07-11-persona-dag-studio-design.md (phases 2–3, merged here)
Scope: sampler extension + Playground backend/frontend (`application/playground`)

## Problem

Phase 1 ships read-only browsing of the Persona Full DAG. The user wants to
demonstrate that adjusting the graph — category influence, attribute priors,
pinned values, individual edge weights — produces different sampled personas,
and to preview those personas and the distribution shift directly in the
Synthesis Studio.

## Decision

Extend the existing Synthesis page (approach A, chosen over a separate
generate wizard and over a sliders-only demo build): all four adjustment
types accumulate into one editable **recipe**; Generate samples the adjusted
configuration and, optionally, a same-seed baseline batch for comparison.
Results render in a new stacked panel with three preview modes.

Delivered in three independently mergeable stages:

- **2a** — sampler pins + overrides, `/sample` and `/render` endpoints (backend only)
- **2b** — Adjust & Generate panel, persona cards + rendered text preview
- **2c** — baseline-vs-adjusted distribution comparison, graph value overlay

## Backend

### Sampler extension (`persona/synthesis/sampler/sampler.py`)

- `pins: dict[node_id, value]` — pinned nodes skip sampling and are clamped
  to the given value index; downstream nodes condition on them through the
  normal forward pass. Do()-intervention semantics: upstream distributions do
  not update (unchanged from the parent spec; accepted 2026-07-11).
- `overrides`, all folded in at plan-compile time:
  - `edge_weights: {"src->dst": factor}` — multiplier on the edge's weight.
  - `node_priors: {node_id: [p, ...]}` — full replacement, renormalized
    server-side; length must match the node's value count.
  - `category_scales: {category: factor}` — expands to a multiplier on every
    edge whose **source** node belongs to the category; composes
    multiplicatively with any per-edge factor on the same edge.
  - (global gamma is passed at the top level of the sample request, not
    inside `overrides`.)
- Compiled plans are cached keyed by a stable hash of the override payload;
  the no-override plan is the existing cached path.
- Backward compatibility: with no pins and no overrides, output is
  bit-identical to current behavior for a fixed seed (guarded by test).

### API (`application/playground/backend`)

| Endpoint | Contract |
| --- | --- |
| `POST /api/synthesis/sample` | Body `{n: 1–200, seed, gamma?, pins: {}, overrides: {}, compareBaseline: bool}` → `{personas: [...], baselinePersonas?: [...], marginals: {...}, baselineMarginals?: {...}, effectiveConfig, flags}`. Baseline uses the same seed with empty pins/overrides. Marginals (per-attribute value frequencies over the batch) are computed server-side for both batches. |
| `POST /api/synthesis/render` | Persona attribute map → natural-language text. Reuses the `render()` function in `persona/synthesis/scripts/render_personas.py` (refactor the reusable part into an importable function; the script keeps its CLI). |

Validation: unknown attribute ids, values, categories, or edges anywhere in
`pins`/`overrides` → 422 naming the offending key. Prior arrays with wrong
length or non-positive mass → 422. Pins on `emit:false` helper nodes are
allowed but echoed under `flags.helperPins`. Sampling is synchronous (the
vectorized sampler returns n ≤ 200 in milliseconds).

## Frontend

Two new `ExpandableStudioPanel`s appended to the existing vertical stack
(components live in `src/components/synthesis/`).

### Panel 4 — "Adjust & Generate" (`AdjustGeneratePanel`)

- **Recipe list**: removable entries, one row each —
  - pin chip: `attribute = value [×]`
  - prior editor: per-value numeric inputs with a live normalized bar
  - category slider: 0×–3× influence factor
  - edge multiplier: `src → dst  weight ×[factor]`
- **Sampling controls**: seed, n, optional gamma, `compare with baseline`
  toggle (default on).
- **Generate**: single `.glow` CTA; enabled even with an empty recipe
  (pure baseline sampling). While in flight it disables and shows progress;
  failure keeps the previous results and shows the error inline.
- Recipe state lives in `SynthesisStudioView` (`useState`), not persisted.

### Panel 5 — "Results" (`ResultsPanel`)

- **Personas tab**: sampled personas as category-grouped attribute cards;
  each card expands to its rendered natural-language text (fetched lazily
  via `/render`, cached per persona).
- **Distribution tab**: for attributes whose marginals moved (total
  variation distance > 0.01), side-by-side baseline vs adjusted bars,
  sorted by total variation distance descending;
  hidden when `compareBaseline` was off.
- **Overlay toggle**: stamps one selected persona's values onto the overview
  and drill-down nodes; pinned nodes get a distinct style. Toggle off
  restores the plain graphs.

### Entry points (all of them only append recipe entries; editing happens in Panel 4)

- Details rail: a "Pin" button per value row; an "Adjust prior" button on the
  prior block; a weight-multiplier affordance per row in the strongest-edges
  lists.
- Overview: when a category is selected, the Details panel header shows an
  "Influence ×" slider entry point for that category.

### Error handling

- Recipe entries invalidated by a 422 (e.g. graph changed on disk) are
  highlighted in the recipe list with the server's message.
- `flags.helperPins` renders as a subdued warning chip on the affected entry.

## Out of scope

- Posterior conditioning (pins remain do()-interventions; labeled in the UI).
- Persisting recipes or writing overrides back to `full_dag.json`.
- Async/queued sampling; n stays ≤ 200.

## Testing

- Sampler unit tests (`tests/`): pin semantics; category scale expands to the
  right edge set and composes with per-edge factors; prior replacement
  renormalizes; no-pin/no-override output bit-identical for fixed seed.
- Backend pytest: pinned attribute equals its pin in every sample; a
  downstream marginal shifts under a pin and under a category scale
  (statistical assertion, fixed seed); plan-cache hit/miss; 422 contracts;
  render endpoint contract; baseline echo uses same seed.
- Frontend: `npm run build` typecheck; Playwright runtime walkthrough —
  pin a value from the Details rail, drag a category slider, generate with
  baseline compare, and check all three previews (cards + text, shifted
  distribution rows, overlay stamps values on both graphs).
- Acceptance: in Playground, pin `region` and `age_bracket`, scale one
  category to 2×, generate 50 personas, and see the distribution tab report
  shifted downstream attributes with the overlay reflecting a sample.

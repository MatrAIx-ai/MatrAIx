# Synthesis Studio Vertical Layout — Design

Date: 2026-07-12
Status: approved
Scope: frontend only (`application/playground/frontend`)

## Problem

The Synthesis Studio (Persona DAG Studio) renders its three panes side by side
(`lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)_minmax(0,3fr)]`). Each pane is too
narrow to preview comfortably, especially the graphs.

## Decision

Stack the three panes vertically, full width, in this order:

1. **Category overview** — `CategoryOverviewGraph`
2. **Drill-down** — hops toolbar + `DrilldownGraph`
3. **Details** — `CategoryAttributeList` / `NodeDetailRail`

Each pane is always visible at a medium default height and has an
expand/restore toggle in its header (chosen over accordion and
collapse-to-header alternatives: nothing ever disappears, and the user
controls which pane gets the big view).

## Components

### `ExpandableStudioPanel` (new, in `studio/StudioShell.tsx`)

Props: `title: string`, `children`, optional `className`.

- Wraps `StudioGlassPanel`; renders a header bar (title on the left, a
  single icon button on the right) above the body.
- Icon button uses the existing `Sym` component: `expand_content` when
  collapsed, `collapse_content` when expanded; `aria-label` switches
  between "Expand panel" / "Restore panel"; `FOCUS_RING` applied.
- Body height: `380px` default, `80vh` when expanded (via inline style or
  Tailwind arbitrary values on the body container; body keeps
  `min-h-0 overflow-hidden` so inner graphs size correctly).
- On expand, calls `scrollIntoView({ block: "nearest", behavior: "smooth" })`
  on the panel root so the enlarged panel stays in view.
- Expansion state is local `useState`, independent per panel, not persisted.
  Multiple panels may be expanded at once.

### `SynthesisStudioView.tsx` (modified)

- Replace the three-column grid with a vertical `flex flex-col gap-4`
  stack of three `ExpandableStudioPanel`s.
- Panel titles: "Category overview", "Drill-down", "Details".
- All inner content, state, and data flow (queries, hops selector,
  selection handlers, empty/error states) are unchanged — only the
  containers change.

## Out of scope

- No persistence of expand state.
- No accordion behavior.
- No changes to graph components, API, or other Studio pages.

## Testing

- Frontend build/typecheck passes.
- Manual verification: panels stack vertically, expand/restore works per
  panel, graphs re-render correctly at both heights, keyboard focus ring
  visible on the toggle.

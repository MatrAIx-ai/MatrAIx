# Full DAG Visualization

This directory contains the generated static HTML visualization for the Persona
Full DAG.

## Generate

Run from the repository root:

```bash
uv run python persona/synthesis/scripts/render_graph_visualization.py
```

By default this reads:

```text
persona/synthesis/graph/full_dag.json
```

and writes:

```text
persona/synthesis/visualization/full_dag_overview.html
```

To render a different graph or output path:

```bash
uv run python persona/synthesis/scripts/render_graph_visualization.py \
  --graph persona/synthesis/graph/full_dag.json \
  --out /tmp/full_dag_overview.html
```

## Open

For normal local review:

```bash
open persona/synthesis/visualization/full_dag_overview.html
```

If a browser or test harness blocks direct `file://` access, serve the repo over
local HTTP:

```bash
python -m http.server 8765
open http://localhost:8765/persona/synthesis/visualization/full_dag_overview.html
```

Stop the temporary server with `Ctrl-C`.

## What It Shows

The page embeds the full graph payload:

- 1,357 nodes
- 6,937 directed proposal edges
- 40 category lanes

Layout semantics:

- X position follows `proposal_view.topological_order`.
- Y position groups nodes by category.
- Node size scales with directed degree.
- Hidden/source-proxy nodes render with lower opacity.

Controls:

- Search by node id, label, or category.
- Filter by category.
- Filter by minimum degree.
- Toggle hidden nodes.
- Toggle edges.
- Drag to pan.
- Scroll to zoom.
- Hover or click a node to inspect id, label, category, degree, value count,
  and emit status.

## Update Policy

Do not hand-edit `full_dag_overview.html`. Regenerate it with
`render_graph_visualization.py` after changing `full_dag.json` or the
visualization code, then commit both the script change and the generated HTML.

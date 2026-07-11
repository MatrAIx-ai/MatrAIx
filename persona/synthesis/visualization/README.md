# Full DAG Visualization

This directory contains generated static visualizations for the Persona Full DAG:

- `full_dag_overview.html` — interactive node-link view of the full graph.
- `persona_schema_taxonomy.png` / `.pdf` — clean taxonomy tree of the schema
  (9 groups / 15 aspects / 43 categories / 1290 attributes) for the paper
  appendix.

## Generate

Run from the repository root:

```bash
uv run python persona/synthesis/scripts/render_graph_visualization.py
```

By default this reads:

```text
persona/synthesis/graph/full_dag.json
persona/schema/dimensions.json
```

and writes:

```text
persona/synthesis/visualization/full_dag_overview.html
```

To render a different graph or output path:

```bash
uv run python persona/synthesis/scripts/render_graph_visualization.py \
  --graph persona/synthesis/graph/full_dag.json \
  --schema persona/schema/dimensions.json \
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

## Persona Schema Taxonomy Tree

`persona_schema_taxonomy.png` / `.pdf` is a clean three-level horizontal bracket
tree of the schema for the paper appendix, aligned to the official taxonomy
table (9 groups / 1290 attributes):

- Left column: the 9 top-level groups, with attribute totals.
- Middle column: the aspects (schema-prefix mid level, e.g. `Demographic`,
  `Developer`).
- Right column: the 43 fine-grained categories, with attribute counts.

Regenerate it from the repository root:

```bash
uv run --extra viz python persona/synthesis/scripts/render_persona_schema_taxonomy.py
```

Aggregation notes:

- Latent/helper graph nodes (18 nodes with no `category`, e.g. `latent_*` /
  `phase*_*`) are excluded, since they are internal modeling variables rather
  than persona attributes; the figure covers exactly the 1,290 real attributes.
- The individual `Developer: *` categories are shown separately (unlike the
  compact table, which merges them into one `Developer/Coding` sub-category), so
  the appendix figure is a more detailed view of the schema.

## What It Shows

The page embeds the full graph payload:

- 1,290 schema/emitted persona attributes
- 0 hidden persona attributes
- 18 latent/helper graph nodes
- 1,308 total graph nodes
- 6,999 directed proposal edges
- 44 category lanes

Layout semantics:

- X position follows `proposal_view.topological_order`.
- Y position groups nodes by category.
- Node size scales with directed degree.
- Latent/helper nodes render with lower opacity.
- Each node inspector labels the node as `attribute` or `latent/helper`.

Controls:

- Search by node id, label, category, or node type.
- Filter by category.
- Filter by minimum degree.
- Toggle hidden/helper nodes.
- Toggle edges.
- Drag to pan.
- Scroll to zoom.
- Hover or click a node to inspect id, label, category, node type, degree,
  value count, schema-attribute status, and emitted-attribute status.

## Update Policy

Do not hand-edit `full_dag_overview.html`. Regenerate it with
`render_graph_visualization.py` after changing `full_dag.json` or the
visualization code, then commit both the script change and the generated HTML.

Likewise, do not hand-edit `persona_schema_taxonomy.png` / `.pdf`. Regenerate
them with `render_persona_schema_taxonomy.py`, then commit both the script change
and the generated figures.

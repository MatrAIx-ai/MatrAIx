# Persona assets

| Path | Purpose |
|------|---------|
| `dimensions.json` | Dimension catalog (`index` = `bench_dim_index` for persona bench tasks) |
| `attribute_pool/` | Candidate attribute pool + normalization outputs |
| `validators/` | Schema checks for `dimensions.json` |
| `datasets/bench-dev-2000/` | Primary dev persona pool (2000 synthetic profiles) |
| `tasks/` | Validation Harbor tasks |
| `scripts/generate_dev_personas.py` | Generate dev YAML from `dimensions.json` |
| `scripts/generate_persona_job.py` | Sample personas → Harbor grounding job YAML |
| `tools/annotation_package/` | Build worker annotation packages from wiki profiles or Amazon reviews |
| `reporting/` | Grounding report after multi-persona jobs |

Persona cards for agents are rendered from `dimensions.json` as wiki-style biography paragraphs (`dimension_profile_narrative`).

## Generate dev personas

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --count 2000 \
  --seed 42 \
  --task persona/tasks/example-survey_product-feedback \
  --stratum-min 2
```

## Dev grounding

Default dataset: `bench-dev-2000`. Jobs read `grounding.toml` on each bench task (filter confounders → stratify on probe). Use `--controlled-probe` for anchor-based cohorts.

```bash
uv run python persona/scripts/generate_persona_job.py \
  --task persona/tasks/example-survey_product-feedback \
  --sample-size-per-value-group 1
```

See [`scripts/README.md`](scripts/README.md) for flags.

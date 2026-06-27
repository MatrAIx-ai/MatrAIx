# bench-dev-sample source

This fixture set is copied from the generated MatrAIx `bench-dev-2000` pool.
It keeps only a small number of personas needed for docs, smoke tests, and
curated recipe parity.

| Field | Value |
|-------|-------|
| Source count | 2002 (2000 base + stratum top-up) |
| Checked-in fixture count | 14 |
| Schema | v2 (`persona_id`, `version`, `dimensions`) |
| Smoke | `persona_0042.yaml` |
| Dimensions | **82** — catalog index 1–47 (core) + all `cog_*` communication dims |

Personas are sampled so **linked dimensions stay consistent** (no counterfactual combos like `18–24` + `Retirement`, or `Student` + `VP`). Independent dims (`economic_motivation`, cognitive style, etc.) are random.

Optional **stratum top-up** ensures each catalog confounder × probe cell has enough real personas for grounding jobs (still passes consistency checks; only non-linked dims are fixed).

Regenerate:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --count 2000 \
  --seed 42 \
  --task persona/tasks/example-survey_product-feedback \
  --stratum-min 2
```

Base pool only (no top-up):

```bash
uv run python persona/scripts/generate_dev_personas.py --count 2000 --seed 42
```

Optional full-pool output: `--out persona/datasets/bench-dev-2000 --smoke-id 0042`

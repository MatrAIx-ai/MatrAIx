# Persona scripts

| Script | Purpose |
|--------|---------|
| [`generate_dev_personas.py`](generate_dev_personas.py) | Generate consistent dev YAML from `persona/schema/dimensions.json` |
| [`generate_persona_job.py`](generate_persona_job.py) | Sample personas -> Harbor grounding job YAML |
| [`synthesize_human_personas.py`](synthesize_human_personas.py) | Generate schema-grounded synthetic persona vectors and reject readable constraint violations |

**Dev pool:** `uv run python persona/scripts/generate_dev_personas.py` -> `persona/datasets/_generated/bench-dev-2000/` (ignored by git; see `--task` / `--stratum-min` for grounding cell top-up)

**Synthetic vectors:** `uv run python persona/scripts/synthesize_human_personas.py --count 100 --seed 42` -> `persona/datasets/_generated/synthetic-human-100/` (ignored by git; uses `persona/schema/dimensions.json` plus `persona/schema/dimension_constraints_readable.txt`, and does not generate biography text)

**Grounding jobs** read confounders from the task catalog when present (filter pool -> stratify on probe only). Default for catalog tasks with confounders. Use `--controlled-probe` for anchor-based cohorts; `--no-controlled-probe` disables anchor mode explicitly.

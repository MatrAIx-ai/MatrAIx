# Scale-up tooling

Supporting code and data for producing **many** purchase-intent survey
scenarios from real Amazon products — the "products × perturbations → surveys"
workflow. This is not part of the single harness scenario in the parent task
folder; it's how that kind of scenario is generated at scale.

All paths below are relative to this `data-generation/` directory.

## Contents

- `fixtures/products.json` — 15 hand-curated real products (small test fixture).
- `fixtures/products_bulk.json` — 494 real Amazon products across 22 best-seller
  categories, each with a working link, price, rating, and 5+ seller-authored
  attributes.
- `fixtures/surveys_v1.jsonl` — 494 generated surveys, one per product, each
  changing exactly one attribute (256 price, 238 physical-attribute), with a
  fully rendered `prompt` and `response_schema`.
- `fixtures/survey_swaps.json` — authored replacement values the generator
  merges in.
- `templates/price_change.md`, `templates/attribute_change.md` — the
  parameterized (`{{placeholder}}`) survey templates.
- `pipeline/` — the survey library: product model, rendering, response
  parsing/validation, retention-rate metrics.
- `scripts/` — scraping + generation tools (below).
- `dev_tests/` — pytest unit tests for the tooling (mock model, no network).
- `verify_pipeline.py` — end-to-end smoke test with a deterministic mock model.

## Setup

From the repo root: `uv sync` (or `pip install -e .`). No local model is
required — tests use a mock, and survey collection targets any
OpenAI-compatible API.

## Running

```bash
python3 -m pytest dev_tests/ -q     # unit tests
python3 verify_pipeline.py          # smoke test
```

## Generating surveys

```bash
# 1. plan which attribute to perturb per product (seeded, reproducible)
python3 scripts/generate_surveys.py --products fixtures/products_bulk.json \
    --emit-worklist output/survey_worklist.json

# 2. author a replacement value per attribute-perturbed survey in
#    fixtures/survey_swaps.json ({survey_id: new_value}; "__price__" falls
#    back to a price change where a chosen attribute has no sensible swap)

# 3. render + validate into the surveys file
python3 scripts/generate_surveys.py --products fixtures/products_bulk.json \
    --assemble --swaps fixtures/survey_swaps.json --out fixtures/surveys_v1.jsonl
```

Collect responses with any model:

```bash
# validate all surveys with no model (safe preflight)
python3 scripts/run_surveys.py --surveys fixtures/surveys_v1.jsonl \
    --out output/preflight.jsonl --dry-run

# real collection against an OpenAI-compatible endpoint
export SURVEY_API_KEY=...
python3 scripts/run_surveys.py --surveys fixtures/surveys_v1.jsonl \
    --out output/survey_responses.jsonl \
    --endpoint https://api.example.com/v1/chat/completions --model <id>
```

## Growing the product dataset

```bash
python3 scripts/scrape_amazon.py <amazon_url> ...     # scrape one/few products
python3 scripts/add_product.py new_products.json      # validate + append
```

Bulk harvest (1000+ products), unattended and resumable:

```bash
nohup bash scripts/run_full_harvest.sh > output/harvest_run.log 2>&1 &
tail -f output/harvest_run.log
```

Runs discovery → harvest → assemble. Requests are paced ~25–37s apart; the
runner detects Amazon's HTTP-200 CAPTCHA block pages, sleeps through block
episodes, and resumes from `output/` checkpoints on rerun. Only records with a
title, plausible price, and ≥5 attributes are accepted (rejects land in
`output/harvest.rejects.jsonl` with reasons). The assembled dataset is written
to `fixtures/products_bulk.json`.

Always confirm a scraped `product_name` matches the product you expected —
ASINs occasionally get reassigned — and spot-check `original_price` on pages
with size/color variant grids or bundled add-ons. The bulk run stopped at 494
of a 1000 target when the scraping IP hit an extended Amazon cooldown; rerunning
from a fresh egress IP grows it without redoing work.

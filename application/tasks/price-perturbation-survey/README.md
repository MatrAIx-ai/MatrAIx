# Price-perturbation purchase-intent survey

Simulates how a shopper reacts when one thing about a product they were
considering changes — either its price or a physical attribute (color,
material, size, ...). The subject is shown the product and the change and
answers a 6-field structured purchase-intent survey; responses are parsed
and validated, then aggregated into a retention rate. Works with or
without a persona (persona text becomes the system prompt).

## Setup

From the repo root:

```bash
uv sync   # or: pip install -e .
```

No local model is required: the pipeline runs against a mock model for
tests, and survey collection targets any OpenAI-compatible API you point
it at (see "Generating and running surveys").

## The task (harness single scenario)

Like the other application survey tasks, this runs as one scenario:
Harbor builds the environment, injects the persona, the agent answers,
and the verifier scores the output file.

- `instruction.md` — the task prompt. Tells the agent to read
  `/app/input/`, answer as its assigned persona, and save the six-field
  JSON to `/app/output/purchase_decision.json`.
- `environment/task-environments/application/price-perturbation-survey/`
  (in the `environment/` module) — the runtime: `Dockerfile` +
  `install-claude-code.sh`, and the input materials `product.md` (a real
  Amazon product with a +25% price change) and `survey.md` (the six
  questions and answer codes) that become `/app/input/`.
- `tests/test_state.py` + `tests/test.sh` — the verifier. Validates
  `/app/output/purchase_decision.json` against the six-field schema
  (allowed-value membership, non-empty reasoning, no extra fields) and
  writes the reward. Standalone; no repo imports.
- `solution/solve.sh` — reference solution: reads the persona's economic
  posture and emits a schema-valid, internally consistent answer set.
  Proves the task is solvable and exercises the verifier.
- `task.toml` — task metadata and `[environment].definition`.

## Scale-up tooling (dataset + generator)

Supporting code for producing many such scenarios at scale (Shirley's
"products × perturbations → surveys" workflow). Not part of the single
harness scenario above.

- `templates/price_change.md`, `templates/attribute_change.md` — the
  parameterized (`{{placeholder}}`) survey templates the bulk generator
  renders per product. (The task-root `instruction.md` is separate.)
- `fixtures/surveys_v1.jsonl` — **494 ready-to-run perturbed surveys**,
  one per product, each changing exactly one attribute (price or a
  physical attribute), with a fully rendered `prompt` + `response_schema`.
- `fixtures/survey_swaps.json` — the authored replacement values that
  `generate_surveys.py` merges in to build the surveys.
- `scripts/generate_surveys.py` — builds `surveys_v1.jsonl`: a
  seeded-random choice of which attribute to perturb per product
  (`--emit-worklist`), then rendering + validation (`--assemble`).
- `scripts/run_surveys.py` — collects responses to the surveys. Model-
  agnostic: `--dry-run` validates every survey with no model (safe
  default), or `--endpoint` targets any OpenAI-compatible
  `/v1/chat/completions` API (bring your own model + `$SURVEY_API_KEY`).
- `pipeline/` — the survey library: product model, prompt rendering,
  response parsing/validation, and retention-rate metrics.
- `dev_tests/` — pytest unit tests for the tooling (mocked model, no
  network). Kept separate from the verifier `tests/`.
- `verify_pipeline.py` — fast end-to-end smoke test with a deterministic
  mock model.

## Product data + scraper

- `fixtures/products.json` — 15 real, curated products with verified
  Amazon links (`amazon_url`/`asin`), attributes, and provenance notes.
- `scripts/scrape_amazon.py` — fetches real product data (title, price,
  rating, review count) from an Amazon product page via a plain HTTP GET
  with browser-like headers. Rating/review count parse reliably for most
  pages; price is unreliable on pages with size/color variant grids or
  bundled add-on offers — always spot-check price and confirm the
  scraped title matches the product you expected (ASINs occasionally
  get reassigned to a different listing over time).
- `scripts/add_product.py` — validate-and-append tool for adding
  scraped/researched products to the fixture (required fields, ASIN
  format, rating bounds, duplicate detection).
- `scripts/discover_products.py` — harvests candidate product URLs from
  Amazon best-seller pages across ~35 physical-goods categories
  (checkpointed; rerunning resumes).
- `scripts/harvest.py` — unattended bulk scraper: candidates → validated
  JSONL records (title, price, rating, reviews, 5+ attributes, feature
  bullets). Checkpoints every record, detects Amazon's CAPTCHA block
  pages, backs off in escalating quiet periods (blocks clear after
  ~2-5 min of silence), and resumes exactly where it left off on rerun.
- `scripts/assemble_dataset.py` — dedupes/validates harvest output into
  the final dataset (`fixtures/products_bulk.json`) with a summary report
  and outlier flags for manual spot-checks.
- `scripts/run_full_harvest.sh` — one-shot orchestrator for the above
  three stages; safe to rerun after interruption.
- `fixtures/surveys_v1.jsonl` — **494 ready-to-run perturbed surveys**,
  one per product, each with exactly one randomly changed attribute
  (price or a physical attribute) and a fully rendered `prompt` plus the
  `response_schema`. This is the testable deliverable.
- `fixtures/survey_swaps.json` — the authored replacement values (one
  per attribute-perturbed survey) that `generate_surveys.py` merges in.
- `scripts/generate_surveys.py` — builds `surveys_v1.jsonl`: a
  seeded-random choice of which attribute to perturb per product
  (`--emit-worklist`), then rendering + validation (`--assemble`).
- `scripts/run_surveys.py` — collects responses to the surveys. Model-
  agnostic: `--dry-run` validates every survey with no model (safe
  default), or `--endpoint` targets any OpenAI-compatible
  `/v1/chat/completions` API (bring your own model + `$SURVEY_API_KEY`).
- `fixtures/products_bulk.json` — the large scraped dataset (494
  products across 22 best-seller categories, ≥5 seller-authored
  attributes each, working Amazon links). Collected 2026-07-09; the
  run was stopped at 494 when the scraping IP entered an extended
  Amazon cooldown — rerun `scripts/run_full_harvest.sh` (ideally from
  a different network) to grow it toward the 1000 target; all stages
  resume from checkpoints.

## Running

```bash
# Verifier (validates a /app/output/purchase_decision.json)
python3 tests/test_state.py

# Tooling unit tests (mock model, no network)
python3 -m pytest dev_tests/ -q

# End-to-end smoke test of the pipeline (mock model, no network)
python3 verify_pipeline.py
```

To exercise the full task the way the harness does — build the
environment, produce an output, score it — see the reference solution
`solution/solve.sh` and verifier `tests/test.sh`.

## Adding products

```bash
# 1. Find the product's real amazon.com/.../dp/<ASIN> URL (web search).
# 2. Scrape title/price/rating/review_count:
python3 scripts/scrape_amazon.py <amazon_url> [<amazon_url> ...]

# 3. Build a JSON array of product objects (see PRODUCT_SCHEMA in
#    scripts/add_product.py) and validate + append:
python3 scripts/add_product.py new_products.json
```

Always confirm the scraped `product_name` matches the product you
searched for, and double-check `original_price` manually on pages with
size/color variants or bundled add-ons — see the caveats in
`scripts/scrape_amazon.py` and `pipeline/product_source.py`.
`scripts/add_product.py` validates required fields, ASIN format,
URL/ASIN consistency, rating bounds, and duplicate ASINs before
appending to `fixtures/products.json`.

## Bulk harvesting (1000+ products)

```bash
nohup bash scripts/run_full_harvest.sh > output/harvest_run.log 2>&1 &
tail -f output/harvest_run.log
```

Runs discovery → harvest → assemble unattended (several hours: requests
are paced ~25-37s apart to stay under Amazon's anti-bot threshold, and
the runner sleeps through block episodes). All stages checkpoint to
`output/`, so rerunning the same command resumes rather than restarts.
Only records with a title, plausible price, and ≥5 attributes are
accepted; rejects land in `output/harvest.rejects.jsonl` with reasons.
The assembled dataset is written to `fixtures/products_bulk.json`.

Anti-bot notes (empirical, 2026-07-08): Amazon soft-blocks with an
HTTP-200 CAPTCHA page; blocks clear after ~2-5 minutes of sending
nothing. Right after recovery it may serve a degraded page template
with an empty buybox (no price) — the harvester retries those once at
the end of the run instead of rejecting them.

## Generating and running surveys

Turn the product dataset into one perturbed survey per product (each
changes exactly one attribute — price or a physical attribute):

```bash
# 1. plan which attribute to perturb per product (seeded, reproducible)
python3 scripts/generate_surveys.py --products fixtures/products_bulk.json \
    --emit-worklist output/survey_worklist.json

# 2. author a replacement value for each attribute-perturbed survey
#    (fixtures/survey_swaps.json — {survey_id: new_value}; use the
#    sentinel "__price__" to fall back to a price change for a product
#    whose chosen attribute has no sensible alternative)

# 3. render + validate into the final surveys file
python3 scripts/generate_surveys.py --products fixtures/products_bulk.json \
    --assemble --swaps fixtures/survey_swaps.json \
    --out fixtures/surveys_v1.jsonl
```

Each line of `surveys_v1.jsonl` is a self-contained survey: `survey_id`,
product identity, a `perturbation` block (`type`, `attribute`,
`original_value`, `new_value`), the fully rendered `prompt` (send as the
user message), and the `response_schema`. A persona "takes" a survey by
supplying its system prompt alongside the user prompt; with no persona,
the prompt is sent alone.

Collect responses with any model:

```bash
# validate all surveys with no model (safe, instant preflight)
python3 scripts/run_surveys.py --surveys fixtures/surveys_v1.jsonl \
    --out output/preflight.jsonl --dry-run

# real collection against an OpenAI-compatible endpoint
export SURVEY_API_KEY=...
python3 scripts/run_surveys.py --surveys fixtures/surveys_v1.jsonl \
    --out output/survey_responses.jsonl \
    --endpoint https://api.example.com/v1/chat/completions --model <id>
```

Responses are parsed/validated by `pipeline/collector.py` (the same
6-field contract as the interactive pipeline) and checkpointed to the
output JSONL, so a rerun resumes where it left off.

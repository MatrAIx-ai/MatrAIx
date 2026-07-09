# Price-perturbation purchase-intent survey

Simulates how different personas react to a product price increase (and,
in the future, non-price attribute changes). Each persona is shown a
product and a new, higher price, and answers a 6-field structured
purchase-intent survey (`instruction.md`). Responses are parsed and
validated, then aggregated into a retention rate.

## Setup

From the repo root:

```bash
uv sync   # or: pip install -e .
```

For a real (non-mock) sample run you also need [Ollama](https://ollama.com)
installed locally with the model pulled:

```bash
ollama pull llama3.1
```

## Layout

- `instruction.md` — the survey prompt template for a price increase.
- `instruction_attribute.md` — survey prompt template for a non-price
  attribute change (color/shape/material). Currently unreachable in
  practice — see note in `pipeline/perturbation.py` about why the swap
  tables don't match our real product attribute strings yet. Kept for
  future work, not deleted.
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
  the final dataset (`fixtures/products_1k.json`) with a summary report
  and outlier flags for manual spot-checks.
- `scripts/run_full_harvest.sh` — one-shot orchestrator for the above
  three stages; safe to rerun after interruption.
- `fixtures/products_1k.json` — the large scraped dataset (1000+
  products, ≥5 seller-authored attributes each, working Amazon links).
- `pipeline/` — the survey pipeline: product loading, prompt rendering,
  response parsing/validation, and retention-rate metrics.
- `tests/` — pytest unit tests (mocked model, no network/Ollama needed).
- `verify_pipeline.py` — fast end-to-end smoke test with a deterministic
  mock model (no Ollama needed). Run this first to confirm your setup
  works.
- `run_real.py` — real sample-collection run against local Ollama
  (llama3.1) over `bench-dev-sample` personas. Tuned for low, steady
  resource use (thread-capped, inter-call delay) so it can run
  unattended.
- `start_run.sh` — launches `run_real.py` fully detached (`nohup` +
  `disown`) so it keeps running after you close the terminal.

## Running

```bash
# 1. Unit tests
python3 -m pytest tests/ -q

# 2. Smoke test (no Ollama required)
python3 verify_pipeline.py

# 3. Real sample run (requires Ollama + llama3.1 pulled)
./start_run.sh
tail -f output/run_real.log       # watch progress live
```

`start_run.sh` clears previous run output, activates the repo's `.venv`
if present, checks that `ollama` and `llama3.1` are available, then
launches the run detached in the background. Results land in
`output/real_run_results.json`; the `output/` directory is gitignored.

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
The assembled dataset is written to `fixtures/products_1k.json`.

Anti-bot notes (empirical, 2026-07-08): Amazon soft-blocks with an
HTTP-200 CAPTCHA page; blocks clear after ~2-5 minutes of sending
nothing. Right after recovery it may serve a degraded page template
with an empty buybox (no price) — the harvester retries those once at
the end of the run instead of rejecting them.

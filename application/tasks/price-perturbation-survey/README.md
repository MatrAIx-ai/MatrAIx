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
- `fixtures/products.json` — 5 real, curated products with verified
  Amazon links (`amazon_url`/`asin`), attributes, and provenance notes.
- `scripts/add_product.py` — validate-and-append tool for adding more
  products to the fixture (Amazon scraping isn't viable — see the
  docstring in `pipeline/product_source.py`).
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
python3 scripts/add_product.py new_products.json
```

`new_products.json` must be a JSON array of product objects. The script
validates required fields, ASIN format, URL/ASIN consistency, rating
bounds, and duplicate ASINs before appending to `fixtures/products.json`.

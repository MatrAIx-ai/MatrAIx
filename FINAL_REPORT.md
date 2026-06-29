# Final Report: Price-Perturbation Purchase-Intent Survey Pipeline

## Summary

This work extends the MatrAIx persona simulation framework with a reusable pipeline
for evaluating how simulated personas respond to retail price increases. Given a set
of one-time-purchase products, the pipeline raises each price by 25%, presents the
scenario to each persona, collects structured purchase decisions, and computes an
aggregate **retention rate** (the fraction of personas who would still buy).

Everything lives on the `feature/price-perturbation-survey` branch (7 commits,
`db47bd9..a7198b9`).

## What was built

### 1. Parameterized instruction file

**`application/tasks/price-perturbation-survey/instruction.md`**

A scenario-specific instruction template parameterized over four product fields:
`{{product_name}}`, `{{product_description}}`, `{{original_price}}`, `{{new_price}}`.
Follows the repo's instruction-file convention:

- Concept framing (price increase scenario)
- Clear task description (decide whether to buy)
- Strict JSON output schema: `{ "would_buy": "yes"|"no", "reasoning": "<string>" }`
- Explicit save path: `/app/output/purchase_decision.json`
- Enumerated allowed values and rules (no extra fields, no placeholder values, no
  empty reasoning)

An accompanying `task.toml` provides standard metadata (version, domain, tags,
timeouts).

### 2. Pipeline code

All pipeline modules live under
`application/tasks/price-perturbation-survey/pipeline/`:

| Module | Purpose |
|--------|---------|
| `models.py` | Frozen `Product` dataclass (product_name, description, original_price, image_url) |
| `product_source.py` | `ProductSource` ABC with `get_products()`. Two implementations: `FixtureProductSource` (reads checked-in JSON, fully offline) and `AmazonProductSource` (stub, raises `NotImplementedError`) |
| `perturbation.py` | `perturb_price(product, factor=1.25)` — returns new price rounded to 2 decimal places |
| `renderer.py` | `render_instruction()` fills `{{placeholder}}`s in `instruction.md`; `render_prompt()` combines product instruction with persona system prompt into a `RenderedPrompt` |
| `collector.py` | `collect_decisions(prompts, model_fn)` calls a `ModelCallable`, parses JSON responses (bare or markdown-fenced), returns `Decision` objects. Gracefully skips unparseable responses |
| `metrics.py` | `compute_retention_rate(decisions)` — plain fraction of `would_buy == "yes"`. Rule-based, no judge model |
| `run.py` | `run_pipeline()` end-to-end orchestrator: source products, render (product x persona) prompts, collect decisions, compute retention rate. Returns a `PipelineResult` dataclass |

### 3. Fixture product data

**`application/tasks/price-perturbation-survey/fixtures/products.json`**

Five realistic one-time-purchase retail products spanning different categories:

| Product | Original Price | +25% Price |
|---------|---------------|------------|
| Cuisinart 14-Cup Food Processor | $199.99 | $249.99 |
| Brooks Ghost 15 Running Shoes | $139.95 | $174.94 |
| Osprey Daylite Plus Daypack | $74.95 | $93.69 |
| Settlers of Catan Board Game | $44.99 | $56.24 |
| Logitech MX Master 3S Wireless Mouse | $99.99 | $124.99 |

### 4. Test suite

**`application/tasks/price-perturbation-survey/tests/test_pipeline.py`**

18 pytest tests in 5 classes covering every pipeline stage:

- `TestProduct` (3): fixture loading, perturbation arithmetic, rounding
- `TestRenderer` (2): placeholder substitution, persona metadata
- `TestCollector` (4): bare JSON parsing, fenced JSON, invalid `would_buy`, empty reasoning
- `TestMetrics` (4): all-yes, all-no, mixed, empty edge case
- `TestPipelineEndToEnd` (5): no-persona run, persona run, all-no, field validation, count consistency

All 18 pass (0.03s, no external dependencies).

### 5. Verification run

**`application/tasks/price-perturbation-survey/verify_pipeline.py`** and
**`application/tasks/price-perturbation-survey/output/verification_results.json`**

A verification script ran the full pipeline with 3 real personas from the repo
(`persona_0001`, `persona_0042`, `persona_0052`) across all 5 fixture products
(15 prompts total). No API key was available, so a deterministic mock model was used
that varies `yes`/`no` by hashing prompt content.

Results:
- **Aggregate retention rate: 66.67%** (10/15 would buy)
- Per-persona: 0001 = 80%, 0042 = 60%, 0052 = 60%
- Per-product: Food Processor = 100%, Running Shoes = 67%, Daypack = 33%,
  Board Game = 67%, Mouse = 67%
- 0 parse failures out of 15 prompts

## How to run

### Run the test suite

```bash
python -m pytest application/tasks/price-perturbation-survey/tests/test_pipeline.py -v
```

### Run the verification script

```bash
python application/tasks/price-perturbation-survey/verify_pipeline.py
```

This produces `output/verification_results.json` under the task directory.

### Use the pipeline programmatically

```python
from application.tasks.price_perturbation_survey.pipeline.product_source import FixtureProductSource
from application.tasks.price_perturbation_survey.pipeline.run import run_pipeline

source = FixtureProductSource()

def my_model(system_prompt, user_prompt):
    # Call your LLM here; return a JSON string
    ...

result = run_pipeline(
    source=source,
    model_fn=my_model,
    persona_prompts={"p1": "You are a budget-conscious shopper..."},
)
print(f"Retention rate: {result.retention_rate:.1%}")
```

## Key decisions and tradeoffs

1. **Pluggable product source.** The `ProductSource` ABC makes it straightforward to
   swap in a live Amazon scraper later without changing any pipeline logic. The fixture
   source ensures the pipeline runs fully offline and deterministically for testing.

2. **`str.replace()` over Jinja2 for product placeholders.** The instruction template
   has exactly 4 fixed placeholders. Using `str.replace()` avoids adding a Jinja2
   dependency to the pipeline itself. The repo's existing Jinja2 templating is for
   persona prompts, which are a separate concern passed into the pipeline as
   pre-rendered strings.

3. **`ModelCallable` indirection.** The collector accepts any
   `Callable[[str | None, str], str]` rather than importing a specific LLM client.
   This makes the entire pipeline testable with mock functions and adaptable to any
   model backend.

4. **Rule-based retention rate.** Per the team's requirement, the metric is a plain
   aggregation (`count(yes) / count(total)`) with no judge model.

5. **Mock verification run.** No API key was available in the execution environment.
   The verification script uses a deterministic hash-based mock that produces a
   realistic decision mix rather than trivially returning all-yes or all-no. A live
   LLM run would be the natural follow-up.

## Follow-up opportunities

- **Live LLM verification:** Re-run `verify_pipeline.py` with an `ANTHROPIC_API_KEY`
  set to get genuine persona responses.
- **Live Amazon scraper:** Implement `AmazonProductSource` behind the existing ABC
  interface (currently a stub raising `NotImplementedError`).
- **Configurable perturbation factors:** The pipeline already accepts a `factor`
  parameter; could sweep 10%, 25%, 50% increases to build price-sensitivity curves.
- **Integration with Harbor:** Wire the instruction template into a Harbor job recipe
  (similar to `appSim-example-survey-product-feedback-random-n4.yaml`) for full
  container-based execution.

## Branch and commits

**Branch:** `feature/price-perturbation-survey`

| Commit | Description |
|--------|-------------|
| `db47bd9` | chore: create feature branch |
| `912d320` | feat: add parameterized instruction.md and task.toml |
| `9623adc` | feat: add fixture product data |
| `8f0b20c` | feat: add pipeline foundation (Product model, ProductSource, perturbation) |
| `31a049c` | feat: add prompt renderer, decision collector, retention-rate metric |
| `3825efa` | feat: add pipeline orchestrator and end-to-end test suite |
| `a7198b9` | feat: add verification run with 3 real personas on fixture products |

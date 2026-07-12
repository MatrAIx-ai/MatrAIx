# Purchase-intent survey

PersonaBench application (Type-1, survey) task, commerce-retail domain. The
persona is shown a real product they were considering and told that **one**
thing about it changed — its price or an attribute (the shipped scenario is a
price increase) — then answers a short structured purchase-intent survey.
Measures how a single product change shifts purchase intent.

## The scenario

Harbor injects the persona; the environment supplies the instrument in
`/app/input/`:

- `product.md` — a real Amazon product (STANLEY Quencher) with a +25% price
  change.
- `survey.md` — six questions and their exact answer codes.

The agent reads both and writes its answers to
`/app/output/purchase_decision.json`.

## Expected artifact

`/app/output/purchase_decision.json` — a single object with exactly six fields:

```json
{
  "purchase_intent": "probably_would_not",
  "price_fairness": "somewhat_high",
  "alternative_seeking": "yes",
  "purchase_timing": "wait_for_sale",
  "necessity_level": "nice_to_have",
  "reasoning": "..."
}
```

The verifier (`tests/test_state.py`) checks the schema: every field present,
each value in its allowed set, `reasoning` non-empty, no extra fields. See
`instruction.md` for the full field spec.

## Layout

- `instruction.md` — the task prompt.
- `task.toml` — metadata + `[environment].definition`.
- `tests/` — verifier (`test_state.py` + `test.sh`).
- `solution/solve.sh` — reference solution (posture-aware, schema-valid).
- `environment/task-environments/application/purchase-intent-survey/` (in the
  `environment/` module) — Dockerfile + the `/app/input` materials.
- `data-generation/` — **scale-up tooling** (not part of the single scenario):
  the Amazon scraper + harvest pipeline, the 494-product dataset, and the survey
  generator that turns products into many perturbed surveys. See
  [`data-generation/README.md`](data-generation/README.md).

## Local smoke

```bash
# reference solution -> verifier (with a persona injected at /app/input/persona.yaml)
bash solution/solve.sh && python3 tests/test_state.py

# or launch through Harbor
uv run harbor run \
  -a persona-claude-code \
  -m "${PERSONABENCH_HARBOR_PERSONA_MODEL:-anthropic/claude-haiku-4-5}" \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/purchase-intent-survey
```

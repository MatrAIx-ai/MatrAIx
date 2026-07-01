# Job Recipes

This directory contains curated Harbor job recipes that run against files kept
in PersonaBench `main`.

Rules for adding recipes:

- Use paths that exist in this repository.
- Use personas from checked-in sample datasets, or document an external dataset
  dependency in the recipe README.
- Do not commit generated `jobs/` outputs.
- Do not add raw snapshots from the MatrAIx source tree.
- Keep generated or bulk recipes separate from hand-curated examples.

Current curated set:

- `example-job-recipe/`: local application task examples backed by
  `application/tasks/` and `persona/datasets/bench-dev-sample/`, plus
  `harbor-smoke-local.yaml` for a no-API-key runtime smoke check.
  Computer-use examples include `appSim-example-computer-use-{macos,ios}-local.yaml`
  and persona demo recipes `appSim-demo-cu-*`.
- `application-task-job-recipe/`: curated generated application recipe fixtures
  whose personas are copied into `persona/datasets/bench-dev-sample/`.
- `persona-task-grounding-job-recipe/`: curated generated persona grounding
  recipe fixtures backed by the same sample dataset.

Deferred from the MatrAIx source recipes:

- Generated random-sample recipes that reference `persona/datasets/bench-dev-2000/`
  beyond the checked-in sample fixture set, because that full dataset is
  intentionally external to git.

## Environment variables

- `ANTHROPIC_API_KEY` — Claude-family persona agents
- `LLM_API_KEY` — `persona-openhands-sdk` (Playwright web)
- `USE_COMPUTER_API_KEY` — `persona-computer-1` with `-e use-computer` (macOS / iOS)
- `USE_COMPUTER_RESERVATION_ID` — Mac Mini reservation for macOS / iOS
  (`reservation_id: ${USE_COMPUTER_RESERVATION_ID}` in job YAML; keep UUID in
  `.env`, not git)
- Docker Linux CUA needs `ANTHROPIC_API_KEY` + `uv sync --extra computer-1`
- `DAYTONA_API_KEY` — when `environment.type: daytona`

See [docs/running.md](../../docs/running.md) for install and smoke-test workflow.

## Run

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

Computer-use: `persona-computer-1` auto-routes — see `example-job-recipe/appSim-example-computer-use-*`
and `appSim-demo-cu-*`. System telemetry:
[computer-use-telemetry.md](../../docs/computer-use-telemetry.md).

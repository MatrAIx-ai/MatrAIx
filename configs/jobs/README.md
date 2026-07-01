# MatrAIx job configs

Harbor Job YAML under `configs/jobs/`. Run with `harbor run -c configs/jobs/<subdir>/<file>.yaml`.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`example-job-recipe/`](example-job-recipe/) | Hand-written **smoke / demo** jobs (checked in; `appSim-*`, `harbor-smoke-local`) |
| [`persona-task-grounding-job-recipe/`](persona-task-grounding-job-recipe/) | Persona bench jobs (`generate_persona_job.py`); **checked-in example** + other outputs gitignored |
| [`application-task-job-recipe/`](application-task-job-recipe/) | Application multi-persona jobs (`generate_application_job.py`); **checked-in example** + other outputs gitignored — [getting-started §7](../../docs/applications/getting-started.md#7-batch--sample-many-personas-job) |

## Example smoke jobs

| File | Purpose |
|------|---------|
| `example-job-recipe/appSim-example-debug-local.yaml` | Quick local run: survey + chat |
| `example-job-recipe/harbor-smoke-local.yaml` | Harbor hello-world smoke (no API key) |
| `example-job-recipe/appSim-example-survey-local.yaml` | Survey task smoke |
| `example-job-recipe/appSim-example-chat-local.yaml` | Chat task smoke |
| `example-job-recipe/appSim-example-web-playwright-local.yaml` | Web via `persona-openhands-sdk` |
| `example-job-recipe/appSim-example-web-browser-use-local.yaml` | Web via `persona-browser-use` |
| `example-job-recipe/appSim-example-web-cocoa-local.yaml` | Web via `persona-cocoa` |
| `example-job-recipe/appSim-example-web-linux-cua-local.yaml` | Docker Linux web CUA |
| `example-job-recipe/appSim-example-computer-use-linux-local.yaml` | Linux desktop notifications |
| `example-job-recipe/appSim-example-computer-use-macos-local.yaml` | macOS desktop |
| `example-job-recipe/appSim-example-computer-use-ios-local.yaml` | iOS Simulator (system telemetry + recording) |

## Checked-in batch examples

| File | Purpose |
|------|---------|
| `application-task-job-recipe/appSim-example-survey-product-feedback-random-n4.yaml` | Application survey batch (4 personas, random sample, seed 42) |
| `persona-task-grounding-job-recipe/personaBench-example-survey-product-feedback-economic-motivation-pg2.yaml` | Persona grounding batch (4 probe values × 2 personas) |

Other files under those directories are **gitignored** (local `generate_*_job.py` output).

### Checked-in `jobs/` outputs (viewer demos)

| `jobs/<job_name>/` | Recipe |
|--------------------|--------|
| `harbor-smoke-local/` | `example-job-recipe/harbor-smoke-local.yaml` |
| `appSim-example-survey-local/`, `appSim-example-chat-local/`, … | matching `example-job-recipe/appSim-*-local.yaml` |
| `appSim-example-survey-product-feedback-random-n4/` | `application-task-job-recipe/appSim-example-survey-product-feedback-random-n4.yaml` |
| `personaBench-example-survey-product-feedback-economic-motivation-pg2/` | `persona-task-grounding-job-recipe/personaBench-example-survey-product-feedback-economic-motivation-pg2.yaml` |

Browse: `uv run harbor view jobs/<job_name> --build`

## Persona grounding recipes

Regenerate locally via `persona/scripts/generate_persona_job.py` → `configs/jobs/persona-task-grounding-job-recipe/`. See [`persona/README.md`](../../persona/README.md).

## Environment variables

- `ANTHROPIC_API_KEY` — Claude-family persona agents
- `LLM_API_KEY` — `persona-openhands-sdk` (Playwright web)
- `USE_COMPUTER_API_KEY` — `persona-computer-1` with `-e use-computer` (macOS / iOS)
- `USE_COMPUTER_RESERVATION_ID` — Mac Mini reservation for macOS / iOS (`reservation_id: ${USE_COMPUTER_RESERVATION_ID}` in job YAML; keep UUID in `.env`, not git)
- Docker Linux CUA needs `ANTHROPIC_API_KEY` + `uv sync --extra computer-1`
- `DAYTONA_API_KEY` — when `environment.type: daytona`

See [`.env.example`](../../.env.example) and [choosing-an-agent.md](../../docs/environments/choosing-an-agent.md).

## Run

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-debug-local.yaml
```

Computer-use: `persona-computer-1` auto-routes — see `example-job-recipe/appSim-example-computer-use-*` and `example-job-recipe/appSim-example-web-linux-cua-local.yaml`. System telemetry: [computer-use-telemetry.md](../../docs/environments/computer-use-telemetry.md).

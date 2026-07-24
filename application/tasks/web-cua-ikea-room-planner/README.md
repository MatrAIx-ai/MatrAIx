# IKEA Room Planner (CUA — Docker Linux desktop)

MatrAIx **CUA** (computer-use) web task on a live public retail site: a persona
designs a room with IKEA's Room Planner / Home Design tool. A real **headed
Chromium** window runs in a Docker Linux desktop (Xvfb + XFCE) and
`persona-computer-1` drives it from **screenshots** (navigate / click / scroll /
type via xdotool), finishing with a **done** action after writing
`/app/output/room_plan.json` from the desktop terminal.

- URL: https://www.ikea.com/us/en/home-design/room/?roomType=generic
- Output: `/app/output/room_plan.json`
- Environment: `application/shared-web-cua-linux`

## Why a CUA variant

IKEA's Room Planner is a heavy 3D/WebGL drag-and-drop canvas behind bot
protection. A headed desktop browser under Xvfb sends a normal Chrome
user-agent natively (clearing UA/automation-fingerprint blocks with no patch)
and the screenshot loop is closer to real end-user behaviour than DOM-only
browsing — the trade-off is that CUA runs are slower and costlier
(screenshot → model → xdotool, many steps). See
[web-interaction.md](../../web-interaction.md) § CUA for the mode comparison.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-computer-1` |
| Environment | `docker` (Linux Xvfb, `network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |
| API key | `ANTHROPIC_API_KEY` (or Bedrock: `AWS_BEARER_TOKEN_BEDROCK` + `AWS_REGION`) |

Anthropic API:

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/web-cua-ikea-room-planner
```

Bedrock (this repo's host default — Sonnet 4.5 computer-use over a Bedrock
bearer token):

```bash
export AWS_BEARER_TOKEN_BEDROCK=...   # Bedrock API key
export AWS_REGION=us-east-1
uv run harbor run -c configs/jobs/example-job-recipe/appSim-web-cua-ikea-room-planner-bedrock.yaml
```

Oracle (reference submission; no live desktop):

```bash
uv run harbor run -p application/tasks/web-cua-ikea-room-planner -a oracle
```

## Notes

- The verifier checks the **submission schema** (≥3 products with names/prices,
  ≥1 IKEA series, valid budget/room/fit enums, ≥1 modification, ≥1 safety-
  guidance entry, a professional-boundary field, and a written reason) — not
  semantic match to live inventory, which changes over time. On success it
  emits `structured_output.json` with `task_outcome`, `web_artifact`,
  `decision`, `personalization`, `safety_guidance`, and `user_feedback`
  contexts, which `reporting.json` `contextRules` aggregate into the batch
  metrics: design personalization, budget / lifestyle fit, and safety +
  professional-boundary quality.
- CUA writes `room_plan.json` itself from the desktop terminal before finishing
  with a **done** action (no `cua_submission_profile` is needed for this custom
  schema — the profile materializers only cover the fixed decision schemas).
- Known limitation: driving IKEA's 3D canvas by screenshot is demanding and
  slow (~20+ min, many steps). The oracle path emits a schema-valid reference
  submission for a completed job + batch report without a live desktop.

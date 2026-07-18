# Sample batch reports

Illustrative Playground batch-reporting output for this task, checked in so
reviewers can see the aggregation → PDF pipeline without running the job.

- `oracle-batch-report.pdf` — Playground UI batch-report export from an
  **oracle** run (deterministic `MockArenaBrain`, no API key, seed 42,
  player-vs-bots) of the default 4-persona crew (`0001`, `0052`, `0229`,
  `0666`). The oracle replays `solution/solve.sh`: `run_arena.py` plays a full
  match in Docker and the verifier emits one `task_outcome` and one
  `task_reasoning_trajectory` context per crew persona, which this task's
  `reporting.json` `contextRules` aggregate by trait group. Reward 1.0.
  Exported from the **Playground UI** batch-report view (`Download PDF`) — the
  branded front matter (instruction, persona sampling strategy, cohort) plus
  the rendered aggregation — which is more readable than the server-side
  `report.pdf`.

Live persona agents (`persona-browser-use`, `persona-computer-1`) can't
complete this task on a Bedrock-only host — CUA has no Xvfb desktop in this
task's image (in-process `BrowserVisionBrain` is the vision path), and live
browser-use trials authenticate but do not win the game (reward 0). The oracle
is the reliable path to a completed job + batch report here.

These are **sample artifacts, not part of the task contract** — safe to drop
from the PR if the repo prefers not to track generated reports. Regenerate with:

```bash
uv run harbor run -c configs/jobs/application-task-job-recipe/appSim-game-starclash-oracle.yaml --yes
# then open the job in the Playground Runs view and click "Download PDF"
```

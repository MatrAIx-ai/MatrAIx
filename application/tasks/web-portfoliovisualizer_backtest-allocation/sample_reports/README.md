# Sample batch reports

Illustrative Playground batch-reporting output for this task, checked in so
reviewers can see the aggregation → PDF pipeline without running the job.

- `live-run-batch-report.pdf` — batch report from a 2-persona live run
  (personas 0069 risk-averse, 0129 risk-tolerant) on Bedrock Claude Sonnet 4.5.
  Both agents drove the live Portfolio Visualizer site, built distinct
  allocations (35/20/40/5 vs 60/20/15/5 equity/bond splits), read the results,
  and reached opposite `satisfied` verdicts; rendered from the job's
  `aggregation.json` after applying this task's `reporting.json` `contextRules`.

These are **sample artifacts, not part of the task contract** — safe to drop
from the PR if the repo prefers not to track generated reports. Regenerate with:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-web-portfoliovisualizer-backtest-bedrock-smoke2.yaml
# then aggregate + render via the Playground backend (job_aggregation + report_pdf)
```

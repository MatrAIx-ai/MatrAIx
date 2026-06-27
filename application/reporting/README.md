# Application Reporting

Post-batch analysis for **application-oriented** persona simulation jobs
(survey, chat, web, computer-use). This surface is currently a placeholder for
aggregators that read job/trial outputs and produce summaries by task,
interaction form, and persona.

## Adding a report for your task

When you need **application-level metrics** across a persona batch (not single-trial pass/fail):

1. Create `application/reporting/<your-task-name>/` (mirror your task slug).
2. Write scripts that read `jobs/<job_name>/` — `result.json`, each trial’s `persona_meta.json`, verifier output, and artifacts under `artifacts/app/output/`.
3. Emit CSV / JSON / HTML for your team.

Persona **grounding** aggregation should stay under `persona/reporting/` when
that reporting surface is imported.

## Planned inputs

- `jobs/<job_id>/` — Harbor job results (`result.json`, trial dirs)
- `<trial>/persona_meta.json` — written by persona agents at trial start
- `<trial>/verifier/reward.txt` — schema / rewardkit scores

## Planned outputs

- Task × persona metric tables (CSV / JSON)
- Distribution summaries (not single pass/fail rates)
- Optional HTML report for team review

## Related

- Persona grounding reports: `persona/reporting/` after that module lands
- job-level mean/max aggregation
- qualitative trajectory review
- per-trial inspection

## See also

- [Application tasks](../tasks/)

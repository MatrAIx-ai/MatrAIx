# WebMD symptom resource choice (Playwright)

MatrAIx **Playwright** web task on the live public WebMD site. The persona
searches or browses health articles, inspects at least three pages, and selects
the article that best helps them understand a health concern.

- Start URL: https://www.webmd.com/
- Output: `/app/output/symptom_resource_choice.json`
- Self-report: `/app/output/user_feedback.json`
- Authentication: none
- External side effects: none

See [Application Tasks](../README.md) for contribution guidance.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (Playwright image, `network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/web-webmd_symptom-resource-choice
```

Oracle (live Playwright browsing; needs outbound network):

```bash
uv run harbor run \
  -p application/tasks/web-webmd_symptom-resource-choice \
  -a oracle
```

The verifier checks WebMD URL structure, internal consistency across the
submitted article metadata, and requires at least three distinct candidates.
Persona alignment is reported separately from objective task completion; there
is no single globally correct article.

## Evaluation contract

**Harbor name:** `application/webmd-symptom-resource-choice`

**Runtime:** Playwright (`application/shared-web-playwright`) — not CUA.

### What we grade

| Layer | Graded how |
|-------|------------|
| Task success | Binary pass: valid artifacts + structural checks |
| Decision | Which article and why (`decision` context) |
| Decision process | ≥3 distinct WebMD articles compared |
| Source fidelity | Valid `https://www.webmd.com/` article URLs |
| User feedback | Post-run self-report (`user_feedback.json`) |
| Web execution | `web_interaction` + `web_artifact` contexts |

### What we do not grade

- Medical correctness or clinical appropriateness
- Trajectory / action-sequence matching
- Login, booking, purchases, or third-party sites

### Goal components

1. `artifact_present` — output JSON saved  
2. `schema_valid` — required fields and enums  
3. `comparison_breadth` — ≥3 distinct articles  
4. `selection_consistent` — selected row matches choice  
5. `source_fidelity` — WebMD URLs only  

### Batch reporting

Policy in `reporting.json` (execution + persona layers). Roll up with:

```bash
uv run python application/scripts/report_job.py jobs/<job-name>
```

Metric templates: `application/task-spec/web/README.md`

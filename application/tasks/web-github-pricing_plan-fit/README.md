# GitHub Pricing Plan Fit

PersonaBench web task on the live public GitHub pricing page. The persona agent
browses the page in read-only mode, chooses the plan they would seriously
consider, and reports pricing comprehension and trust.

- URL: https://github.com/pricing
- Output: `/app/output/pricing_plan_evaluation.json`

No login, signup, purchase, or organization change is required.

## Suggested Setup

| Field | Value |
|---|---|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (Playwright image, `network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/web-github-pricing_plan-fit
```

Oracle check (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/web-github-pricing_plan-fit -a oracle
```

## Expected Submission

```json
{
  "source_url": "https://github.com/pricing",
  "selected_plan": "Team",
  "fit_rating": 8,
  "trust_rating": 7,
  "budget_fit": "acceptable",
  "conversion_intent": "consider",
  "reason": "The plan includes the collaboration features this persona needs.",
  "friction_points": ["Advanced Security pricing is not clear from the page"]
}
```

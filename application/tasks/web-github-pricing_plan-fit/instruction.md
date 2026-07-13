# GitHub pricing plan fit

Browse the public GitHub pricing page:

https://github.com/pricing

Act as the assigned persona. Decide which GitHub plan you would seriously
consider for your own context, such as an individual project, student use,
open-source maintenance, startup team, or security-sensitive organization.

Do not sign in, start a trial, contact sales, create an account, or change any
GitHub setting. This is a read-only pricing-comprehension task.

Write your result to `/app/output/pricing_plan_evaluation.json`:

```json
{
  "source_url": "https://github.com/pricing",
  "selected_plan": "<Free, Pro, Team, Enterprise, or Unsure>",
  "fit_rating": 1,
  "trust_rating": 1,
  "budget_fit": "<too_expensive, acceptable, good_value, unclear, or not_applicable>",
  "conversion_intent": "<avoid, compare_more, consider, or choose>",
  "reason": "<why the selected plan does or does not fit your persona>",
  "friction_points": ["<pricing, trust, feature, or signup confusion>"]
}
```

Ratings must be integers from 1 to 10. Use only information visible on the page
or directly linked official GitHub pricing/docs pages.

Suggested agent: `persona-openhands-sdk` (terminal + Python).

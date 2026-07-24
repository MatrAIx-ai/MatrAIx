# Compare Cloudflare Network & CDN plans

## Your situation

You are responsible for recommending a Cloudflare **Network & CDN** plan for
your organization's public-facing website. Read `input/context.md`, then make
your recommendation.

## Your goal

Use the live Cloudflare pricing page to compare the four Network & CDN plans
and recommend the **one plan you would choose** for your organization.

## Constraints on your behavior

- Use only plan information visible on the live Cloudflare pricing page.
- Use the organization type or size in your background. Your organization may
  be identified by either its size or its sector, such as academia or the
  public sector. Do not treat sectors as size categories.
- Do not invent quantitative traffic, compliance, security, support, uptime,
  or other requirements that are not stated in your background or on the page.
- Do not log in, create an account, sign up, purchase, check out, contact
  sales, contact anyone, or visit a linked plan-registration page.

## Interaction requirements

Stay in the **Network & CDN** category. Inspect the summaries for all four
plans—Free, Pro, Business, and Contract—and examine the visible feature
comparison before deciding. Compare published prices, billing terms, intended
audiences, included features, and other visible information when relevant.

Save your recommendation to
`/app/output/cloudflare_plan_comparison.json`:

```json
{
  "decision_subject_id": "<free|pro|business|contract>",
  "decision_subject_label": "<Free|Pro|Business|Contract>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this plan fits your organization and priorities, grounded in the page>",
  "task_pricing_category": "Network & CDN",
  "task_source_url": "https://www.cloudflare.com/plans/",
  "task_price_text": "<selected plan price and billing text as shown>",
  "task_target_text": "<selected plan audience description as shown>",
  "task_options_considered": [
    {
      "decision_subject_id": "<free|pro|business|contract>",
      "decision_subject_label": "<Free|Pro|Business|Contract>",
      "task_price_text": "<price and billing text as shown>",
      "task_target_text": "<audience description as shown>",
      "task_relevance_note": "<why this plan suits or does not suit your organization>"
    }
  ]
}
```

## Termination criteria

- `task_options_considered` must contain exactly one entry for each of the four
  Network & CDN plans: Free, Pro, Business, and Contract.
- The selected plan must appear in `task_options_considered`, with matching
  stable ID, canonical label, price text, and audience description.
- Use the fixed lowercase plan IDs shown in the schema and copy each plan
  heading exactly from its plan card.
- Keep price, billing, and audience text faithful to the rendered live page; do
  not invent metadata.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to your organization, priorities, and visible
  differences among the plans.
- Do not invent quantitative traffic, compliance, security, support, or uptime
  requirements that are not stated in your background or on the page.
- Finish after saving the completed JSON file.

## Success judgment

The task is successful when the saved JSON follows the required structure,
includes one internally consistent entry for each of the four Network & CDN
plans, recommends one of those entries, and keeps every plan label, price,
billing term, and audience description faithful to the live page.

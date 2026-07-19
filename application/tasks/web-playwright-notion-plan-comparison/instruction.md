# Compare Notion workspace plans

Read the scenario brief in `input/context.md`. Use the live Notion pricing page
to select the **one standard workspace plan** that you would most realistically
choose for the personal or work context represented in your persona.

Immediately after the pricing page loads, **click or otherwise activate Pay
monthly at least once**, even if it appears to be selected or the prices
already say “per month.” Do not treat the mere presence of the “Pay monthly”
label as evidence that monthly billing is selected: the page can display that
label while showing annual-billing rates. After activating the control, verify
its selected state or that the rendered plan-card prices update before
recording them. If a text-label click fails, locate and use its interactive
parent or associated control rather than assuming the state is already
correct.

Inspect the summaries for all four plans—Free, Plus, Business, and
Enterprise—and examine relevant parts of the visible feature comparison before
deciding. Compare published monthly prices, intended audiences, included
features, and other visible information when relevant.

Save your choice to `/app/output/notion_plan_comparison.json`:

```json
{
  "decision_subject_id": "<free|plus|business|enterprise>",
  "decision_subject_label": "<Free|Plus|Business|Enterprise>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this plan fits your persona and realistic context, grounded in the page>",
  "task_billing_mode": "monthly",
  "task_source_url": "https://www.notion.com/pricing",
  "task_price_text": "<selected plan standard monthly price text as shown>",
  "task_target_text": "<selected plan audience description as shown>",
  "task_options_considered": [
    {
      "decision_subject_id": "<free|plus|business|enterprise>",
      "decision_subject_label": "<Free|Plus|Business|Enterprise>",
      "task_price_text": "<standard monthly price text as shown>",
      "task_target_text": "<audience description as shown>",
      "task_relevance_note": "<why this was a plausible or implausible option for you>"
    }
  ]
}
```

Requirements:

- `task_options_considered` must contain exactly one entry for each standard
  plan: Free, Plus, Business, and Enterprise.
- The selected plan must appear in `task_options_considered`, with matching
  stable ID, canonical label, price text, and audience description.
- Use the fixed lowercase plan IDs shown in the schema and copy each plan
  heading exactly from its plan summary.
- Keep monthly price and audience text faithful to the rendered live page; do
  not invent metadata.
- Use the standard public plan cards. Do not apply education discounts,
  promotions, or negotiated pricing.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to your persona, realistic use context, and visible
  differences among the plans.
- Do not invent an exact team size, compliance requirement, security policy,
  or organizational rule that is not stated in your persona or on the page.
- If your persona has no work or organization context, choose for your own
  individual use.

No login, account creation, signup, purchase, demo request, or contact-sales
action is required.

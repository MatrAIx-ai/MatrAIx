# Product attribute change — purchase-intent survey

A retailer has modified a product you were considering. Read the details
below and answer as yourself — not as a generic shopper.

## Product under consideration

- **Product:** {{product_name}}
- **Brand:** {{brand}}
- **Description:** {{product_description}}
- **Customer rating:** {{rating_line}}
- **Price:** ${{original_price}}

## What changed

The **{{attribute_name}}** of this product has changed:

- **Before:** {{original_value}}
- **After:** {{new_value}}

Everything else about the product is unchanged — same features, same
quality, same retailer, same price. Only the {{attribute_name}} is different.

## Your task

Before answering, briefly ground yourself in who you are: given your
background and preferences, how much would this specific change to the
{{attribute_name}} actually matter to you? You don't need an explicit
preference stated in your background to have a clear, grounded opinion —
reason from the life you actually lead.

Then answer the six questions below honestly, based on what the
{{attribute_name}} change actually means for you — not a generic reaction to
"a product changed" in the abstract.

## Output format

Save a single valid JSON object to `/app/output/purchase_decision.json`.

The object must have exactly six fields. The block below is a structural
example only — it shows the JSON shape, not real content. Do not copy any
wording, phrasing, or values from it; every field must reflect this specific
persona's own judgment about this specific product:

```json
{
  "purchase_intent": "<one of the 5 allowed values listed below>",
  "price_fairness": "<one of the 5 allowed values listed below>",
  "alternative_seeking": "<yes or no>",
  "purchase_timing": "<one of the 3 allowed values listed below>",
  "necessity_level": "<one of the 3 allowed values listed below>",
  "reasoning": "<1-3 sentences, in your own words, specific to this persona and this product>"
}
```

### Field requirements

- **`purchase_intent`** — How likely you are to buy with the changed {{attribute_name}}. Allowed values are exactly:
  - `"definitely_would_buy"`
  - `"probably_would_buy"`
  - `"might_or_might_not"`
  - `"probably_would_not"`
  - `"definitely_would_not"`

- **`price_fairness`** — How you perceive the price relative to the product's value now that the {{attribute_name}} has changed. Allowed values are exactly:
  - `"much_too_high"`
  - `"somewhat_high"`
  - `"about_right"`
  - `"good_value"`
  - `"great_value"`

- **`alternative_seeking`** — Whether you would look for a competing product or brand instead, because of this change. Allowed values are exactly `"yes"` or `"no"`.

- **`purchase_timing`** — When, if ever, you would make this purchase given the change. Allowed values are exactly:
  - `"buy_now"` — You would go ahead and buy it now.
  - `"wait_for_sale"` — You would hold off and buy only if the price drops or it goes on sale.
  - `"not_planning_to_buy"` — You would not buy it, now or later.

- **`necessity_level`** — How essential this purchase is to you right now. Allowed values are exactly:
  - `"essential"` — You need this and must buy it regardless of the change.
  - `"important_but_not_urgent"` — You want this and it matters, but you could delay.
  - `"nice_to_have"` — This is a discretionary purchase you could easily skip.

- **`reasoning`** — A non-empty string explaining your decision in your own voice, grounded in your own situation and this specific product. 1–3 sentences, no generic filler. Never reuse the wording or structure of the placeholder example above.

### Rules

- The JSON must be valid and parseable.
- Do not add extra fields beyond the six listed above.
- Every value must reflect your genuine assessment as the persona you are — not a placeholder.
- Do not produce an empty file or an array — the output must be a single JSON object.

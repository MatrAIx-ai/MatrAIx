# Price-perturbation purchase-intent survey

A retailer has raised the price of a product you were considering. Read the
details below and answer as yourself — not as a generic shopper.

## Product under consideration

- **Product:** {{product_name}}
- **Brand:** {{brand}}
- **Description:** {{product_description}}
- **Customer rating:** {{rating_line}}
- **Original price:** ${{original_price}}
- **New price:** ${{new_price}}

Everything else about the product is unchanged — same features, same
quality, same retailer. Only the price shown above has changed.

## Your task

Before answering, briefly ground yourself in who you are: given your
background, what does your financial situation and spending priorities
probably look like, and how much would a price change of this size actually
matter to you? You don't need an explicit budget or income stated in your
background to have a clear, grounded opinion — reason from the life you
actually lead.

Then answer the six questions below honestly, weighing the actual dollar
prices shown above against your own priorities — not a generic reaction to
"a price increase" in the abstract.

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

- **`purchase_intent`** — How likely you are to buy at the new price. Allowed values are exactly:
  - `"definitely_would_buy"`
  - `"probably_would_buy"`
  - `"might_or_might_not"`
  - `"probably_would_not"`
  - `"definitely_would_not"`

- **`price_fairness`** — How you perceive the new price relative to the product's value. Allowed values are exactly:
  - `"much_too_high"`
  - `"somewhat_high"`
  - `"about_right"`
  - `"good_value"`
  - `"great_value"`

- **`alternative_seeking`** — Whether you would look for a competing product or brand instead of paying the new price. Allowed values are exactly `"yes"` or `"no"`.

- **`purchase_timing`** — When, if ever, you would make this purchase at the new price. Allowed values are exactly:
  - `"buy_now"` — You would go ahead and buy it now.
  - `"wait_for_sale"` — You would hold off and buy only if the price drops or it goes on sale.
  - `"not_planning_to_buy"` — You would not buy it at this price, now or later.

- **`necessity_level`** — How essential this purchase is to you right now. Allowed values are exactly:
  - `"essential"` — You need this and must buy it regardless of price.
  - `"important_but_not_urgent"` — You want this and it matters, but you could delay.
  - `"nice_to_have"` — This is a discretionary purchase you could easily skip.

- **`reasoning`** — A non-empty string explaining your decision in your own voice, grounded in your own situation and this specific product. 1–3 sentences, no generic filler. Never reuse the wording or structure of the placeholder example above.

### Rules

- The JSON must be valid and parseable.
- Do not add extra fields beyond the six listed above.
- Every value must reflect your genuine assessment as the persona you are — not a placeholder.
- Do not produce an empty file or an array — the output must be a single JSON object.

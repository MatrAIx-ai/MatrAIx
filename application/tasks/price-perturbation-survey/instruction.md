# Price-perturbation purchase-intent survey

A retailer has raised the price of a product you were considering buying.
Review the product details below and decide — as yourself — whether you would
still purchase it at the new, higher price.

## Product under consideration

- **Product:** {{product_name}}
- **Description:** {{product_description}}
- **Original price:** ${{original_price}}
- **New price (after increase):** ${{new_price}}

The new price is approximately 25% higher than the original. The product itself
is unchanged — same features, same quality, same retailer. Only the listed
price has increased.

## Your task

Think through how this price increase affects your willingness to buy. Consider
your personal budget, how much you need or want this product, whether
alternatives exist at a lower price, and whether the new price still feels
reasonable for what the product offers.

Then make a clear purchase decision: would you still buy this product at the
new price, or not?

## Output format

Save a single valid JSON object to `/app/output/purchase_decision.json`.

The object must have exactly two fields:

```json
{
  "would_buy": "yes",
  "reasoning": "Even at the higher price, this still fits comfortably within my budget and I have been planning to buy one for a while."
}
```

### Field requirements

- **`would_buy`** — Your purchase decision. Allowed values are exactly `"yes"` or `"no"`. No other value is accepted.
  - `"yes"` — You would still buy the product at the new, higher price.
  - `"no"` — You would not buy the product at the new, higher price.

- **`reasoning`** — A non-empty string explaining your decision in your own voice. Write 1–3 sentences that reflect your actual perspective: your financial situation, your need for the product, how you feel about the price increase, and any alternatives you might consider. Do not write generic filler. Do not copy the example text above — write your own reasoning.

### Rules

- The JSON must be valid and parseable.
- Do not add extra fields beyond `would_buy` and `reasoning`.
- Do not use placeholder values. Every value must reflect your genuine assessment as the persona you are.
- Do not produce an empty file or an array — the output must be a single JSON object.

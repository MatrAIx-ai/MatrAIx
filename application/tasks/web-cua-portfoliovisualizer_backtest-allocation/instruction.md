# Backtest a portfolio asset allocation (live web)

Use the Portfolio Visualizer **Backtest Portfolio** tool at:

https://www.portfoliovisualizer.com/backtest-portfolio

Explore the tool as **yourself** — someone with your own financial situation,
goals, and risk preference. Construct one or more candidate asset allocations,
run a historical backtest, read the results, and decide whether the portfolio
fits your goals.

## What to do

1. **Assume your own situation.** Ground every choice in your persona: your
   income and investable assets, your age and time horizon, your investment
   goal (retirement, wealth growth, income generation, or capital
   preservation), and your risk tolerance (conservative, moderate, or
   aggressive). Honour any personal constraints — ethical/sector preferences,
   currency, or cultural/religious investment rules (for example avoiding
   interest-bearing instruments) and family obligations.
2. **Input details gradually.** Set the allocation across asset classes one
   step at a time (for example US stocks, international stocks, bonds, REITs,
   gold/commodities, cash). Pick a start year and initial amount that match your
   real horizon rather than the tool's defaults.
3. **Run the backtest** and read the key metrics the tool reports — final
   balance, CAGR, standard deviation, best/worst year, maximum drawdown, and
   the Sharpe ratio.
4. **Flag unrealistic assumptions.** If the projection looks overly optimistic —
   a short backtest window that misses a downturn, survivorship in the sample
   period, extrapolating past CAGR into the future, or a drawdown you could not
   actually tolerate given your horizon — say so explicitly.

No login, payment, or account is required. Read the numbers from the live
results page — do not invent values. Pages change, so record what you actually
see.

## Submission

Write your configuration, the results you read, and your judgement to
`/app/output/portfolio_backtest.json`:

```json
{
  "persona_context": {
    "investment_goal": "retirement | wealth_growth | income_generation | capital_preservation",
    "risk_tolerance": "conservative | moderate | aggressive",
    "time_horizon_years": 20,
    "constraints": ["<e.g. no interest-bearing assets, ESG only, GBP base currency, none>"]
  },
  "backtest_config": {
    "start_year": 2005,
    "initial_amount_usd": 10000,
    "allocation": [
      { "asset_class": "US Stock Market (VTSMX)", "percent": 60 },
      { "asset_class": "Total US Bond Market (VBMFX)", "percent": 40 }
    ]
  },
  "results": {
    "final_balance_usd": "<number or string exactly as shown, e.g. 45123.45>",
    "cagr_percent": "<number or string as shown, e.g. 7.85>",
    "stdev_percent": "<number or string as shown>",
    "max_drawdown_percent": "<number or string as shown>",
    "sharpe_ratio": "<number or string as shown>"
  },
  "goal_alignment": "aligned | partially_aligned | misaligned",
  "flagged_concerns": [
    "<each unrealistic assumption or overly optimistic projection you noticed>"
  ],
  "satisfied": true,
  "reason": "<why this allocation does or does not fit you as this persona>"
}
```

Rules for the submission:

- `allocation` must list at least two asset classes and the `percent` values
  must sum to **100**.
- `investment_goal` and `risk_tolerance` must use one of the enumerated values.
- `goal_alignment` must be one of `aligned`, `partially_aligned`, `misaligned`.
- `flagged_concerns` must be a list — include at least one concern if the
  backtest relies on any optimistic or unrealistic assumption; use an empty
  list only if you genuinely found none.
- `satisfied` must be `true` or `false`.
- `reason` must explain the fit in your own voice (at least a sentence).

# Recipe to cook this week

Read `input/context.md` for scenario and application background.

Save your choice to `/app/output/recipe_choice.json`:

```json
{
  "decision_subject_id": "<stable slug you derive from the recipe title or its URL path>",
  "decision_subject_label": "<recipe title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this recipe matched you>",
  "task_total_time_label": "<total time exactly as shown on the recipe page>",
  "task_url": "<AllRecipes URL of the recipe page you chose>"
}
```

Requirements:

- `decision_subject_id` can be the recipe slug from the page URL.
- `basis_primary` should capture the main reason this recipe fits you (for
  example `taste`, `convenience` for a quick weeknight meal, or `price` for a
  budget cook).
- Keep `reason` specific to the chosen recipe and your persona's diet, taste,
  time budget, and cooking skill.
- Read the title and total time from the live recipe page; do not invent values.

No account, saving, or rating action is required.

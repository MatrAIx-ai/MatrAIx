# Choose an Allrecipes recipe

Read the scenario brief in `input/context.md`. Use the live Allrecipes website
to choose the **one recipe you would most realistically prepare for an upcoming
meal**.

Search or browse the catalog, then open and inspect at least **three distinct
recipe-detail pages** before deciding. Compare ingredients, total time,
servings, preparation difficulty, cuisine, familiarity, novelty, and other
information when they are relevant to you. Use dietary or health-related
constraints only when they are explicitly present in your persona; do not
invent allergies, medical restrictions, religious restrictions, household
needs, or available equipment.

Save your choice to `/app/output/recipe_choice.json`:

```json
{
  "decision_subject_id": "<numeric recipe ID from the selected Allrecipes URL>",
  "decision_subject_label": "<recipe title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this recipe fits you, grounded in your persona and the pages you inspected>",
  "task_recipe_url": "https://www.allrecipes.com/recipe/<numeric-id>/<recipe-slug>/",
  "task_total_time_text": "<total time exactly as shown>",
  "task_servings": "<positive integer servings count>",
  "task_options_considered": [
    {
      "decision_subject_id": "<numeric recipe ID>",
      "decision_subject_label": "<recipe title exactly as shown>",
      "task_recipe_url": "https://www.allrecipes.com/recipe/<numeric-id>/<recipe-slug>/",
      "task_total_time_text": "<total time exactly as shown>",
      "task_servings": "<positive integer servings count>",
      "task_relevance_note": "<why this was a plausible candidate for you>"
    }
  ]
}
```

Requirements:

- `task_options_considered` must contain at least three distinct recipes whose
  detail pages you actually opened.
- The selected recipe must appear in `task_options_considered`, with matching
  title, numeric ID, URL, total time, and servings.
- Use the numeric recipe ID from the URL as `decision_subject_id`.
- Keep titles, total-time text, and servings faithful to the live pages; do not
  invent metadata.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to both your persona and evidence from the selected
  recipe page.

No login, account creation, saving, rating, reviewing, photo upload, newsletter
signup, purchase, sharing, contact action, or third-party-site visit is
required. Do not treat the recipe selection as medical or nutritional advice.

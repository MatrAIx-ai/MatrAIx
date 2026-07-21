# What to see at the Met

Read `input/context.md` for scenario and application background.

Save your choice to `/app/output/visit_pick.json`:

```json
{
  "decision_subject_id": "<stable id: collection object number from the URL, or a slug you derive from the exhibition title>",
  "decision_subject_label": "<exhibition or artwork title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this pick matched you>",
  "task_pick_type": "<exhibition or artwork>",
  "task_url": "<Met Museum URL of the page you chose>"
}
```

Requirements:

- Pick either a **current exhibition** or a **specific artwork** from the
  online collection — whichever you would genuinely prioritize on a visit.
- For artworks, use the numeric id from the collection URL
  (`/art/collection/search/<id>`) as `decision_subject_id`; for exhibitions,
  derive a simple slug from the title.
- `basis_primary` should capture the main reason this pick appeals to you.
- Keep `reason` specific to the chosen pick and your persona's cultural
  interests and visit plans.
- Read titles from the live pages; do not invent values.

No ticket purchase, account, or booking action is required.

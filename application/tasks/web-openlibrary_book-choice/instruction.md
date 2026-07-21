# Book to read next

Read `input/context.md` for scenario and application background.

Save your choice to `/app/output/book_choice.json`:

```json
{
  "decision_subject_id": "<Open Library work id (e.g. OL45883W) or a stable slug you derive from the title>",
  "decision_subject_label": "<book title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this book matched you>",
  "task_author": "<author name exactly as shown>",
  "task_url": "<Open Library URL of the book page you chose>"
}
```

Requirements:

- Prefer the Open Library work id from the page URL (the `OL...W` segment) for
  `decision_subject_id`; fall back to a simple slug of the title if needed.
- `basis_primary` should capture the main reason this book appeals to you.
- Keep `reason` specific to the chosen book and your persona's reading taste.
- Read title and author from the live page; do not invent values.

No login, borrowing, or list-saving action is required.

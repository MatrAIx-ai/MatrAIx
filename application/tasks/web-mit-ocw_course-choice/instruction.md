# Course to start learning

Read `input/context.md` for scenario and application background.

Save your choice to `/app/output/course_choice.json`:

```json
{
  "decision_subject_id": "<stable slug from the course page URL path>",
  "decision_subject_label": "<course title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this course matched you>",
  "task_course_number": "<MIT course number exactly as shown (e.g. 6.0001)>",
  "task_url": "<OCW URL of the course page you chose>"
}
```

Requirements:

- `decision_subject_id` can be the course slug from the page URL
  (e.g. `6-0001-introduction-to-computer-science-...`).
- `basis_primary` should capture the main reason this course fits you (for
  example `fit` for matching your learning goal, or `quality` for depth of
  materials).
- Keep `reason` specific to the chosen course and your persona's learning
  goals, background, and available time.
- Read the course title and number from the live page; do not invent values.

No account, enrollment, or download action is required.

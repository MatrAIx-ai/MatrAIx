# Choose a WebMD article for your health concern

## Your situation

You want to understand a health concern or symptom you have been thinking about.
Read the scenario brief in `input/context.md`, then use the live WebMD website
to find information that fits you.

## Your goal

Search or browse the public WebMD site, open and inspect at least **three
distinct health article pages**, compare them, and choose the **one article
that best helps you understand your concern and think about next steps**.

## Constraints on your behavior

- Use only information visible on the live WebMD site at `https://www.webmd.com/`.
- Do not invent symptoms, diagnoses, test results, or treatment plans.
- This task evaluates whether you completed a thoughtful browse-and-choose flow,
  not whether a clinician would agree with your choice.
- Do not log in, book care, purchase products, download apps, contact anyone,
  or visit third-party sites outside WebMD.
- Do not treat WebMD as a substitute for professional medical advice.

## Interaction requirements

Use the live website in the browser. Compare article titles, scope, tone, and
what each page emphasizes (for example causes, symptoms, treatment, lifestyle
changes, or when to seek care) when those differences matter to you.

Save your choice to `/app/output/symptom_resource_choice.json`:

```json
{
  "decision_subject_id": "<stable slug derived from the selected article URL path>",
  "decision_subject_label": "<article title copied from the page main heading>",
  "decision_outcome": "selected",
  "basis_primary": "<trust|fit|quality|features|convenience|familiarity|novelty|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this article best fits your concern, grounded in the pages you inspected>",
  "task_concern_summary": "<one sentence restating the health concern you brought to the task, in your own words>",
  "task_article_url": "https://www.webmd.com/<path-to-selected-article>",
  "task_source_url": "https://www.webmd.com/",
  "used_search": "<optional true or false>",
  "task_options_considered": [
    {
      "decision_subject_id": "<slug>",
      "decision_subject_label": "<title copied from the page main heading>",
      "task_article_url": "https://www.webmd.com/<path>",
      "task_topic_focus": "<what this article emphasizes, e.g. causes, treatment, when to see a doctor>",
      "task_relevance_note": "<why this was a plausible candidate for you>"
    }
  ]
}
```

After saving the JSON, complete the post-run self-report defined in
`input/self_report_schema.yaml` and save it to `/app/output/user_feedback.json`.

## Termination criteria

- `task_options_considered` must contain at least three distinct WebMD articles
  whose detail pages you actually opened.
- For every article you record, copy its title from the main heading of that
  article page, not from a search result snippet, browser title, or sidebar card.
- The selected article must appear in `task_options_considered` with matching
  slug, title, and URL.
- Use `https://www.webmd.com/` article URLs only. Derive `decision_subject_id`
  from the URL path (for example `heart-disease-what-causes-heart-palpitations`).
  When a path segment contains underscores, normalize them to hyphens in the slug.
- Keep titles, topic focus notes, and concern summary faithful to what you read;
  do not invent page content.
- `basis_secondary` is optional. If included, it must differ from `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to your concern, priorities, and evidence from the
  selected article.
- Finish after saving both completed JSON files.

## Success judgment

The task is successful when the saved JSON follows the required structure, the
candidate list contains at least three distinct WebMD articles you visited, the
selected article matches one candidate, and all recorded titles, slugs, and URLs
are faithful to the live site.

# Compare self-hosted note-taking tools

## Your situation

You are considering a self-hosted note-taking tool. Read the scenario brief in
`input/context.md`, then make the choice as yourself.

## Your goal

Use the live awesome-selfhosted website to review the **Note-taking & Editors**
category, compare three plausible projects in more depth, and select the **one
project you would most realistically try first**.

## Constraints on your behavior

- Use the recommended HTML edition of awesome-selfhosted as the discovery
  source. Start at
  `https://awesome-selfhosted.net/tags/note-taking--editors.html`.
- Do not invent a server, team, compliance requirement, security policy,
  budget, or feature need that is not included in the information provided
  about you or on the pages you inspect.
- Do not infer that a project is easy or difficult to run solely from its star
  count. Look at its listed platform information and a linked project page.
- Do not log in, create an account, install or run software, download files,
  make a purchase, contact anyone, or change anything on an external service.

## Interaction requirements

1. Browse at least five distinct project listings in the **Note-taking &
   Editors** category.
2. Shortlist exactly three projects that you consider plausible for your own
   use. Copy each project name exactly from its level-three heading on the
   category page.
3. For every shortlisted project, open at least one linked **Website** or
   **Source Code** page. Use that page together with the awesome-selfhosted
   listing to understand the project's purpose and likely hosting burden.
4. Compare the three projects using the listing description, platform or
   deployment labels, license, last-update signal, and any relevant information
   from the linked page. Record both a fit and a tradeoff for every project.
5. Select one of the three projects. Base the decision on your realistic needs,
   priorities, and tolerance for technical complexity.

Save the result to `/app/output/selfhosted_note_tool_comparison.json`:

```json
{
  "decision_subject_id": "<selected project's Source Code URL>",
  "decision_subject_label": "<selected project name exactly as shown in the category heading>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this project best fits your realistic context, grounded in the pages inspected>",
  "task_source_url": "https://awesome-selfhosted.net/tags/note-taking--editors.html",
  "task_category_label": "Note-taking & Editors",
  "task_projects_reviewed_count": 5,
  "task_shortlist": [
    {
      "decision_subject_id": "<project's Source Code URL>",
      "decision_subject_label": "<project name exactly as shown in the category heading>",
      "task_project_url": "<Website URL copied from the listing; use the Source Code URL when no separate Website link exists>",
      "task_source_code_url": "<Source Code URL copied from the listing>",
      "task_detail_evidence_url": "<linked Website or Source Code URL that you opened>",
      "task_description": "<project description from the awesome-selfhosted listing>",
      "task_platforms": ["<one or more platform/deployment labels shown in the listing>"],
      "task_licenses": ["<one or more license labels shown in the listing>"],
      "task_last_update": "<YYYY-MM-DD or ?>",
      "task_fit_note": "<why this project could fit you>",
      "task_tradeoff_note": "<the most important drawback or uncertainty for you>"
    }
  ]
}
```

## Termination criteria

- `task_projects_reviewed_count` must be an integer of at least 5.
- `task_shortlist` must contain exactly three distinct projects.
- The selected project must appear exactly once in `task_shortlist`, with the
  same label and Source Code URL.
- Use each project's Source Code URL as its stable `decision_subject_id`.
- Copy project names, project links, descriptions, platform/deployment labels,
  licenses, and update dates from the live category page rather than inventing
  metadata.
- `task_detail_evidence_url` must equal that project's recorded Website or
  Source Code URL, and you must actually open it before recording it.
- `task_platforms` and `task_licenses` must each contain at least one label.
- Use `?` only when the listing itself shows no update date.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason`, fit notes, and tradeoff notes specific to your realistic
  context and the pages you inspected.
- Finish after saving the completed JSON file.

## Success judgment

The task is successful when the saved JSON follows the required structure,
shows that at least five listings were reviewed, contains an internally
consistent three-project comparison, selects one of those projects, and keeps
all recorded project metadata faithful to the live awesome-selfhosted page.

# MatrAIx Migration Provenance

This directory records provenance for the MatrAIx-to-PersonaBench migration. It is metadata-only and does not import code into `main`.

Files:

- `main_commits.tsv`: first-parent MatrAIx `main` commits, including source author/committer metadata and the PersonaBench migration PR/branch/commit mapping. Skipped commits are included with `migration_status=skipped`.
- `source_prs.tsv`: every MatrAIx GitHub PR and the PersonaBench PR that imported it as a snapshot or diff.
- `source_pr_commits.tsv`: commits inside every MatrAIx GitHub PR, including commit authors, emails, dates, subjects, and bodies where available from GitHub.

Important exclusions:

- `06a5450001128b696e4116176c5cf00a9a0734ae` was intentionally skipped because it removed legacy scaffold directories from the old MatrAIx main.
- `30e1e5a4992c8c207a6d49480d757b84121352bd` was skipped because it had an empty diff.

Generated from local migration reports under `/tmp/personabench_full_matraix_migration` and live GitHub PR metadata for `MatrAIx-ai/MatrAIx`.

# Persona Annotation Package Tool

Build self-contained annotation packages for collaborators. The owner keeps
raw data and source databases locally; workers receive only a compact package
with `tasks.jsonl`, `dimensions.json`, `assignment.json`, `package_manifest.json`,
`run_assignment.sh`, and `collab_kit/`.

Generated package directories and `.tar.gz` archives are handoff artifacts, not
source files. Do not commit them.

## Wiki Profiles

```bash
python -m persona.tools.annotation_package.cli make \
  --source wiki \
  --db /tmp/matraix_wiki_profiles_20260601_v1.sqlite \
  --range 100:200 \
  --out-dir /tmp/A_100_200_worker \
  --assignment-id A_100_200 \
  --worker-id worker \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 SHA256_OF_SOURCE_DB
```

The wiki source expects a SQLite `profiles` table with:

- `global_idx`
- `task_id`
- `qid`
- `title`
- `source_url`
- `profile_text`
- optional `input_sha256`

If `input_sha256` is absent, the tool computes one from the immutable task
payload.

## Amazon Reviews

```bash
python -m persona.tools.annotation_package.cli make \
  --source amazon-reviews \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --range 0:100 \
  --out-dir /tmp/amazon_0_100_worker \
  --assignment-id amazon_0_100 \
  --worker-id worker \
  --dataset-id matraix_amazon_reviews_2023_user_histories_v1 \
  --dataset-sha256 SHA256_OF_USER_HISTORIES
```

The Amazon source renders one reviewer per task. Reviews are sorted by time,
spread across `--cv-folds` folds, and rendered into fold-labeled evidence so the
starter solver can require support across folds.

Useful Amazon options:

- `--cv-folds 3`
- `--min-support-folds 2`
- `--max-reviews-per-user 90`
- `--max-review-text-chars 900`
- `--max-profile-text-chars 70000`

## Worker Flow

Send the generated `.tar.gz` to the worker. They unpack and run:

```bash
tar -xzf A_100_200_worker.tar.gz
cd A_100_200_worker
./run_assignment.sh --status
./run_assignment.sh
./run_assignment.sh --validate
```

Workers should return `results.jsonl`.

## Owner Merge

Use `merge_results.merge_results()` from Python for owner-side validation and
merge. It validates returned rows against `dimensions.json`, optionally checks
profile identity against a source SQLite DB, and unions fields by `global_idx`.

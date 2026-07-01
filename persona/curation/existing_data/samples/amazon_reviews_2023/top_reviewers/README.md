# Amazon Top Reviewer Queues

This directory contains reusable reviewer ID queues for staged Amazon Reviews
2023 persona curation.

`amazon_top_10000_rich_persona_reviewer_ids_2018_2023.md` lists 10,000
high-signal reviewer IDs selected from the 2018-2023 eligible-user artifact.
It stores IDs and lightweight selection context only, not review histories.

To build a worker-facing package directly from a rank slice of this queue, run:

```bash
persona/curation/existing_data/scripts/make_amazon_top_reviewer_package.sh \
  0:100 \
  alice
```

The wrapper writes a temporary rank-slice ID file, exports the matching user
histories from the Hugging Face user-bucket artifact, and then builds an Amazon
collaborator package with `make_package.py`. Set `MATRIX_DATA_ROOT` and
`MATRIX_PACKAGE_OUT_ROOT` to control where local histories and package archives
are written.

To retrieve only the corresponding review histories, pass this file to:

```bash
python3 persona/curation/existing_data/scripts/export_hf_amazon_user_histories.py \
  --user-ids persona/curation/existing_data/samples/amazon_reviews_2023/top_reviewers/amazon_top_10000_rich_persona_reviewer_ids_2018_2023.md \
  --output /path/to/user_histories.jsonl.gz
```

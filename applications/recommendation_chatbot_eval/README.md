# Recommendation Chatbot Evaluation

This directory tracks the application-side data interface for persona-conditioned
recommendation chatbot evaluation.

The working scope is a normalized candidate catalog: every domain exposes a list
of recommendable items, and every item exposes enough text and metadata for a
recommendation bot to reason over. The evaluation environment and chatbot logic
should depend on the normalized catalog interface, not on each source dataset's
raw file format.

## Current Decision

Use a small movie catalog first for local testing, based on the CMU Movie Summary
Corpus shape. Keep the same catalog schema so later domains can plug in without
changing the recommendation bot interface.

Full source datasets should not be committed to this repository. The repo should
contain only:

- dataset documentation and source manifests,
- schema definitions,
- adapters/loaders when implemented,
- tiny fixtures for local tests and CI.

Large raw and normalized data should live under gitignored local paths:

```text
data/raw/<source_name>/
data/normalized/recommendation_catalogs/<source_name>/
```

## Files

- [DATASETS.md](DATASETS.md): candidate dataset inventory and field coverage.
- [LOCAL_MOVIE_TESTING.md](LOCAL_MOVIE_TESTING.md): movie-first local testing plan.
- [schemas/catalog_item.schema.json](schemas/catalog_item.schema.json): normalized catalog item schema.
- [samples/cmu_movie_summary_tiny.jsonl](samples/cmu_movie_summary_tiny.jsonl): tiny synthetic movie fixture using the normalized shape.

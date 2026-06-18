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
- [INTERECAGENT_PROVIDER.md](INTERECAGENT_PROVIDER.md): setup and boundary notes for the Microsoft RecAI/InteRecAgent provider.
- [schemas/catalog_item.schema.json](schemas/catalog_item.schema.json): normalized catalog item schema.
- [samples/cmu_movie_summary_tiny.jsonl](samples/cmu_movie_summary_tiny.jsonl): tiny synthetic movie fixture using the normalized shape.

## RecBot Provider

The RecBot provider layer gives MatrAIx a normalized request/result contract for
external recommendation backends. For Microsoft RecAI/InteRecAgent, MatrAIx owns
the `RecBotRequest`, `RecBotTurnResult`, subprocess provider, JSON bridge, and
tests around that boundary. InteRecAgent remains the source of truth for
conversational recommendation reasoning, tool planning, retrieval, ranking, and
domain resources.

InteRecAgent native output is preserved inside the `RecBotTurnResult` envelope:
`native_action.raw` carries the backend's native `Final Answer` or
`Action ToolExecutor` text, while `trace` carries normalized inspection fields
such as raw tool plans and tool outputs when available. See
[INTERECAGENT_PROVIDER.md](INTERECAGENT_PROVIDER.md) for local setup,
environment variables, smoke testing, and the default unit test command.

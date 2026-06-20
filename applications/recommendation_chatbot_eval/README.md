# Recommendation Chatbot Evaluation

This directory tracks the application-side data interface for persona-conditioned
recommendation chatbot evaluation.

The working scope is a normalized candidate catalog: every domain exposes a list
of recommendable items, and every item exposes enough text and metadata for a
recommendation bot to reason over. The evaluation environment and chatbot logic
should depend on the normalized catalog interface, not on each source dataset's
raw file format.

## Current Decision

Use the full normalized CMU Movie Summary Corpus for local movie-domain testing.
Keep the same catalog schema so later domains can plug in without changing the
recommendation bot interface.

## Quick Test Interface

After `.env.local`, the normalized movie catalog, and generated RecAI resources
are prepared locally, run the fixed smoke test with one command:

```sh
python applications/recommendation_chatbot_eval/scripts/recbot.py test
```

The smoke test runs a fixed two-turn movie recommendation conversation against
the catalog-backed InteRecAgent provider. It fails with a non-zero exit code if
the backend returns a retry response, a broken tool output, or a turn without
catalog item ids. Default output is compact; add `--show-json` for the full
`RecBotTurnResult` payload or `--verbose` for backend debug logs.

Start a manual command-line conversation with:

```sh
python applications/recommendation_chatbot_eval/scripts/recbot.py chat
```

Add `--show-json` to either command to inspect native actions, tool traces, and
recommended catalog item ids. The wrapper loads `.env.local`, sets the default
catalog-backed RecAI mode, and injects the app path, so callers do not need to
manually set `PYTHONPATH`.

Cold-start note: each new CLI process loads the full catalog resources and the
local dense `item_sim.npy`, so the first turn can take several minutes. Keep one
`chat` session open for manual multi-turn testing; later turns in the same
session are much faster because the agent remains in memory.

Default unit tests do not call the external RecAI backend:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval \
  python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

Full source datasets should not be committed to this repository. The repo should
contain only:

- dataset documentation and source manifests,
- schema definitions,
- adapters/loaders when implemented,
- unit tests with inline minimal records.

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

## RecBot Provider

The RecBot provider layer gives MatrAIx a normalized request/result contract for
external recommendation backends. For Microsoft RecAI/InteRecAgent, MatrAIx owns
the `RecBotRequest`, `RecBotTurnResult`, subprocess provider, JSON bridge, and
tests around that boundary. The default InteRecAgent provider now uses the
MatrAIx normalized catalog as the source of truth for the item universe, then
generates a RecAI-compatible resource directory for RecAI's native lookup,
filter, similarity, and mapping tools.

Personalized ranking is handled by a catalog-backed semantic profile ranker by
default because RecAI's native `RecModelTool` requires a UniRec checkpoint
trained against the same item ids. If a catalog-aligned checkpoint is available,
the provider can switch back to RecAI's native ranker with
`INTERECAGENT_RANKER_MODE=native`.

InteRecAgent native output is preserved inside the `RecBotTurnResult` envelope:
`native_action.raw` carries the backend's native `Final Answer` or
`Action ToolExecutor` text, while `trace` carries normalized inspection fields
such as raw tool plans and tool outputs when available. See
[INTERECAGENT_PROVIDER.md](INTERECAGENT_PROVIDER.md) for local setup,
environment variables, interactive chat, smoke testing, and the default unit
test command.

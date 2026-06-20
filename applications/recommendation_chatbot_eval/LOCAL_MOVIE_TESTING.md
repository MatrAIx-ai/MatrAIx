# Local Movie Testing Plan

The first local test source is the movie domain. This keeps the data small while
exercising the same catalog interface that later supports Amazon, WebShop, Yelp,
Google Local, and H&M.

## Source

Primary source: CMU Movie Summary Corpus.

Relevant raw files after extracting the corpus:

```text
MovieSummaries/
|-- movie.metadata.tsv
|-- plot_summaries.txt
|-- character.metadata.tsv
|-- name.clusters.txt
|-- tvtropes.clusters.txt
`-- README.txt
```

Use `movie.metadata.tsv` and `plot_summaries.txt` first. Join character metadata
later only if we need actor/character-aware recommendation scenarios.

## Local Paths

Raw data should be placed outside git-tracked files:

```text
data/raw/cmu_movie_summary/MovieSummaries/
```

The normalized local catalog should be generated to:

```text
data/normalized/recommendation_catalogs/cmu_movie_summary/items.jsonl
```

Generate the full local catalog from the official CMU files with:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval \
  python applications/recommendation_chatbot_eval/scripts/normalize_cmu_movie_summary.py
```

The full catalog is local-only and gitignored. In the current CMU corpus this
produces 42,207 recommendable movie items after joining plot summaries to movie
metadata.

## Normalization Shape

Each normalized movie item should follow
`schemas/catalog_item.schema.json`.

Example shape:

```json
{
  "item_id": "cmu:54166",
  "domain": "movie",
  "title": "Example Movie",
  "description": "Plot summary text.",
  "display_text": "Example Movie. Genres: Adventure, Action. Plot: ...",
  "categories": ["Adventure", "Action"],
  "metadata": {
    "release_date": "1981-06-12",
    "runtime_minutes": 115,
    "languages": ["English"],
    "countries": ["United States of America"]
  },
  "signals": {
    "box_office_revenue": 389925971
  },
  "domain_metadata": {
    "freebase_movie_id": "/m/0f4yh"
  },
  "source": {
    "dataset": "cmu_movie_summary_corpus",
    "license": "CC BY-SA",
    "original_id": "54166",
    "url": "https://www.cs.cmu.edu/~ark/personas/"
  }
}
```

## First Local Test Scenario

Use the full movie catalog and persona-conditioned prompts. The test should check
that the recommender can read a normalized item list and return candidate movies
that match stated or elicited preferences.

Initial base request:

```text
Can you recommend a movie for tonight?
```

Suggested persona variants:

- wants a thoughtful family drama, avoids horror and violence,
- wants a tense science-fiction thriller with mystery,
- wants a light romantic comedy set in a city,
- wants a documentary or realistic survival/adventure story.

Planned full local test behavior:

- The recommendation bot should ask at least one clarification question when the
  request is underspecified.
- Final recommendations should come from the provided movie catalog, not from
  open-world movie knowledge.
- Explanations should cite catalog metadata such as genre, tone, plot summary,
  runtime, or language.
- A future evaluator should extract and log which item ids were recommended.

## Implementation Boundary

The current InteRecAgent provider is catalog-backed by default. It converts the
normalized movie catalog into a RecAI-compatible resource directory, uses RecAI's
native lookup/filter/similarity/map tools, and replaces only the
checkpoint-dependent personalized ranking tool with a semantic profile ranker
unless `INTERECAGENT_RANKER_MODE=native` is explicitly set.

The RecAI similarity tool requires a dense `item_sim.npy` whose shape matches
the generated item ids. For full catalogs, this matrix must be generated
offline or provided in a complete generated resource directory. The bridge does
not use sampled catalogs or substitute similarity implementations.

Movie catalog evaluation should validate:

1. the normalized catalog item schema,
2. loading the full item list,
3. passing catalog items to a recommendation bot,
4. checking that final recommendations reference valid item ids.

## Simple Smoke Test

After setting up Microsoft RecAI/InteRecAgent, API credentials, the normalized
movie catalog, and generated RecAI resources, run this from the repository root:

```sh
python applications/recommendation_chatbot_eval/scripts/recbot.py test
```

This validates a fixed two-turn recommendation conversation through the MatrAIx
provider to the catalog-backed InteRecAgent movie backend. It requires the
external RecAI checkout and API credentials; default unit tests do not run this
real backend smoke test.

Expected compact output:

```text
Running MatrAIx RecBot test...
running turn 1/2
running turn 2/2
MatrAIx RecBot test completed
conversation_id=local_movie_test
turns=2
turn 1: planned_tools=...; executed_tools=...; recommended_ids=...
turn 2: planned_tools=...; executed_tools=...; recommended_ids=...
```

The command returns a non-zero exit code if any fixed turn returns a backend
retry response, a broken tool output, or no catalog item ids. Add `--show-json`
to print full `RecBotTurnResult` payloads, or `--verbose` to include backend
debug logs.

## Advanced JSON Smoke Test

The older provider-level smoke script remains available when a raw JSON
container is useful:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval "$INTERECAGENT_PYTHON" applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py
```

Its output is one JSON object with `conversation_id` and `turns`. Each entry in
`turns` is a `RecBotTurnResult` containing the assistant response, the preserved
InteRecAgent native action, and trace fields:

```json
{
  "conversation_id": "local_movie_smoke",
  "turns": [
    {
      "backend": "interecagent",
      "conversation_id": "local_movie_smoke",
      "turn_id": 1,
      "user_message": "Can you recommend a movie for tonight?",
      "assistant_message": "...",
      "native_action": {
        "raw": "...",
        "raw_tool_plan": []
      },
      "trace": {
        "raw_tool_plan": [],
        "raw_tool_outputs": null,
        "recommended_item_ids": ["cmu:54166"]
      }
    },
    {
      "backend": "interecagent",
      "conversation_id": "local_movie_smoke",
      "turn_id": 2,
      "user_message": "I want something tense and mysterious, but not horror.",
      "assistant_message": "...",
      "native_action": {
        "raw": "...",
        "raw_tool_plan": []
      },
      "trace": {
        "raw_tool_plan": [],
        "raw_tool_outputs": null,
        "recommended_item_ids": []
      }
    }
  ]
}
```

## Interactive Chat

For a manual multi-turn conversation, run:

```sh
python applications/recommendation_chatbot_eval/scripts/recbot.py chat
```

Add `--show-json` to inspect native actions, tool traces, and recommended item
ids for each turn. The wrapper loads `.env.local`, re-execs into
`INTERECAGENT_PYTHON` when set, and keeps one RecAI agent in memory so the full
catalog is initialized once per chat session. You can start broad and then add
preferences:

```text
I want to watch a movie.
Something tense and mysterious, but not horror.
I liked Aurora Station. Anything similar?
```

Each new CLI process must load the full catalog resources and dense
`item_sim.npy`, so the first turn can take several minutes. Later turns in the
same `chat` session are much faster.

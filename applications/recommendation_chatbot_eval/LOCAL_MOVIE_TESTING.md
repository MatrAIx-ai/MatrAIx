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

The repo fixture for quick smoke tests is:

```text
applications/recommendation_chatbot_eval/samples/cmu_movie_summary_tiny.jsonl
```

The fixture is synthetic but follows the CMU-derived normalized movie shape.

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

Use a small movie catalog and persona-conditioned prompts. The test should check
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

For v0, do not build full conversational evaluation yet. The current
InteRecAgent smoke test is only intended to validate provider-to-InteRecAgent
conversation flow and the native action/trace envelope. Automatic recommended
item id extraction and validation are future work; the v0 bridge returns
`recommended_item_ids: []`.

Future movie catalog evaluation should validate:

1. the normalized catalog item schema,
2. loading a small item list,
3. passing catalog items to a recommendation bot,
4. checking that final recommendations reference valid item ids.

## InteRecAgent Smoke Test

After setting up Microsoft RecAI/InteRecAgent and downloading the movie
resources, run this from the repository root:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval "$INTERECAGENT_PYTHON" applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py
```

This validates a persona-style user message through the MatrAIx provider to the
existing InteRecAgent movie backend. It requires the external RecAI checkout,
InteRecAgent resources, and API credentials; default unit tests do not run this
real backend smoke test.

Expected output is one JSON container object with `conversation_id` and `turns`.
Each entry in `turns` is a `RecBotTurnResult` containing the assistant response,
the preserved InteRecAgent native action, and trace fields:

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
        "recommended_item_ids": []
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

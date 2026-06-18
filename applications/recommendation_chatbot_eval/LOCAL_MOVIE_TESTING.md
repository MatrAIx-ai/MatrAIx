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

Expected behavior:

- The recommendation bot should ask at least one clarification question when the
  request is underspecified.
- Final recommendations should come from the provided movie catalog, not from
  open-world movie knowledge.
- Explanations should cite catalog metadata such as genre, tone, plot summary,
  runtime, or language.
- The local test should log which item ids were recommended.

## Implementation Boundary

For v0, do not build full conversational evaluation yet. The movie local test is
only intended to validate:

1. the normalized catalog item schema,
2. loading a small item list,
3. passing catalog items to a recommendation bot,
4. checking that final recommendations reference valid item ids.

# InteRecAgent Provider

MatrAIx calls Microsoft RecAI/InteRecAgent as an external recommendation
backend. The default provider uses RecAI's planner and native tool contract, but
the recommendable item universe comes from the MatrAIx normalized catalog.

## Ownership Boundary

MatrAIx owns the provider boundary:

- `RecBotRequest` input envelopes,
- `RecBotTurnResult` output envelopes,
- the subprocess provider,
- the JSON bridge into InteRecAgent,
- local unit tests for the provider, bridge, and native action contract.

InteRecAgent owns the agent behavior:

- conversational recommendation reasoning,
- native `Final Answer` and `Action ToolExecutor` output,
- native query, retrieval, similarity, and mapping tool execution.

MatrAIx owns the application-side recommendation data:

- the normalized item catalog,
- the generated RecAI resource directory,
- the default semantic personalized ranker used when no catalog-aligned RecAI
  checkpoint is available.

The provider preserves InteRecAgent native action output inside the
`RecBotTurnResult` envelope so evaluators can inspect both the normalized MatrAIx
response fields and the backend-native trace.

## External Setup

Clone RecAI and create the InteRecAgent environment:

```sh
git clone https://github.com/microsoft/RecAI.git
cd RecAI/InteRecAgent
conda create -n interecagent python=3.9
conda activate interecagent
pip install -r requirements.txt
```

The default MatrAIx catalog-backed mode does not require the ready-to-run RecAI
resource archives. Those archives are only needed if you explicitly run
`INTERECAGENT_RESOURCE_MODE=recai_resources`.

For native RecAI resources, download the ready-to-run InteRecAgent resources
linked from the RecAI README and place them under:

```text
RecAI/InteRecAgent/resources/movie
RecAI/InteRecAgent/resources/game
RecAI/InteRecAgent/resources/beauty_product
```

## Environment

Set the provider and default backend options in your shell:

```sh
export INTERECAGENT_ROOT="$HOME/RecAI/InteRecAgent"
export INTERECAGENT_PYTHON="$HOME/miniconda3/envs/interecagent/bin/python"
export INTERECAGENT_DOMAIN=movie
export INTERECAGENT_ENGINE=gpt-4o-mini
export INTERECAGENT_BOT_TYPE=chat
export INTERECAGENT_RESOURCE_MODE=matraix_catalog
export INTERECAGENT_RANKER_MODE=semantic_profile
export OPENAI_API_KEY="..."
```

`INTERECAGENT_CATALOG_PATH` is optional for the movie local test. When unset, it
defaults to the full normalized CMU catalog:

```text
data/normalized/recommendation_catalogs/cmu_movie_summary/items.jsonl
```

If the full local catalog has not been generated yet, the provider fails with a
setup error. Full catalog data is a hard requirement for local movie runs.

The generated RecAI-compatible files are written under:

```text
data/cache/recommendation_chatbot_eval/recai_resources/movie/
```

Use a full normalized movie catalog by setting:

```sh
export INTERECAGENT_CATALOG_PATH="$PWD/data/normalized/recommendation_catalogs/cmu_movie_summary/items.jsonl"
```

Generate that full catalog from the official CMU Movie Summary Corpus files:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval \
  python applications/recommendation_chatbot_eval/scripts/normalize_cmu_movie_summary.py
```

Use RecAI's original resources instead of MatrAIx catalog resources only when
you intentionally want that provider-native item universe:

```sh
export INTERECAGENT_RESOURCE_MODE=recai_resources
export INTERECAGENT_RANKER_MODE=native
```

Use a catalog-aligned RecAI/UniRec checkpoint only when the checkpoint was
trained for the same generated resource ids:

```sh
export INTERECAGENT_RANKER_MODE=native
export INTERECAGENT_MODEL_CKPT_FILE="/path/to/catalog-aligned/model.ckpt"
```

For Azure OpenAI-compatible deployments, set:

```sh
export OPENAI_API_TYPE=azure
export OPENAI_API_BASE="https://<resource>.openai.azure.com/"
export OPENAI_API_VERSION="<api-version>"
export OPENAI_API_KEY="..."
export AZURE_OPENAI_DEPLOYMENT="<deployment-name>"
export INTERECAGENT_ENGINE="$AZURE_OPENAI_DEPLOYMENT"
```

## Local Smoke Test

Run the movie smoke test from the repository root:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval "$INTERECAGENT_PYTHON" applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py
```

The smoke test sends a persona-style movie request through the MatrAIx
subprocess provider to the catalog-backed InteRecAgent movie backend. It prints
one `RecBotTurnResult` container JSON object with this shape:

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

Each turn contains `assistant_message`, `native_action.raw`, and `trace` fields.
`recommended_item_ids` is populated when the RecAI map tool output can be mapped
back to normalized catalog ids.

The smoke test requires a working RecAI checkout and API credentials. In default
catalog-backed mode it does not require downloaded RecAI resource archives.

## Interactive Chat

Run a multi-turn local chat loop:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval \
  python applications/recommendation_chatbot_eval/scripts/chat_interecagent_movie.py \
  --show-json
```

The chat script loads `.env.local`, re-execs into `INTERECAGENT_PYTHON` when
configured, and defaults to in-process execution so full-catalog RecAI
initialization happens once per chat session. Example inputs:

```text
I want to watch a movie.
Something tense and mysterious, but not horror.
I liked Aurora Station. Anything similar?
```

The script preserves chat history across turns and routes each turn through the
same `RecBotRequest` / provider / bridge path used by automated tests.

## Ranking Modes

`semantic_profile` is the default ranking mode for MatrAIx catalog-backed runs.
It mimics RecAI's native `RecModelTool` interface:

- input is a JSON ranking plan with `schema`, `prefer`, and `unwanted`,
- `prefer` / `unwanted` titles are fuzzy matched to catalog item ids,
- `popularity` ranking uses `visited_num`,
- `similarity` ranking uses the generated item similarity scores,
- `preference` ranking uses semantic similarity to liked items, current request
  text, popularity prior, and unwanted-item penalty.

This substitute keeps the candidate set under MatrAIx control without requiring
a UniRec checkpoint trained on the same catalog ids. If such a checkpoint exists,
use `INTERECAGENT_RANKER_MODE=native`.

The similarity stage uses RecAI's native `SimilarItemTool`, which loads a dense
`item_sim.npy` at startup. For a MatrAIx catalog, that file must be generated
offline with ids aligned to `item_info.parquet`; the bridge does not substitute
another similarity implementation.

RecAI's provided movie resources do not hit this as a startup problem because
the ready-to-run resource archive already includes a precomputed `item_sim.npy`
for its own item ids. The preprocessing notebooks build that matrix offline
from interaction data and save it as `float16`; the runtime tool only loads the
file and indexes into it. A new MatrAIx catalog must therefore provide its own
aligned matrix instead of reusing RecAI's original matrix.

## Default Tests

Default unit tests do not require RecAI, InteRecAgent resources, or API keys:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

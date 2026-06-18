# InteRecAgent Provider

MatrAIx calls Microsoft RecAI/InteRecAgent as an external recommendation
backend. It does not reimplement InteRecAgent planning, retrieval, ranking, tool
execution, or domain-specific recommendation resources.

## Ownership Boundary

MatrAIx owns the provider boundary:

- `RecBotRequest` input envelopes,
- `RecBotTurnResult` output envelopes,
- the subprocess provider,
- the JSON bridge into InteRecAgent,
- local unit tests for the provider, bridge, and native action contract.

InteRecAgent owns the recommendation behavior:

- conversational recommendation reasoning,
- native `Final Answer` and `Action ToolExecutor` output,
- query, retrieval, ranking, and mapping tools,
- domain resources and checkpoints.

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

Download the ready-to-run InteRecAgent resources linked from the RecAI README
and place them under:

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
export OPENAI_API_KEY="..."
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
subprocess provider to the existing InteRecAgent movie backend. It prints one
`RecBotTurnResult` container JSON object with this shape:

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
`recommended_item_ids` is currently reserved for future item-id extraction and
may be empty in the v0 bridge.
The smoke test requires RecAI, downloaded InteRecAgent resources, and API
credentials. It is not part of the default unit test path.

## Default Tests

Default unit tests do not require RecAI, InteRecAgent resources, or API keys:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

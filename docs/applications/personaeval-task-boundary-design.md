# PersonaEval Task Boundary Design

## Goal

PersonaEval evaluates interactive applications with simulated users that have
predefined persona attributes. A simulation runs a persona agent against an
application under test, records the interaction, and produces task-defined
feedback about whether the application satisfied the simulated user's need.

The core system should stay general across application types. It should know how
to list tasks, start an isolated run, move artifacts between the run and the UI,
and display the result. The concrete application behavior belongs to the task
package that defines that behavior.

## Ownership Model

The PersonaEval app owns the reusable control plane:

- the FastAPI backend used by the local UI
- the React UI
- shared run and artifact transport code
- persona catalog loading
- generic task discovery
- generic job state and run history

Each task package owns the task-specific execution contract:

- task instruction text
- interaction protocol, such as survey, chat, or browser interaction
- application sidecars and their dependencies
- application-specific data bundles
- artifact schema required by that task
- scoring function and questionnaire shape
- display metadata used by the UI

This boundary keeps RecAI, OpenBB, web application fixtures, and survey forms out
of the generic PersonaEval package. Those dependencies can change independently
inside their task directories.

## Runtime Flow

PersonaEval discovers a task from `application/tasks/<task_id>`. The task
manifest describes the application type, task protocol, sidecars, required
artifacts, and scorer entry point. PersonaEval starts the task environment in an
isolated sandbox and passes the task instruction to the persona agent. The task
environment mediates the interaction with the application under test and writes
artifacts to the agreed output directory. PersonaEval then loads the artifacts,
calls the task-owned scorer, and renders the transcript and scores in the UI.

The persona agent and the application under test do not share dependencies. The
task environment is the integration boundary between them. This is especially
important for chatbot tasks where the persona agent may use one model provider,
while the application chatbot and scorer may use different providers and local
packages.

## Target Layout

```text
applications/persona_eval/
  backend/                 # FastAPI app, generic run orchestration, UI API
  frontend/                # PersonaEval UI
  persona_eval/            # generic types, artifact helpers, persona loading
  data/personas/           # shared persona catalog

application/tasks/
  application_interface/   # shared manifests and protocol templates

  chatbot_chat_api/
    environment/
      chatbot_controller.py
      chatbot_api/
        harbor_api/        # chat API router and application adapters
        recbot/            # RecAI/InteRecAgent bridge
        recai/             # RecAI source checkout or submodule
        data/catalogs/     # chatbot catalog bundles
        scripts/           # chatbot resource setup and smoke scripts
    tests/

  survey_form/
    environment/
    tests/

  web-ecommerce-platform_product-discovery/
    environment/
    solution/
    tests/
```

The existing recommender and finance chatbots are both implementations of the
same chatbot task protocol. The UI can continue to switch between them through
the chatbot application selection. Survey and web tasks can be registered in the
same catalog before they are wired to the UI.

## Task Manifest Contract

Each task should expose a small manifest that PersonaEval can read without
importing task-specific application code:

```json
{
  "applicationType": "chatbot",
  "displayName": "Chatbot application",
  "protocol": "chat_api",
  "components": {
    "persona": "sandbox-provided",
    "application": "task-sidecar",
    "scorer": "task-owned"
  },
  "artifacts": [
    "transcript.json",
    "application_result.json",
    "user_feedback.json"
  ],
  "scorer": {
    "module": "task_scorer",
    "function": "score"
  }
}
```

The manifest is intentionally data-only. PersonaEval may show it in the UI and
use it to validate a run, but task-specific imports happen only inside the task
environment or the task scorer.

## Migration Plan

1. Add structure tests that require `applications/persona_eval` to be the
   canonical app root and require chatbot adapters to live under
   `application/tasks/chatbot_chat_api/environment/chatbot_api`.
2. Move the generic app from `applications/recommendation_chatbot_eval` to
   `applications/persona_eval`.
3. Move chatbot-specific sidecars, RecAI bridge code, resource scripts, RecAI
   checkout, and chatbot catalogs into the chatbot task environment.
4. Update import path helpers and local dev scripts so the backend can still run
   the chatbot applications from the UI.
5. Update Docker compose build contexts so Harbor builds chatbot sidecars from
   the task directory.
6. Keep survey and web registered at the task layer, without requiring UI wiring
   in this refactor.

## Validation

The refactor is acceptable when the existing chatbot UI can still start a
chatbot run end to end, backend tests pass from the new app root, chatbot task
tests pass from the task directory, and the frontend builds from
`applications/persona_eval/frontend`.

# PersonaEval Task Boundary Refactor Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move PersonaEval to a generic app root and move chatbot-specific
application code into the chatbot task environment while preserving existing
chatbot UI runs.

**Architecture:** PersonaEval remains the local control plane for persona
simulation, UI state, run history, and artifact display. Task packages own their
own application environments, task instructions, artifact expectations, and
scoring contracts.

**Tech Stack:** Python FastAPI backend, React/Vite frontend, Docker Compose task
environments, pytest, TypeScript build checks.

---

### Task 1: Lock The Target Boundary With Tests

**Files:**
- Create: `tests/unit/matraix/test_persona_eval_structure.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_persona_eval_core_and_chatbot_task_are_separated() -> None:
    app_root = REPO_ROOT / "applications" / "persona_eval"
    chatbot_api = (
        REPO_ROOT
        / "application"
        / "tasks"
        / "chatbot_chat_api"
        / "environment"
        / "chatbot_api"
    )

    assert (app_root / "backend").is_dir()
    assert (app_root / "frontend").is_dir()
    assert (app_root / "persona_eval").is_dir()
    assert not (app_root / "recbot").exists()
    assert not (app_root / "harbor_api").exists()
    assert (chatbot_api / "harbor_api").is_dir()
    assert (chatbot_api / "recbot").is_dir()
    assert (chatbot_api / "data" / "catalogs").is_dir()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/matraix/test_persona_eval_structure.py -q
```

Expected: fail because the canonical app root and chatbot task adapter path do
not exist yet.

### Task 2: Move Files To The New Boundaries

**Files:**
- Move tracked files from `applications/recommendation_chatbot_eval/` to
  `applications/persona_eval/`
- Move chatbot adapter files from `applications/persona_eval/harbor_api/` to
  `application/tasks/chatbot_chat_api/environment/chatbot_api/harbor_api/`
- Move RecAI bridge files from `applications/persona_eval/recbot/` to
  `application/tasks/chatbot_chat_api/environment/chatbot_api/recbot/`
- Move chatbot catalogs from `applications/persona_eval/data/catalogs/` to
  `application/tasks/chatbot_chat_api/environment/chatbot_api/data/catalogs/`
- Move chatbot resource scripts from `applications/persona_eval/scripts/` to
  `application/tasks/chatbot_chat_api/environment/chatbot_api/scripts/`

- [ ] **Step 1: Move tracked files only**

Use `git mv` or equivalent tracked-file moves. Leave local caches and other
untracked generated files out of the move.

- [ ] **Step 2: Move local untracked config if needed**

Move `.env.local` only as an untracked local file so existing local dev secrets
continue to load from the new app root.

### Task 3: Update Import And Build Paths

**Files:**
- Modify: `applications/persona_eval/backend/service/__init__.py`
- Modify: `applications/persona_eval/backend/run_dev.sh`
- Modify: `applications/persona_eval/backend/service/bundle_catalog.py`
- Modify: `application/tasks/chatbot_chat_api/environment/docker-compose.yaml`
- Modify: `application/tasks/recommender-agent_chat_api/environment/docker-compose.yaml`
- Modify: `application/tasks/chatbot_chat_api/environment/chatbot_api/harbor_api/Dockerfile`
- Modify: `application/tasks/chatbot_chat_api/environment/chatbot_api/harbor_api/finance.Dockerfile`

- [ ] **Step 1: Resolve the chatbot API source path from the repo root**

The backend service package should add
`application/tasks/chatbot_chat_api/environment/chatbot_api` to `sys.path` so
lazy `import recbot` works for the local UI.

- [ ] **Step 2: Update Docker contexts**

The chatbot Docker Compose file should build router, RecAI, finance, and OpenBB
sidecars from `application/tasks/chatbot_chat_api/environment/chatbot_api`.

- [ ] **Step 3: Keep compatibility where needed**

References to cache namespaces may keep existing directory names only when they
point to persisted local state. Source paths should use `applications/persona_eval`.

### Task 4: Validate Chatbot UI Compatibility

**Files:**
- No production file changes unless validation finds a regression.

- [ ] **Step 1: Run Python tests**

```bash
PYTHONPATH=src:applications/persona_eval:application/tasks/chatbot_chat_api/environment/chatbot_api \
  .venv/bin/python -m pytest \
  tests/unit/matraix/test_persona_eval_structure.py \
  applications/persona_eval/backend/tests \
  application/tasks/chatbot_chat_api/tests \
  -q
```

Survey and web task verifier files expect task-produced artifacts under
`/app/output`, so check their syntax locally and run them inside their task
environment when artifacts exist:

```bash
.venv/bin/python -m py_compile \
  application/tasks/survey_form/tests/test_state.py \
  application/tasks/web-ecommerce-platform_product-discovery/tests/test_state.py
```

- [ ] **Step 2: Build the frontend**

```bash
npm --prefix applications/persona_eval/frontend run build
```

- [ ] **Step 3: Start the local UI stack and run a browser check**

```bash
bash applications/persona_eval/backend/run_dev.sh
npm --prefix applications/persona_eval/frontend run dev
```

Open the Vite URL, start a chatbot persona evaluation, and confirm the UI shows
persona, chatbot, scorer, prompt metadata, transcript turns, and scores.

# Application tasks

Harbor tasks for **application product research**. Owned by the **Application team**.

The shared protocol index lives in
[`application_interface/`](application_interface/). It groups the current task
family into survey, chatbot, and web/computer-use application protocols without
moving existing Harbor task paths.

## Naming

- **`example-*`** — reference tasks in the repo (copy from these).
- **Your task** — `application/tasks/<your-task-name>/` (any folder name you choose).

## New task

Copy the closest `example-*` sibling (same interaction type), then edit files. See
[`skills/create-matraix-task/SKILL.md`](../../skills/create-matraix-task/SKILL.md) (Application track).

1. Add entry in [`src/matraix/task_catalog.py`](../../src/matraix/task_catalog.py)
2. `cp -R application/tasks/example-survey_product-feedback application/tasks/<your-task-name>`
3. `[task].name` → `matraix/application-{slug}`; `[metadata]` matches catalog
4. Smoke: `-p application/tasks/<your-task-name>` with `persona/datasets/bench-dev-2000/persona_0042.yaml`

## Metadata

| Field | Meaning |
|-------|---------|
| **type** | Interaction form (`survey`, `chat`, `web`, `desktop`, `mobile`, …) |
| **domain** | Vertical: `software` · `finance` · `healthcare` · `commerce-retail` |
| **tags** | Task-specific (see `src/matraix/task_catalog.py`) |

## Current application protocols

| Protocol | Canonical runnable task |
| --- | --- |
| Survey | `survey_form` |
| Chatbot | `chatbot_chat_api` |
| Web / computer-use | `web-ecommerce-platform_product-discovery` |

See [../../docs/applications/task-guide.md](../../docs/applications/task-guide.md) and [../../docs/applications/](../../docs/applications/).

Persona bench: [`persona/tasks/`](../../persona/tasks/) — same example names, independent tasks.

## Docker (`persona-claude-code` tasks)

[`_docker/install-claude-code.sh`](_docker/install-claude-code.sh) pre-bakes Claude Code + `uv` into the image. Copy it into `environment/` when authoring survey or chat tasks (see `example-survey_product-feedback` / `example-chat-*`). Web and computer-use tasks use different base images and do not use this script.

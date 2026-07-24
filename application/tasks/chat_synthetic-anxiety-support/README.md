# Anxiety Support Chatbot

MatrAIx chatbot task for a synthetic anxiety support assistant.

Product under test: Qwen-powered anxiety support sidecar (OpenAI and Anthropic
optional). The persona agent acts as a simulated user, has a multi-turn
conversation, and saves transcript plus self-report artifacts.

Harbor runtime:

- Persona agent: `environment/task-environments/application/shared-chat-persona`
- Local endpoint: `environment/task-environments/application/chatbot-api-sidecar_anxiety`
  (`anxiety-chatbot`, host port **8907**)

## Sidecar smoke

```bash
cd environment/task-environments/application/chatbot-api-sidecar_anxiety
export QWEN_API_KEY=your-key
docker compose -f standalone-compose.yaml up --build
curl http://127.0.0.1:8907/health
```

## Harbor smoke

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/chat_synthetic-anxiety-support \
  --execution-mode auto \
  --persona-ids 0042

export QWEN_API_KEY=your-key
export CHATBOT_UPSTREAM_ANXIETY=http://127.0.0.1:8907
export ANTHROPIC_API_KEY=sk-ant-...
uv run harbor run -c configs/jobs/application-task-job-recipe/chat-synthetic-anxiety-support-n1.yaml
```

## Persona pool

If Playground sampling is thin for the task filters, generate a local pool:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --strategy application/tasks/chat_synthetic-anxiety-support/persona_strategy.json
```

## Expected artifacts

- `/app/output/transcript.json`
- `/app/output/user_feedback.json`

See `input/protocol.md` for the HTTP contract and `input/self_report_schema.yaml`
for the feedback schema.

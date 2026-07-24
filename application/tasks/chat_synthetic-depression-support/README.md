# Depression Support Chatbot

MatrAIx chatbot task for a synthetic depression support assistant with SAMHSA
safe-messaging guardrails.

Product under test: multi-LLM depression support sidecar (Qwen default; OpenAI
and Anthropic optional). The persona agent acts as a simulated user, has a
multi-turn conversation, and saves transcript plus self-report artifacts.

Harbor runtime:

- Persona agent: `environment/task-environments/application/shared-chat-persona`
- Local endpoint: `environment/task-environments/application/chatbot-api-sidecar_depression`
  (`depression-chatbot`, host port **8906**)

## Sidecar smoke

```bash
cd environment/task-environments/application/chatbot-api-sidecar_depression
export QWEN_API_KEY=your-key
docker compose -f standalone-compose.yaml up --build
curl http://127.0.0.1:8906/health
```

## Harbor smoke

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/chat_synthetic-depression-support \
  --execution-mode auto \
  --persona-ids 0042

export QWEN_API_KEY=your-key
export CHATBOT_UPSTREAM_DEPRESSION=http://127.0.0.1:8906
export ANTHROPIC_API_KEY=sk-ant-...
uv run harbor run -c configs/jobs/application-task-job-recipe/chat-synthetic-depression-support-n1.yaml
```

## Persona pool

If Playground sampling is thin for the task filters, generate a local pool:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --strategy application/tasks/chat_synthetic-depression-support/persona_strategy.json
```

## Expected artifacts

- `/app/output/transcript.json`
- `/app/output/user_feedback.json`

See `input/protocol.md` for the HTTP contract and `input/self_report_schema.yaml`
for the feedback schema.

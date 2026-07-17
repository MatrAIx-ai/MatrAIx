# chatbot-api-sidecar_anxiety

Local HTTP sidecar for the synthetic anxiety support chatbot.

- `anxiety-chatbot` — MatrAIx adapter (`/health`, `/ready`, `/v1/session`,
  `/v1/messages`, `/v1/conversation`, `/v1/recommendations`) backed by **Qwen
  by default**, with optional OpenAI or Anthropic. Structured fields are exposed
  as `crisisEscalationTriggered` and `copingStrategySuggested` (task
  `structuredExposure` selectors).

Persona agent runtime: `application/shared-chat-persona`.
Task: `application/tasks/chat_synthetic-anxiety-support`.

Requires an LLM API key for real agent turns (`/ready` checks for one).

## Default: Qwen

Compose defaults to `ANXIETY_AGENT_PROVIDER=qwen` and `ANXIETY_AGENT_MODEL=qwen-plus`.

```bash
cd environment/task-environments/application/chatbot-api-sidecar_anxiety
export QWEN_API_KEY=your-key
docker compose -f standalone-compose.yaml up --build
curl http://127.0.0.1:8907/health
```

For international DashScope keys (`sk-ws-*`):

```bash
export QWEN_API_BASE=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

## Other providers (optional)

| Provider | Env | Default model |
|----------|-----|---------------|
| OpenAI | `ANXIETY_AGENT_PROVIDER=openai` + `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `ANXIETY_AGENT_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| Auto | `ANXIETY_AGENT_PROVIDER=auto` | first key: OpenAI → Anthropic → Qwen |

## Local dev (without Harbor `main`)

Harbor's `docker-compose.yaml` includes a placeholder `main` service. For local
sidecar-only testing, use `standalone-compose.yaml`.

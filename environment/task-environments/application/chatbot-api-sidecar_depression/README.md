# chatbot-api-sidecar_depression

Local HTTP sidecar for the synthetic depression support chatbot.

- `depression-chatbot` — MatrAIx adapter (`/health`, `/ready`, `/v1/session`,
  `/v1/messages`, `/v1/conversation`, `/v1/recommendations`) backed by **Qwen
  by default**, with optional OpenAI or Anthropic. Structured fields are exposed
  as `crisisEscalationTriggered`, `phq9DomainsExplored`, and
  `safeMsgComplianceViolation` (task `structuredExposure` selectors).

Persona agent runtime: `application/shared-chat-persona`.
Task: `application/tasks/chat_synthetic-depression-support`.

Requires an LLM API key for real agent turns (`/ready` checks for one).

## Default: Qwen

Compose defaults to `DEPRESSION_AGENT_PROVIDER=qwen` and `DEPRESSION_AGENT_MODEL=qwen-plus`.

```bash
cd environment/task-environments/application/chatbot-api-sidecar_depression
export QWEN_API_KEY=your-key
docker compose -f standalone-compose.yaml up --build
curl http://127.0.0.1:8906/health
```

For international DashScope keys (`sk-ws-*`):

```bash
export QWEN_API_BASE=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

## Other providers (optional)

| Provider | Env | Default model |
|----------|-----|---------------|
| OpenAI | `DEPRESSION_AGENT_PROVIDER=openai` + `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `DEPRESSION_AGENT_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| Auto | `DEPRESSION_AGENT_PROVIDER=auto` | first key: OpenAI → Anthropic → Qwen |

## Local dev (without Harbor `main`)

Harbor's `docker-compose.yaml` includes a placeholder `main` service. For local
sidecar-only testing, use `standalone-compose.yaml`.

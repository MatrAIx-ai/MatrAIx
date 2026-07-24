# Owly support chat (product return)

PersonaBench **chatbot** task against [Hesper-Labs/owly](https://github.com/Hesper-Labs/owly),
an open-source AI customer-support system, hosted by the `shared-chat-api-owly`
sidecar stack. The persona contacts support about returning a two-week-old
purchase (order **58214**) and pushes for a clear return-and-refund path.

- Chat API: `http://owly-api:3000` (Owly's native `POST /api/chat`)
- Artifacts: `transcript.json`, `user_feedback.json` under `/app/output`

The scenario is grounded in Owly's seeded knowledge base: a 30-day return
policy for unused products in original packaging and refunds within 5–10
business days. That gives the debrief a stable correctness anchor for what a
"good" support answer looks like.

See [Application Tasks](../README.md) for contribution guidance.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (compose stack: owly-api + owly-db) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
OPENAI_API_KEY=sk-... uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/owly-support_chat_api
```

Notes:

- **Requires `OPENAI_API_KEY`** in the host environment — Owly's reply engine
  is LLM-backed (the sidecar passes the key through).
- Smoke the sidecar before a batch run: `curl -s http://owly-api:3000/api/health`
  and one `POST /api/chat {"message": "What is your return policy?", "channel": "api"}`
  exchange; the reply should quote the 30-day policy from the seeded knowledge
  base. If it answers generically, the database seed did not run — see
  `environment/task-environments/application/shared-chat-api-owly/README.md`.

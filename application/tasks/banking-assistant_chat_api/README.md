# Banking assistant chat (Rasa financial-demo)

PersonaBench **chatbot** task against the open-source
[RasaHQ/financial-demo](https://github.com/RasaHQ/financial-demo) retail-banking
assistant, hosted by the `shared-chat-api-rasa-banking` sidecar stack. The
persona pursues one everyday banking errand (balance, spending history,
transfer, credit card payment, or transfer charges) over a multi-turn chat.

- Chat API: `http://banking-api:8000` (adapter in front of Rasa's REST channel)
- Artifacts: `transcript.json`, `user_feedback.json` under `/app/output`

The bot is a deterministic Rasa 3.1 NLU/dialogue stack — no LLM API key is
required on the application side, which makes this task a good reliability
baseline (repeat trials for Tau-style `pass^k`).

See [Application Tasks](../README.md) for contribution guidance.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (compose stack: banking-api + rasa + rasa-actions + duckling) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/banking-assistant_chat_api
```

Notes:

- The first environment build is slow: `rasa train` runs inside the image
  build (several minutes; `build_timeout_sec = 1800`).
- Smoke the sidecar directly before a batch run:
  `curl -s http://banking-api:8000/health` and one
  `POST /v1/messages {"message": "what's my account balance?"}` exchange.

# Rasa Account Recovery Support Chatbot

PersonaBench application task for a real chatbot sidecar backed by the
open-source Rasa framework.

The task asks a persona to recover access to a fictional account while deciding
how much personal information to share. The environment builds a local Rasa
project from
`environment/task-environments/application/rasa-account-recovery_support-chatbot/rasa-bot/`
and exposes the standard Rasa REST webhook at
`http://rasa-account-recovery:5005/webhooks/rest/webhook`.

Source framework: https://github.com/RasaHQ/rasa.

## Contract

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/webhooks/rest/webhook` | Send one user message and receive Rasa bot replies |
| `GET` | `/status` | Rasa server status when `--enable-api` is active |

The REST webhook accepts:

```json
{"sender": "persona-0042", "message": "I cannot access my account."}
```

and returns a list of bot messages:

```json
[{"recipient_id": "persona-0042", "text": "I can help with account recovery..."}]
```

## Expected Artifacts

The persona agent writes:

- `/app/output/transcript.json`
- `/app/output/account_recovery_result.json`

The verifier checks multi-turn coverage, Rasa source attribution, metric shape,
persona self-report fields, and privacy-sensitive outcome metadata.

## Suggested Setup

| Field | Value |
|---|---|
| Agent | `persona-claude-code` |
| Environment | `docker` |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/rasa-account-recovery_support-chatbot
```

This task intentionally stays small: it proves the real-chatbot-sidecar pattern
without adding credentials, live customer data, or a production support tenant.

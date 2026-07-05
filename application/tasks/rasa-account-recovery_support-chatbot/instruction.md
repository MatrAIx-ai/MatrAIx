# Rasa account recovery support chat

You are a customer trying to recover access to a fictional account. Act
according to your assigned persona.

Read `/app/input/account_context.md` for the seeded account scenario. Do not use
real credentials, real email addresses, real phone numbers, government IDs, or
payment details.

The support chatbot is a Rasa sidecar named `rasa-account-recovery`, reachable
from this container at:

`http://rasa-account-recovery:5005/webhooks/rest/webhook`

Use `curl` or a short script to have a real multi-turn conversation with the
chatbot.

## Endpoint

| Method | Path | Body | Response |
|---|---|---|---|
| `POST` | `/webhooks/rest/webhook` | `{"sender": "<conversation id>", "message": "<your text>"}` | `[{"recipient_id": "...", "text": "..."}]` |

Use one stable sender id such as `persona-0042` for the whole conversation.

## Required Work

1. Have at least three user turns and three assistant turns.
2. Ask for account recovery help and respond naturally as your persona would.
3. Notice whether the bot asks for unnecessary sensitive information.
4. Decide whether the recovery path is clear enough to continue.
5. Save the exact conversation you observed to `/app/output/transcript.json`.
6. Save your final task result to `/app/output/account_recovery_result.json`.

## Output Schemas

`/app/output/transcript.json`:

```json
{
  "conversation_id": "persona-0042",
  "sidecar": "rasa-account-recovery",
  "endpoint": "http://rasa-account-recovery:5005/webhooks/rest/webhook",
  "messages": [
    {"role": "user", "content": "<string>"},
    {"role": "assistant", "content": "<string>"}
  ]
}
```

`/app/output/account_recovery_result.json`:

```json
{
  "conversation_id": "persona-0042",
  "source_reference": {
    "repository": "https://github.com/RasaHQ/rasa",
    "runtime": "rasa/rasa:3.6.21-full",
    "endpoint": "http://rasa-account-recovery:5005/webhooks/rest/webhook"
  },
  "application_result": {
    "outcome_class": "recovery_options_explained",
    "recovery_path": "email verification and support escalation",
    "asked_for_sensitive_data": false,
    "requested_personal_data": ["account email alias"]
  },
  "persona_self_report": {
    "trust_rating": 7,
    "frustration_rating": 4,
    "privacy_comfort": "medium",
    "reason": "<string>"
  },
  "metric_summary": {
    "numeric": {
      "turns_to_resolution": 3,
      "trust_rating": 7,
      "frustration_rating": 4
    },
    "categorical": {
      "outcome_class": "recovery_options_explained",
      "privacy_comfort": "medium"
    },
    "textual": {
      "main_friction": "<string>",
      "persona_rationale": "<string>"
    }
  }
}
```

Allowed `outcome_class` values are `recovery_options_explained`, `escalated`,
`blocked`, and `unclear`. Keep JSON valid and do not invent claims about the
real Rasa project beyond the sidecar interaction you performed.

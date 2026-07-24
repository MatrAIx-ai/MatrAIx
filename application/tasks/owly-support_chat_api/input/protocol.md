# Chat API protocol

The support agent is available through a REST API sidecar named `owly-api`,
reachable from this container at `http://owly-api:3000`. Use `curl` or a short
script to have a real multi-turn conversation with support.

Open with your situation the way a real customer would, then answer follow-up
questions, provide your order number when asked, and continue until you can
judge whether support gave you a usable return-and-refund path.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/api/health` | - | health status |
| `POST` | `/api/chat` | `{"message": "<your message>", "conversationId": "<optional>", "channel": "api"}` | `{"conversationId": "...", "response": "..."}` |

Omit `conversationId` on your first message; the API creates a conversation
and returns its id. Reuse the returned `conversationId` on every following
message so the agent keeps your conversation context.

## Required work

1. Have at least three user turns and three assistant turns.
2. Pursue the return-and-refund goal described in `context.md`.
3. Continue until you have a clear resolution path or can judge that support
   could not provide one.

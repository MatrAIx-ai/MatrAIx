# Chat API protocol

The banking assistant is available through a REST API sidecar named
`banking-api`, reachable from this container at `http://banking-api:8000`.
Use `curl` or a short script to have a real multi-turn conversation with the
assistant.

Based on your persona, decide what banking errand you realistically have, what
details matter to you, and how cautious you are about confirming actions. Do
not reveal everything at once. Interact naturally, answer follow-up questions,
respond to confirmation prompts, and continue until you can judge whether the
assistant handled your errand.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/health` | - | `{"status": "ok"}` |
| `POST` | `/v1/messages` | `{"sessionId": "...", "message": "<your message>"}` | `{"sessionId": "...", "reply": "..."}` |
| `GET` | `/v1/conversation?sessionId=...` | - | `{"messages": [...]}` |

You may omit `sessionId` on the first `/v1/messages` call; the API will create
a session automatically and return its id. Reuse the returned `sessionId` on
every following message so the assistant keeps your conversation state.

When a reply contains an `Options:` line, those are the assistant's suggested
answers — reply with the option text (or a natural phrasing of it).

## Required work

1. Have at least three user turns and three assistant turns.
2. Pursue one concrete banking errand consistent with your persona and the
   demo account profile in `context.md`.
3. Continue until the errand is completed, refused, or clearly stuck, so you
   can judge the experience.

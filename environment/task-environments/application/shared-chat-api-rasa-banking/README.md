# shared-chat-api-rasa-banking

Chat sidecar stack that hosts the [RasaHQ/financial-demo](https://github.com/RasaHQ/financial-demo)
retail-banking assistant behind the PersonaBench chat API contract.

Services (see `docker-compose.yaml`):

| Service | Purpose |
|---|---|
| `banking-api` | Adapter exposing `POST /v1/messages` / `GET /health`, forwards to Rasa's REST channel and joins multi-part replies |
| `rasa` | Rasa 3.1.0 server; the model is trained at image build (`rasa train`) |
| `rasa-actions` | Upstream action server (financial-demo root Dockerfile, rasa-sdk 3.1.0, port 5055) |
| `duckling` | Entity extraction for amounts, dates, numbers |

Notes:

- Upstream is pinned to commit `7627cebe` (last main commit) in both the
  `rasa/Dockerfile` tarball URL and the `rasa-actions` git build context.
- `rasa train` runs at image build, so the first build is slow (TensorFlow
  training, several minutes) and needs network. Use a generous
  `build_timeout_sec` (the task sets 1800).
- No LLM API key is needed: the bot is a deterministic Rasa NLU/dialogue
  stack, which makes it a good reliability baseline (Tau-style `pass^k`).
- The demo profile has fictional credit cards (`emblem`, `justice bank`,
  `credit all`, `iron bank`) and vendors (`Starbucks`, `Amazon`, `Target`).
  Task prose should ground the persona in those, not real accounts.

Runtime assets only — task-specific prose belongs in the task folder
(`application/tasks/banking-assistant_chat_api`).

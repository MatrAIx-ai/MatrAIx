# shared-chat-api-owly

Chat sidecar stack that hosts [Hesper-Labs/owly](https://github.com/Hesper-Labs/owly),
an open-source AI customer-support system, behind its native chat API.

Services (see `docker-compose.yaml`):

| Service | Purpose |
|---|---|
| `owly-api` | Owly Next.js app (built from the upstream Dockerfile, pinned to commit `430c646e`); chat at `POST /api/chat`, health at `GET /api/health` |
| `owly-db` | PostgreSQL 16 backing store |

Chat contract (native, no adapter needed):

```
POST /api/chat  {"message": "...", "conversationId": "<optional>", "channel": "api"}
→ {"conversationId": "...", "response": "..."}
```

Notes:

- **Requires `OPENAI_API_KEY`** in the host environment — Owly's reply engine
  is LLM-backed. Without it the health check passes but chat replies fail.
- Startup runs `prisma migrate deploy` and then attempts `prisma db seed`,
  which loads the demo knowledge base (business hours, contact info, product
  overview, 30-day return policy, 5–10 day refund policy) plus departments.
  If seeding is unavailable in the runtime image the stack still boots;
  verify at smoke time that policy questions get grounded answers.
- Secrets in the compose file are local-only placeholders for the sandboxed
  trial network, not production credentials.

Runtime assets only — task-specific prose belongs in the task folder
(`application/tasks/owly-support_chat_api`).


## Smoke-test status (2026-07-20)

Local Docker smoke on Apple Silicon surfaced cascading build/runtime couplings in
upstream Owly. **The `build.context: <git-url>` approach in the original
docker-compose does NOT build.** A vendored, pinned Dockerfile under
[`owly-app/`](owly-app/Dockerfile) fixes the build:

1. **Build-time secrets** — `next build` statically analyzes routes that import
   the config module, which hard-requires `JWT_SECRET`. The Dockerfile sets
   dummy build-time `JWT_SECRET`/`NEXTAUTH_SECRET`/`WEBHOOK_SECRET`; the real
   values still come from compose `environment:` at runtime.
2. **Prerender hits the DB** — dashboard pages/layouts are async server
   components that run Prisma queries; Next.js executes them during static
   prerender at build time, when no database exists. An idempotent build-time
   codemod prepends `export const dynamic = "force-dynamic"` to server
   `page.tsx`/`layout.tsx`/`route.ts` that don't already declare it, so those
   routes are not prerendered.

With both fixes the image **builds cleanly**. To use it, point compose at the
vendored Dockerfile instead of the git context:

```yaml
  owly-api:
    build:
      context: ./owly-app
```

### Remaining blockers (not yet resolved)

- **Runtime DB migration fails.** The container's `prisma migrate deploy` exits
  with *"The datasource.url property is required in your Prisma config file"* —
  the pinned lockfile resolves Prisma 7.6.0, whose `prisma.config.ts` handling
  no longer picks up `DATABASE_URL` for `migrate deploy` the old way. Needs the
  datasource URL wired into `prisma.config.ts` (or a Prisma pin/downgrade).
- **`OPENAI_API_KEY` required at runtime** for actual chat replies; health and
  seed can run without it, but the `/api/chat` reply path cannot be validated
  without a key.

Given three separate integration issues plus the LLM-key dependency, Owly is a
high-friction SUT. If a lower-friction support chatbot is acceptable, a
deterministic Rasa assistant (e.g. RasaHQ/helpdesk-assistant) avoids the
build-coupling and the API-key requirement.

### Update — build + boot now validated (2026-07-20, later)

With the vendored Dockerfile the stack now **builds, boots, migrates, and seeds**:

- `COPY --from=builder /app/prisma.config.ts ./` was the runtime fix — Owly's
  `schema.prisma` datasource has no `url`; it lives only in the root
  `prisma.config.ts`, which upstream's Dockerfile never copied. With it,
  `prisma migrate deploy` applies all 7 migrations and the DB connects.
- Seed runs via `npx tsx prisma/seed.ts` in the CMD (NOT `prisma db seed` —
  Prisma 7 ignores package.json `prisma.seed` and reports "no seed configured").
  Verified: 5 knowledge-base rows load, including Return Policy and Refund Policy.
- `/api/health` → `{"status":"ok","services":{"database":"connected","openai":"not_configured"}}`.

### Decisive blocker for the persona task: API authentication

`POST /api/chat` is NOT open. `src/middleware.ts` requires **either** a JWT
cookie (`owly-token`) **or** an `x-api-key` header on every `/api/*` route
except a small allowlist (`/api/health`, `/api/auth`, `/api/openapi.json`,
`/login`, `/setup`). With no credential, chat returns
`401 {"code":"UNAUTHORIZED"}` before any LLM call.

So the task's `input/protocol.md` and `input/chatbot.yaml` (which assume an
unauthenticated `POST /api/chat`) are WRONG as written. To make the persona
task work, the environment must:

1. **Provision an API key at setup** — log in as the seeded admin
   (`admin` / `admin123`) via `POST /api/auth`, then create a key via
   `POST /api/admin/api-keys`, and capture it.
2. **Send that key on every persona request** as an `x-api-key` header. This
   requires the PersonaBench chatbot `sidecar_http` transport to support a
   static auth header (UNVERIFIED — the transport source could not be read this
   session due to a macOS permission issue; confirm before relying on Owly).
3. Supply `OPENAI_API_KEY` at runtime for actual replies.

Net: Owly needs build patching (done), a runtime seed fix (done), API-key
provisioning + header-auth wiring into the transport (NOT done, and possibly
needs harness support), plus an OpenAI key. A deterministic Rasa support SUT
(e.g. RasaHQ/helpdesk-assistant) avoids all four.

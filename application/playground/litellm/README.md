# LiteLLM proxy — global LLM rate limiter (Plan B)

A single proxy process that funnels every OpenAI-family LLM call (Harbor
agents/verifiers, persona / user-sim, and batch reporting) through one shared
`rpm`/`tpm` budget. This lets you raise `parallelism` (`n_concurrent_trials`)
toward your machine's limits without triggering provider 429 storms — the proxy
queues/backs off bursts instead of failing trials.

## Why this exists

Harbor/Playground has no application-level LLM throttle — only a 3-attempt retry
in `environment/runtime/harbor/llms/lite_llm.py`. Without a global limiter, high
concurrency (especially survey/chat, which fork one subprocess per trial) burns
straight through provider rate limits.

Because all traffic goes through this one process, its in-memory rpm/tpm
accounting is exact — no Redis needed for local single-host runs.

## Which call paths are covered

| Path | Client | Routed via proxy? |
| --- | --- | --- |
| Harbor agents / verifiers | `litellm.acompletion` (reads `OPENAI_API_BASE`/`OPENAI_BASE_URL`) | Yes |
| Persona / user-sim | `OpenAIChatClient` / `OpenAIToolStepClient` (openai SDK, reads `OPENAI_BASE_URL`) | Yes |
| Batch reporting | `OpenAIChatClient` (`job_aggregation.py`) | Yes |
| Persona model = `anthropic/...` (proxy ON) | routed via proxy's OpenAI-compatible endpoint | Yes |
| Persona model = `anthropic/...` (proxy OFF) | `AnthropicJSONClient` / `AnthropicToolStepClient` (direct `api.anthropic.com`) | N/A (proxy off) |

Claude personas: when proxy mode is on (`OPENAI_BASE_URL` set), the persona
JSON and tool-calling clients auto-route Claude through the proxy's
OpenAI-compatible endpoint (`config.yaml` `anthropic/*` entry) using the same
base URL + master key as the OpenAI paths — LiteLLM translates the format. No
Anthropic-specific base URL or key juggling needed. When the proxy is off they
fall back to calling `api.anthropic.com` directly (unchanged behavior).

## Setup

No install needed — the launch script runs `uv run litellm`, using the project
`.venv` where `litellm` and its proxy extras are already available.

## Run

1. Start the proxy (reads real keys from `application/playground/.env.local`):

```bash
./application/playground/litellm/run_proxy.sh
# or a custom port:  PORT=4100 ./application/playground/litellm/run_proxy.sh
```

2. Point the backend / job runners at it by exporting these before launching the
   Playground backend (or uncomment them in `.env.local`):

```bash
export OPENAI_BASE_URL=http://127.0.0.1:4000/v1
export OPENAI_API_BASE=http://127.0.0.1:4000/v1
# OPENAI_API_KEY stays your real key — the proxy reuses it as its master key,
# so callers need no key change.
```

These env vars are inherited by the survey/chat trial subprocesses, so the
limiter covers them too.

3. Set your real limits in `config.yaml` (`rpm`/`tpm` per model) from
   platform.openai.com → Settings → Limits. For GPT-5.5 also set values that
   respect the separate long-context limit.

4. Now raise parallelism toward your machine's ceiling (the proxy absorbs
   bursts). Rough local guidance with the proxy in place:
   - survey: 25–35
   - chat: 12–20 (8–12 for heavy medical/finance sidecars)
   - web: 3–6 (docker-bound; not TPM-bound)

## Verify it's working

```bash
curl -s http://127.0.0.1:4000/health/readiness   # proxy up

curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

The proxy logs each request; watch for `429`/cooldown lines when you push
concurrency to confirm throttling engages instead of failing trials.

## Turning it off

Stop the proxy process and unset `OPENAI_BASE_URL` / `OPENAI_API_BASE`. Calls go
straight to the providers again.

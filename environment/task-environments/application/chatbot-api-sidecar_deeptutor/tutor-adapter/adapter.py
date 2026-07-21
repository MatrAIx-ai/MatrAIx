"""MatrAIx /v1/messages adapter for a DeepTutor partner.

Bridges the MatrAIx chatbot sidecar contract (POST /v1/messages ->
{sessionId, reply, turn}) to DeepTutor's partner chat HTTP API
(POST /api/v1/partners/{partner_id}/chat, session-persistent).

On startup (lazily, on the first request) the adapter:
  1. waits for the DeepTutor backend to come up,
  2. seeds the model catalog with one LLM profile from env if empty,
  3. ensures a tutor partner exists and is started.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tutor-adapter")

DEEPTUTOR_BASE = os.environ.get("DEEPTUTOR_BASE_URL", "http://deeptutor:8001").rstrip("/")
LLM_BINDING = os.environ.get("DEEPTUTOR_LLM_BINDING", "openai")
LLM_MODEL = os.environ.get("DEEPTUTOR_LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.environ.get("DEEPTUTOR_LLM_BASE_URL", "")
LLM_API_KEY = (
    os.environ.get("DEEPTUTOR_LLM_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY")
    or ""
)
PARTNER_NAME = os.environ.get("DEEPTUTOR_PARTNER_NAME", "MatrAIx Tutor")
PARTNER_DESCRIPTION = os.environ.get(
    "DEEPTUTOR_PARTNER_DESCRIPTION",
    "A patient, adaptive one-on-one tutor. Understand the learner's background "
    "and goal first, then explain step by step at the right level, checking "
    "understanding as you go.",
)
STARTUP_TIMEOUT_SECONDS = float(os.environ.get("DEEPTUTOR_STARTUP_TIMEOUT", "180"))

app = FastAPI()
_bootstrap_lock = asyncio.Lock()
_bootstrapped = False
_partner_id: str | None = None
_turns: dict[str, int] = {}


class MessageRequest(BaseModel):
    sessionId: str | None = None
    message: str
    title: str | None = None
    botType: str | None = None
    applicationContext: str | None = None
    applicationId: str | None = None


async def _wait_for_backend(client: httpx.AsyncClient) -> None:
    deadline = asyncio.get_event_loop().time() + STARTUP_TIMEOUT_SECONDS
    while True:
        try:
            resp = await client.get(f"{DEEPTUTOR_BASE}/api/v1/partners")
            if resp.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        if asyncio.get_event_loop().time() > deadline:
            raise RuntimeError("DeepTutor backend did not come up in time")
        await asyncio.sleep(2)


async def _seed_catalog(client: httpx.AsyncClient) -> None:
    resp = await client.get(f"{DEEPTUTOR_BASE}/api/v1/settings/catalog")
    resp.raise_for_status()
    catalog = resp.json().get("catalog", resp.json())
    llm = catalog.get("services", {}).get("llm", {})
    if llm.get("profiles"):
        log.info("model catalog already has an LLM profile; leaving it as-is")
        return
    if not LLM_API_KEY:
        log.warning("no LLM API key in env; tutor replies will fail until one is configured")
    profile_id = f"llm-profile-{uuid.uuid4().hex[:8]}"
    model_id = f"llm-model-{uuid.uuid4().hex[:8]}"
    llm["profiles"] = [
        {
            "id": profile_id,
            "name": "MatrAIx seeded profile",
            "binding": LLM_BINDING,
            "base_url": LLM_BASE_URL,
            "api_key": LLM_API_KEY,
            "api_version": "",
            "extra_headers": {},
            "models": [{"id": model_id, "name": LLM_MODEL, "model": LLM_MODEL}],
        }
    ]
    llm["active_profile_id"] = profile_id
    llm["active_model_id"] = model_id
    catalog.setdefault("services", {})["llm"] = llm
    resp = await client.put(
        f"{DEEPTUTOR_BASE}/api/v1/settings/catalog", json={"catalog": catalog}
    )
    resp.raise_for_status()
    log.info("seeded LLM profile binding=%s model=%s", LLM_BINDING, LLM_MODEL)


async def _ensure_partner(client: httpx.AsyncClient) -> str:
    resp = await client.get(f"{DEEPTUTOR_BASE}/api/v1/partners")
    resp.raise_for_status()
    partners = resp.json()
    if isinstance(partners, dict):
        partners = partners.get("partners", [])
    for partner in partners:
        if partner.get("name") == PARTNER_NAME:
            partner_id = partner.get("partner_id") or partner.get("id")
            log.info("reusing existing partner %s", partner_id)
            return partner_id
    resp = await client.post(
        f"{DEEPTUTOR_BASE}/api/v1/partners",
        json={
            "name": PARTNER_NAME,
            "description": PARTNER_DESCRIPTION,
            "start": True,
        },
    )
    resp.raise_for_status()
    body = resp.json()
    partner_id = body.get("partner_id") or body.get("id") or (
        body.get("partner", {}) or {}
    ).get("partner_id")
    if not partner_id:
        raise RuntimeError(f"could not determine partner id from response: {body}")
    log.info("created partner %s", partner_id)
    return partner_id


async def _probe_partner(client: httpx.AsyncClient, partner_id: str) -> str | None:
    """Send one probe message; return None on success, else the error text."""
    resp = await client.post(
        f"{DEEPTUTOR_BASE}/api/v1/partners/{partner_id}/chat",
        json={"content": "Reply with the single word: ready", "session_id": "bootstrap-probe"},
    )
    if resp.status_code != 200:
        return f"probe HTTP {resp.status_code}: {resp.text[:200]}"
    reply = str(resp.json().get("content") or "")
    if reply.startswith("Sorry, the turn failed"):
        return reply[:300]
    return None


async def _restart_partner(client: httpx.AsyncClient, partner_id: str) -> None:
    await client.post(f"{DEEPTUTOR_BASE}/api/v1/partners/{partner_id}/stop")
    await asyncio.sleep(2)
    resp = await client.post(f"{DEEPTUTOR_BASE}/api/v1/partners/{partner_id}/start")
    resp.raise_for_status()


async def _bootstrap_once() -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        await _wait_for_backend(client)
        await _seed_catalog(client)
        partner_id = await _ensure_partner(client)
        # The partner runtime may capture LLM config at start; if it raced
        # the catalog seed, its first calls use stale defaults. Probe with
        # a real turn and restart the partner once if the LLM call fails.
        if LLM_API_KEY:
            error = await _probe_partner(client, partner_id)
            if error is not None:
                log.warning("bootstrap probe failed (%s); restarting partner", error)
                await _restart_partner(client, partner_id)
                error = await _probe_partner(client, partner_id)
                if error is not None:
                    raise RuntimeError(f"partner still failing after restart: {error}")
            log.info("bootstrap probe ok — tutor answers with a live LLM")
        return partner_id


async def _bootstrap() -> str:
    global _bootstrapped, _partner_id
    async with _bootstrap_lock:
        if _bootstrapped and _partner_id:
            return _partner_id
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                _partner_id = await _bootstrap_once()
                _bootstrapped = True
                return _partner_id
            except Exception as exc:  # noqa: BLE001 - retried below
                last_error = exc
                log.warning("bootstrap attempt %d failed: %s", attempt, exc)
                await asyncio.sleep(3 * attempt)
        raise RuntimeError(f"bootstrap failed after 3 attempts: {last_error}")


@app.on_event("startup")
async def _kickoff_bootstrap() -> None:
    async def _run() -> None:
        try:
            await _bootstrap()
        except Exception as exc:  # noqa: BLE001 - surfaced via /ready and /health
            log.error("background bootstrap failed: %s", exc)

    asyncio.get_running_loop().create_task(_run())


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        await _bootstrap()
    except Exception as exc:  # noqa: BLE001 - health must report, not crash
        return {"status": "starting", "detail": str(exc)}
    return {"status": "ok", "partner_id": _partner_id}


@app.get("/ready")
async def ready() -> Any:
    """Shared-sidecar readiness: 200 only once the tutor verifiably answers."""
    from fastapi.responses import JSONResponse

    if _bootstrapped and _partner_id:
        return {"status": "ok", "partner_id": _partner_id}
    try:
        await _bootstrap()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "starting", "detail": str(exc)})
    return {"status": "ok", "partner_id": _partner_id}


@app.post("/v1/messages")
async def v1_messages(payload: MessageRequest) -> dict[str, Any]:
    partner_id = await _bootstrap()
    session_id = payload.sessionId or uuid.uuid4().hex
    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(
                f"{DEEPTUTOR_BASE}/api/v1/partners/{partner_id}/chat",
                json={"content": payload.message, "session_id": session_id},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"DeepTutor unreachable: {exc}")
    if resp.status_code != 200:
        detail = resp.text[:500]
        raise HTTPException(status_code=502, detail=f"DeepTutor error: {detail}")
    body = resp.json()
    reply = body.get("content") or ""
    turn_index = _turns.get(session_id, 0) + 1
    _turns[session_id] = turn_index
    return {
        "sessionId": body.get("session_id", session_id),
        "reply": reply,
        "turn": {
            "index": turn_index,
            "userMessage": payload.message,
            "assistantReply": reply,
        },
    }

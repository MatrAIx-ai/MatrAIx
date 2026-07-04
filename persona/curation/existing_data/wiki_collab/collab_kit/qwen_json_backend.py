#!/usr/bin/env python3
"""Normalize local Qwen OpenAI-compatible chat output for the collab runner."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"

JSON_SYSTEM_PROMPT = (
    "You are a strict JSON extraction endpoint for persona attribution. "
    "Return exactly one JSON object with a fields array. Do not include "
    "chain-of-thought, <think> blocks, markdown, prose, tables, bullets, or "
    "code fences."
)


def _base_url() -> str:
    return (
        os.environ.get("QWEN_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or "http://127.0.0.1:8000/v1"
    )


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _strip_noise(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def _extract_fields_object(text: str) -> dict[str, Any]:
    text = _strip_noise(text)
    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("fields"), list):
            return payload
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    found: dict[str, Any] | None = None
    for idx, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("fields"), list):
            found = payload
    if found is not None:
        return found
    raise ValueError(f"Qwen output did not contain a fields object: {text[:500]}")


def _extract_payload(response: dict[str, Any]) -> dict[str, Any]:
    if isinstance(response.get("fields"), list):
        return response
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"Unexpected Qwen response shape: {response}")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError(f"Unexpected Qwen choice shape: {first}")
    message = first.get("message")
    content = message.get("content") if isinstance(message, dict) else first.get("text")
    if not isinstance(content, str):
        raise ValueError(f"Unexpected Qwen message content: {first}")
    return _extract_fields_object(content)


def _request(prompt: str) -> dict[str, Any]:
    model = os.environ.get("WIKI_COLLAB_REQUESTED_MODEL", "").strip() or DEFAULT_MODEL
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": JSON_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": _float_env("WIKI_COLLAB_QWEN_TEMPERATURE", 0.0),
        "max_tokens": _int_env("WIKI_COLLAB_QWEN_MAX_TOKENS", 4096),
        "stream": False,
    }
    if os.environ.get("WIKI_COLLAB_QWEN_RESPONSE_FORMAT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "json",
    }:
        body["response_format"] = {"type": "json_object"}

    api_key = (
        os.environ.get("QWEN_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or "EMPTY"
    )
    request = urllib.request.Request(
        _chat_completions_url(_base_url()),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    timeout = _int_env("WIKI_COLLAB_COMMAND_TIMEOUT", 900)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    prompt = sys.stdin.read()
    try:
        response = _request(prompt)
        normalized = _extract_payload(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        sys.stderr.write(f"Qwen HTTP {exc.code}: {detail[:3000]}")
        return 1
    except Exception as exc:
        sys.stderr.write(str(exc)[:4000])
        return 2

    out = {
        "fields": normalized.get("fields", []),
        "reported_model": normalized.get("reported_model") or response.get("model") or DEFAULT_MODEL,
        "model_source": normalized.get("model_source") or "qwen_openai_compatible",
        "model_confidence": normalized.get("model_confidence") or "declared_or_api",
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

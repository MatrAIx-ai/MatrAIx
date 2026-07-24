"""Sidecar adapter that exposes the Rasa financial-demo bot behind the
PersonaBench chat API contract (POST /v1/messages -> {sessionId, reply}).

Rasa's REST channel returns a list of messages per user turn; this adapter
joins them into one reply string and surfaces button captions as plain text
so the persona can answer naturally.
"""

from __future__ import annotations

import os
import uuid

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

RASA_URL = os.environ.get("RASA_URL", "http://rasa:5005").rstrip("/")

_conversations: dict[str, list[dict[str, str]]] = {}


def _flatten_reply(rasa_messages: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for item in rasa_messages:
        text = str(item.get("text") or "").strip()
        if text:
            parts.append(text)
        buttons = item.get("buttons")
        if isinstance(buttons, list) and buttons:
            titles = [str(b.get("title", "")).strip() for b in buttons if b.get("title")]
            if titles:
                parts.append("Options: " + " / ".join(titles))
        image = item.get("image")
        if image:
            parts.append(f"[image: {image}]")
    return "\n".join(parts).strip()


@app.get("/health")
def health():
    try:
        status = requests.get(f"{RASA_URL}/status", timeout=5)
        status.raise_for_status()
    except requests.RequestException as exc:
        return jsonify({"status": "degraded", "rasa": str(exc)}), 503
    return jsonify({"status": "ok"})


@app.post("/v1/messages")
def post_message():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "message must not be empty"}), 400

    session_id = str(payload.get("sessionId") or "").strip() or uuid.uuid4().hex

    try:
        response = requests.post(
            f"{RASA_URL}/webhooks/rest/webhook",
            json={"sender": session_id, "message": message},
            timeout=60,
        )
        response.raise_for_status()
        rasa_messages = response.json()
    except (requests.RequestException, ValueError) as exc:
        return jsonify({"error": f"rasa upstream error: {exc}"}), 502

    reply = _flatten_reply(rasa_messages if isinstance(rasa_messages, list) else [])
    if not reply:
        reply = "(the assistant did not reply)"

    history = _conversations.setdefault(session_id, [])
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

    return jsonify({"sessionId": session_id, "reply": reply})


@app.get("/v1/conversation")
def get_conversation():
    session_id = str(request.args.get("sessionId", "")).strip()
    return jsonify({"sessionId": session_id, "messages": _conversations.get(session_id, [])})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

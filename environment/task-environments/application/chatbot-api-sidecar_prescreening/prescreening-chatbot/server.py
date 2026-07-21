"""Clinical-trial pre-screening chatbot sidecar (rule-based smoke implementation).

A deterministic screener for the `chat_prescreening-*` tasks: it loads a
trial protocol (criteria, probe questions, applicability rules) from
./protocols/, walks the participant through every applicable criterion one
question at a time, and ends with the fenced-JSON final assessment the task
verifiers check. Answers it cannot read as yes / no / not-sure trigger one
explicit confirmation question, so any cooperative participant can complete
the screen.

Protocol selection, in order: request body `protocolId` (or `title`) matching
a file in ./protocols/ or a `protocol_id` inside one; env
`PRESCREENING_PROTOCOL_ID`; the first protocol alphabetically.

This is a smoke-run product (same tier as the Acme support sidecar). A
production LLM screener can replace it by pointing the tasks'
`CHATBOT_UPSTREAM_PRESCREENING` at a different endpoint.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

PROTOCOLS_DIR = Path(__file__).resolve().parent / "protocols"

UNKNOWN_RE = re.compile(
    r"\b(don'?t know|do not know|not sure|unsure|no idea|can'?t remember|"
    r"cannot remember|not certain|never (checked|measured|tested)|"
    r"i'?d have to check|would have to check)\b",
    re.IGNORECASE,
)
NO_RE = re.compile(
    r"^\s*(no|nope|nah|never|none)\b|\b(don'?t have|do not have|haven'?t|"
    r"has not|hasn'?t|not applicable|doesn'?t apply|not pregnant|no,)\b",
    re.IGNORECASE,
)
YES_RE = re.compile(
    r"^\s*(yes|yeah|yep|yup|correct|definitely|absolutely|sure)\b|"
    r"\b(i do\b|i am\b|i have\b|that'?s right|yes,)\b",
    re.IGNORECASE,
)
FEMALE_RE = re.compile(r"\b(female|woman|girl|f)\b", re.IGNORECASE)
MALE_RE = re.compile(r"\b(male|man|boy|m)\b", re.IGNORECASE)

_sessions: dict[str, dict] = {}


def _load_protocols() -> dict[str, dict]:
    protocols = {}
    for path in sorted(PROTOCOLS_DIR.glob("*.json")):
        protocol = json.loads(path.read_text(encoding="utf-8"))
        protocols[path.stem] = protocol
        protocols.setdefault(protocol.get("protocol_id", path.stem), protocol)
    return protocols


PROTOCOLS = _load_protocols()


def _pick_protocol(payload: dict) -> dict:
    for key in ("protocolId", "title"):
        wanted = str(payload.get(key) or "").strip()
        if wanted and wanted in PROTOCOLS:
            return PROTOCOLS[wanted]
    env_id = os.environ.get("PRESCREENING_PROTOCOL_ID", "").strip()
    if env_id and env_id in PROTOCOLS:
        return PROTOCOLS[env_id]
    return PROTOCOLS[sorted(k for k in PROTOCOLS if k.startswith("chat_"))[0]]


def _uses_sex(protocol: dict) -> bool:
    return any("sex" in (c.get("not_applicable_when") or {}) for c in protocol["criteria"])


def _applicable(criterion: dict, sex: str | None) -> bool:
    condition = criterion.get("not_applicable_when") or {}
    if not condition:
        return True
    return not all(
        (key == "sex" and sex is not None and sex == value) or False
        for key, value in condition.items()
    )


def _parse_yes_no_unknown(text: str) -> str | None:
    if UNKNOWN_RE.search(text):
        return "unknown"
    if NO_RE.search(text):
        return "no"
    if YES_RE.search(text):
        return "yes"
    return None


def _greeting(protocol: dict) -> str:
    return (
        f"Hello! I can help you find out whether you might qualify for the study "
        f"\"{protocol['study_title']}\" ({protocol['protocol_id']}). I'll go through "
        "the eligibility questions one at a time. Please note this is a preliminary "
        "pre-screening only - it does not guarantee enrollment, and the study team "
        "will confirm final eligibility against your records."
    )


def _confirm_question(criterion: dict) -> str:
    if criterion["kind"] == "inclusion":
        return (
            f"Thanks. For this study, the requirement is: \"{criterion['text']}\" "
            "Based on what you just told me, do you meet this requirement - "
            "yes, no, or not sure?"
        )
    return (
        f"Thanks. This study excludes people for whom the following applies: "
        f"\"{criterion['text']}\" Does this apply to you - yes, no, or not sure?"
    )


def _record(state: dict, criterion: dict, answer: str) -> None:
    if answer == "unknown":
        status = "unknown"
    elif criterion["kind"] == "inclusion":
        status = "ok" if answer == "yes" else "fail"
    else:
        status = "fail" if answer == "yes" else "ok"
    state["results"][criterion["id"]] = status


def _next_prompt(state: dict) -> str:
    criteria = state["criteria"]
    index = state["index"]
    if index < len(criteria):
        return criteria[index]["probe"]
    return _final_assessment(state)


def _final_assessment(state: dict) -> str:
    results = state["results"]
    not_met = [cid for cid, status in results.items() if status == "fail"]
    unknown = [cid for cid, status in results.items() if status == "unknown"]
    if not_met:
        eligibility = "likely_ineligible"
        summary = (
            "Based on your answers, you are likely NOT eligible for this study "
            f"(criteria not met: {', '.join(not_met)})."
        )
    elif unknown:
        eligibility = "insufficient_information"
        summary = (
            "I could not determine some requirements from your answers "
            f"({', '.join(unknown)}), so there is not enough information for a "
            "preliminary result yet."
        )
    else:
        eligibility = "likely_eligible"
        summary = "Based on your answers, you appear likely eligible for this study."
    verdict = {
        "final_assessment": True,
        "eligibility": eligibility,
        "criteria_not_met": not_met,
        "criteria_unknown": unknown,
        "notes": "Deterministic pre-screen from self-reported answers.",
    }
    return (
        f"That was my last question. {summary} Remember, this is a preliminary "
        "pre-screen only - the study team makes the final eligibility decision.\n\n"
        "```json\n" + json.dumps(verdict, indent=1) + "\n```"
    )


def _advance(state: dict, message: str) -> str:
    # Optional one-time sex question so sex-conditional criteria can be skipped.
    if state["stage"] == "sex":
        if FEMALE_RE.search(message):
            state["sex"] = "female"
        elif MALE_RE.search(message):
            state["sex"] = "male"
        state["criteria"] = [
            c for c in state["protocol"]["criteria"] if _applicable(c, state["sex"])
        ]
        state["stage"] = "criteria"
        return _next_prompt(state)

    criteria = state["criteria"]
    if state["index"] >= len(criteria):
        return (
            "The screening is complete - my preliminary assessment is above. "
            "The study team will confirm final eligibility."
        )

    criterion = criteria[state["index"]]
    answer = _parse_yes_no_unknown(message)

    if answer is None and not state["confirming"]:
        state["confirming"] = True
        return _confirm_question(criterion)

    if answer is None:
        answer = "unknown"  # unreadable twice -> per protocol, treat as unknown

    _record(state, criterion, answer)
    state["confirming"] = False
    state["index"] += 1
    return _next_prompt(state)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "protocols": sorted(PROTOCOLS)})


@app.post("/v1/messages")
def post_message():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "message must not be empty"}), 400

    session_id = str(payload.get("sessionId") or "").strip() or uuid.uuid4().hex
    state = _sessions.get(session_id)
    if state is None:
        protocol = _pick_protocol(payload)
        state = {
            "protocol": protocol,
            "criteria": list(protocol["criteria"]),
            "index": 0,
            "results": {},
            "confirming": False,
            "sex": None,
            "stage": "sex" if _uses_sex(protocol) else "criteria",
            "turn": 0,
            "messages": [],
        }
        _sessions[session_id] = state
        if state["stage"] == "sex":
            first_question = (
                "First, may I ask your sex? Some questions only apply to certain "
                "participants."
            )
        else:
            first_question = _next_prompt(state)
        reply = f"{_greeting(protocol)}\n\n{first_question}"
    else:
        reply = _advance(state, message)

    state["turn"] += 1
    state["messages"].append({"role": "user", "content": message})
    state["messages"].append({"role": "assistant", "content": reply})
    turn_view = {
        "index": state["turn"],
        "userMessage": message,
        "assistantReply": reply,
    }
    return jsonify({"sessionId": session_id, "reply": reply, "turn": turn_view})


@app.get("/v1/conversation")
def get_conversation():
    session_id = str(request.args.get("sessionId") or "").strip()
    state = _sessions.get(session_id)
    if state is None:
        return jsonify({"sessionId": session_id, "messages": []})
    return jsonify({
        "sessionId": session_id,
        "domain": "clinical_trial_prescreening",
        "messages": state["messages"],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

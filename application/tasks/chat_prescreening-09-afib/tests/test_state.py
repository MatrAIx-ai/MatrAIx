"""Verifier for a clinical-trial pre-screening chatbot task.

Objective checks (rule-based, stdlib only), driven by this folder's data files:
  - transcript.json parses and has a valid multi-turn shape;
  - the screener ends with one fenced-JSON final assessment in an ASSISTANT
    turn (the LAST valid block wins; user-turn JSON is ignored by design);
  - a preliminary-screen disclaimer appears in an assistant turn;
  - when the transcript names a case from tests/ground_truth.json, the
    predicted eligibility label must match the deterministic ground truth.

Emits verifier/structured_output.json with task_outcome, conversation_summary,
and (when user_feedback.json exists) user_feedback contexts.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

TESTS_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(
    os.environ.get("HARBOR_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
FEEDBACK_PATH = OUTPUT_DIR / "user_feedback.json"

VALID_LABELS = {"likely_eligible", "likely_ineligible", "insufficient_information"}
DISCLAIMER_RE = re.compile(
    r"preliminary|pre[\s-]*screen|does\s*(?:not|n't)\s*guarantee|doesn'?t\s*guarantee|"
    r"no guarantee|not a guarantee|final eligibility|study (team|staff|coordinator)s? will "
    r"(confirm|verify|review|determine)",
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"```(?:json)?(.*?)```", re.DOTALL)


def _verifier_dir() -> Path:
    base = (
        os.environ.get("HARBOR_VERIFIER_DIR")
        or "/logs/verifier"
    )
    path = Path(base)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        path = TESTS_DIR.parent / "verifier"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _load_json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"Missing {path}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"{path.name} root must be an object"
    return value


def _require_string(value: Any, label: str) -> str:
    assert isinstance(value, str) and value.strip(), f"{label} must be a non-empty string"
    return value.strip()


def _last_verdict(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    verdict = None
    for entry in messages:
        if entry.get("role") != "assistant" or not isinstance(entry.get("content"), str):
            continue
        for block in FENCE_RE.findall(entry["content"]):
            try:
                candidate = json.loads(block.strip())
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and candidate.get("final_assessment") is True:
                verdict = candidate
    return verdict


def _ground_truth(transcript: dict[str, Any]) -> dict[str, Any] | None:
    gt_path = TESTS_DIR / "ground_truth.json"
    persona_id = transcript.get("personaId") or transcript.get("persona_id")
    if not gt_path.is_file() or not persona_id:
        return None
    return json.loads(gt_path.read_text(encoding="utf-8"))["cases"].get(str(persona_id))


def _optional_score(feedback: dict[str, Any], key: str) -> int | None:
    value = feedback.get(key)
    if value is None:
        return None
    assert isinstance(value, int) and 1 <= value <= 10, f"{key} must be an integer 1-10"
    return value


def test_transcript_schema() -> None:
    protocol = _load_json(TESTS_DIR / "protocol.json")
    transcript = _load_json(TRANSCRIPT_PATH)
    _require_string(transcript.get("sessionId"), "transcript.sessionId")
    _require_string(transcript.get("domain"), "transcript.domain")

    messages = transcript.get("messages")
    assert isinstance(messages, list) and messages, "transcript.messages must be a non-empty list"
    for entry in messages:
        assert entry.get("role") in {"user", "assistant"}, "invalid transcript role"
        _require_string(entry.get("content"), "message content")

    user_turns = sum(1 for entry in messages if entry.get("role") == "user")
    assistant_turns = sum(1 for entry in messages if entry.get("role") == "assistant")
    question_count = sum(
        1
        for entry in messages
        if entry.get("role") == "assistant" and "?" in entry.get("content", "")
    )

    verdict = _last_verdict(messages)
    assert verdict is not None, (
        "no parsable final assessment: the screener must end with one fenced JSON "
        "block with final_assessment=true in an assistant turn"
    )
    predicted = verdict.get("eligibility")
    assert predicted in VALID_LABELS, f"verdict.eligibility must be one of {sorted(VALID_LABELS)}"
    for key in ("criteria_not_met", "criteria_unknown"):
        assert isinstance(verdict.get(key), list), f"verdict.{key} must be a list"

    disclaimer_given = any(
        entry.get("role") == "assistant" and DISCLAIMER_RE.search(entry.get("content", ""))
        for entry in messages
    )
    assert disclaimer_given, "no preliminary-screen disclaimer found in any assistant turn"

    ground_truth = _ground_truth(transcript)
    if ground_truth is not None:
        outcome_status = "resolved" if predicted == ground_truth["label"] else "unresolved"
        resolution_basis = "objective_check"
        reason = (
            f"The screener's final assessment was {predicted}; the case's deterministic "
            f"ground-truth label is {ground_truth['label']}. The verdict was machine-"
            f"parsable and the preliminary-screen disclaimer was given."
        )
    else:
        outcome_status = "partially_resolved"
        resolution_basis = "conversation_commitment"
        reason = (
            "The screener produced a machine-parsable final assessment and gave the "
            "preliminary-screen disclaimer; the transcript did not name a labeled test "
            "case, so verdict correctness was not scored against ground truth."
        )

    conversation_path = (
        "clarify_then_resolve" if outcome_status == "resolved" and question_count > 0
        else "direct_resolution" if outcome_status == "resolved"
        else "clarify_then_partial" if question_count > 0
        else "stalled"
    )
    process_notes = (
        f"The screener asked {question_count} question-bearing turns while working "
        f"through the {protocol.get('protocol_id', 'trial')} eligibility criteria and "
        "closed with a structured verdict."
    )

    payload: dict[str, Any] = {
        "schemaVersion": "1.0",
        "artifactType": "matraix.trial_evaluation",
        "taskType": "chatbot",
        "presenceCheck": {
            "passed": True,
            "requiredArtifacts": ["transcript.json"],
            "missingArtifacts": [],
        },
        "sourceArtifacts": {
            "transcript": str(TRANSCRIPT_PATH),
            "userFeedback": str(FEEDBACK_PATH) if FEEDBACK_PATH.is_file() else None,
        },
        "contexts": [
            {
                "key": "task_outcome.primary",
                "label": "Task outcome",
                "contextType": "task_outcome",
                "facets": [
                    {"key": "outcome_status", "label": "Outcome status",
                     "role": "primary", "kind": "categorical", "value": outcome_status},
                    {"key": "resolution_basis", "label": "Resolution basis",
                     "role": "primary", "kind": "categorical", "value": resolution_basis},
                    {"key": "outcome_reason", "label": "Outcome reason",
                     "role": "explanation", "kind": "textual", "value": reason},
                    {"key": "task_goal_label", "label": "Task goal",
                     "role": "evidence", "kind": "textual",
                     "value": "Get a correct, clearly-caveated preliminary eligibility "
                              "assessment for the trial"},
                    {"key": "task_predicted_label", "label": "Predicted eligibility",
                     "role": "evidence", "kind": "categorical", "value": predicted},
                    {"key": "task_disclaimer_given", "label": "Preliminary disclaimer given",
                     "role": "evidence", "kind": "categorical", "value": "true"},
                ],
            },
            {
                "key": "conversation_summary.primary",
                "label": "Conversation summary",
                "contextType": "conversation_summary",
                "facets": [
                    {"key": "conversation_path", "label": "Conversation path",
                     "role": "primary", "kind": "categorical", "value": conversation_path},
                    {"key": "process_notes", "label": "Process notes",
                     "role": "explanation", "kind": "textual", "value": process_notes},
                    {"key": "user_turn_count", "label": "User turn count",
                     "role": "score", "kind": "numerical", "value": user_turns},
                    {"key": "assistant_turn_count", "label": "Assistant turn count",
                     "role": "score", "kind": "numerical", "value": assistant_turns},
                    {"key": "message_count", "label": "Message count",
                     "role": "score", "kind": "numerical", "value": len(messages)},
                    {"key": "clarification_question_count", "label": "Screening question count",
                     "role": "score", "kind": "numerical", "value": question_count},
                ],
            },
        ],
    }

    if FEEDBACK_PATH.is_file():
        feedback = _load_json(FEEDBACK_PATH)
        rating = _optional_score(feedback, "overallExperienceRating")
        assert rating is not None, (
            "user_feedback.overallExperienceRating is required when feedback exists"
        )
        fb_reason = _require_string(feedback.get("reason"), "user_feedback.reason")
        facets = [
            {"key": "overall_experience_rating", "label": "Overall experience rating",
             "role": "score", "kind": "numerical", "value": rating},
            {"key": "feedback_reason", "label": "Feedback reason",
             "role": "explanation", "kind": "textual", "value": fb_reason},
        ]
        trust = _optional_score(feedback, "trustLevel")
        if trust is not None:
            facets.append({"key": "trust_level", "label": "Trust level",
                           "role": "score", "kind": "numerical", "value": trust})
        payload["contexts"].append({
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": facets,
        })

    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    assert outcome_status != "unresolved", reason


if __name__ == "__main__":
    test_transcript_schema()
    print("prescreening verifier: OK")

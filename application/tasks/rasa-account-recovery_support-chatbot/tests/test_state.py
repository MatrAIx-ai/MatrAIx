from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path(
    os.environ.get("PERSONABENCH_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
RESULT_PATH = OUTPUT_DIR / "account_recovery_result.json"

ALLOWED_OUTCOMES = {
    "recovery_options_explained",
    "escalated",
    "blocked",
    "unclear",
}
DISALLOWED_PII = {
    "ssn",
    "social security",
    "password",
    "full card",
    "credit card number",
    "government id",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"{path} is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty string")
    return value


def require_rating(value: Any, label: str) -> int:
    if not isinstance(value, int) or value < 1 or value > 10:
        fail(f"{label} must be an integer 1-10")
    return value


def validate_messages(messages: Any) -> None:
    if not isinstance(messages, list):
        fail("transcript.messages must be a list")
    user_turns = 0
    assistant_turns = 0
    combined: list[str] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            fail(f"transcript.messages[{index}] must be an object")
        role = message.get("role")
        content = require_string(message.get("content"), "message content")
        if role not in {"user", "assistant"}:
            fail(f"message role must be user or assistant, got {role!r}")
        if role == "user":
            user_turns += 1
        else:
            assistant_turns += 1
        combined.append(content.lower())
    if user_turns < 3:
        fail(f"expected at least 3 user turns, found {user_turns}")
    if assistant_turns < 3:
        fail(f"expected at least 3 assistant turns, found {assistant_turns}")
    transcript_text = " ".join(combined)
    if "account" not in transcript_text:
        fail("conversation should mention account recovery")
    if "recover" not in transcript_text and "recovery" not in transcript_text:
        fail("conversation should include recovery language")


def validate_source_reference(source: Any) -> None:
    if not isinstance(source, dict):
        fail("source_reference must be an object")
    repository = require_string(source.get("repository"), "source_reference.repository")
    if repository != "https://github.com/RasaHQ/rasa":
        fail("source_reference.repository must point to RasaHQ/rasa")
    runtime = require_string(source.get("runtime"), "source_reference.runtime")
    if "rasa/rasa:" not in runtime:
        fail("source_reference.runtime must name the Rasa container image")
    endpoint = require_string(source.get("endpoint"), "source_reference.endpoint")
    if "rasa-account-recovery" not in endpoint:
        fail("source_reference.endpoint must point at the Rasa sidecar")


def validate_application_result(result: Any) -> None:
    if not isinstance(result, dict):
        fail("application_result must be an object")
    outcome = require_string(result.get("outcome_class"), "application_result.outcome_class")
    if outcome not in ALLOWED_OUTCOMES:
        fail(f"unsupported outcome_class {outcome!r}")
    require_string(result.get("recovery_path"), "application_result.recovery_path")
    asked = result.get("asked_for_sensitive_data")
    if not isinstance(asked, bool):
        fail("application_result.asked_for_sensitive_data must be boolean")
    requested = result.get("requested_personal_data")
    if not isinstance(requested, list):
        fail("application_result.requested_personal_data must be a list")
    requested_text = " ".join(str(item).lower() for item in requested)
    for token in DISALLOWED_PII:
        if token in requested_text:
            fail(f"requested_personal_data includes disallowed sensitive data: {token}")


def validate_self_report(report: Any) -> None:
    if not isinstance(report, dict):
        fail("persona_self_report must be an object")
    require_rating(report.get("trust_rating"), "persona_self_report.trust_rating")
    require_rating(
        report.get("frustration_rating"),
        "persona_self_report.frustration_rating",
    )
    privacy = require_string(
        report.get("privacy_comfort"),
        "persona_self_report.privacy_comfort",
    )
    if privacy not in {"low", "medium", "high"}:
        fail("persona_self_report.privacy_comfort must be low, medium, or high")
    require_string(report.get("reason"), "persona_self_report.reason")


def validate_metric_summary(summary: Any) -> None:
    if not isinstance(summary, dict):
        fail("metric_summary must be an object")
    numeric = summary.get("numeric")
    categorical = summary.get("categorical")
    textual = summary.get("textual")
    if not isinstance(numeric, dict) or not numeric:
        fail("metric_summary.numeric must be a non-empty object")
    if not isinstance(categorical, dict) or not categorical:
        fail("metric_summary.categorical must be a non-empty object")
    if not isinstance(textual, dict) or not textual:
        fail("metric_summary.textual must be a non-empty object")
    for key in ("turns_to_resolution", "trust_rating", "frustration_rating"):
        value = numeric.get(key)
        if not isinstance(value, (int, float)):
            fail(f"metric_summary.numeric.{key} must be numeric")
    if categorical.get("outcome_class") not in ALLOWED_OUTCOMES:
        fail("metric_summary.categorical.outcome_class is missing or unsupported")
    for key, value in textual.items():
        require_string(value, f"metric_summary.textual.{key}")


def main() -> int:
    transcript = load_json(TRANSCRIPT_PATH)
    result = load_json(RESULT_PATH)

    conversation_id = require_string(
        transcript.get("conversation_id"),
        "transcript.conversation_id",
    )
    if result.get("conversation_id") != conversation_id:
        fail("transcript and result conversation_id differ")

    endpoint = require_string(transcript.get("endpoint"), "transcript.endpoint")
    if "rasa-account-recovery" not in endpoint:
        fail("transcript.endpoint must point at the Rasa sidecar")
    if transcript.get("sidecar") != "rasa-account-recovery":
        fail("transcript.sidecar must be rasa-account-recovery")

    validate_messages(transcript.get("messages"))
    validate_source_reference(result.get("source_reference"))
    validate_application_result(result.get("application_result"))
    validate_self_report(result.get("persona_self_report"))
    validate_metric_summary(result.get("metric_summary"))

    print("PASS: Rasa account recovery chatbot artifacts are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

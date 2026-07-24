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
    # Canonical resolution (task-spec #262): HARBOR_VERIFIER_DIR in a Harbor
    # trial, else the mounted /logs/verifier in a Docker sandbox. No
    # <task-root>/verifier fallback - that is local-dev leakage.
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path
    container_default = Path("/logs/verifier")
    try:
        container_default.mkdir(parents=True, exist_ok=True)
        return container_default
    except OSError as exc:
        raise RuntimeError(
            "HARBOR_VERIFIER_DIR is required when running outside a Harbor "
            "trial container; point it at jobs/<job>/<trial>/verifier."
        ) from exc


def _load_json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"Missing {path}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # clean failure, not a raw traceback
        raise AssertionError(f"{path.name} is not valid JSON: {exc}") from exc
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


def _protocol() -> dict[str, Any]:
    return _load_json(TESTS_DIR / "protocol.json")


def _applicable_criteria(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    """Protocol criteria that could apply to this run.

    Sex-gated criteria are only expected when the screener itself treated them
    as in scope, i.e. when it named them in one of its criterion lists.
    """
    named = set(verdict.get("criteria_not_met") or []) | set(
        verdict.get("criteria_unknown") or []
    )
    out = []
    for criterion in _protocol()["criteria"]:
        if criterion.get("not_applicable_when") and criterion["id"] not in named:
            continue
        out.append(criterion)
    return out


def _criterion_coverage(
    messages: list[dict[str, Any]], verdict: dict[str, Any]
) -> tuple[set[str], set[str]]:
    """(covered, uncovered) criterion ids, by matching the screener's own turns.

    A criterion counts as covered when an assistant turn quotes its probe or
    enough of its keywords, or when the verdict already reports on it.
    """
    asked = " ".join(
        entry.get("content", "").lower()
        for entry in messages
        if entry.get("role") == "assistant"
    )
    reported = set(verdict.get("criteria_not_met") or []) | set(
        verdict.get("criteria_unknown") or []
    )
    covered, uncovered = set(), set()
    for criterion in _applicable_criteria(verdict):
        cid = criterion["id"]
        probe = (criterion.get("probe") or "").lower().strip().rstrip("?")
        keywords = [str(k).lower() for k in (criterion.get("keywords") or [])]
        hit = cid in reported
        if not hit and probe:
            hit = probe[:40] in asked
        if not hit and keywords:
            hit = sum(1 for k in keywords if k in asked) >= max(1, len(keywords) // 2)
        (covered if hit else uncovered).add(cid)
    return covered, uncovered


def _label_from_criteria(verdict: dict[str, Any]) -> str:
    """The eligibility label the screener's own criterion lists imply.

    A failed criterion is decisive, so it outranks anything still unknown; an
    unknown that is not already excluded leaves the screen incomplete.
    """
    if verdict.get("criteria_not_met"):
        return "likely_ineligible"
    if verdict.get("criteria_unknown"):
        return "insufficient_information"
    return "likely_eligible"


def _ground_truth(transcript: dict[str, Any]) -> dict[str, Any] | None:
    """Look up the labeled case for this trial, trying every id channel a
    runner can provide: transcript caseId/personaId (offline runners write
    these) or the MATRIX_TRIAL_CASE_ID env var (for harnesses that know the
    case out-of-band). The stock chat harness injects none of them yet, so
    label checking stays inert there until case-bound personas land."""
    gt_path = TESTS_DIR / "ground_truth.json"
    if not gt_path.is_file():
        return None
    cases = json.loads(gt_path.read_text(encoding="utf-8"))["cases"]
    # Trust order matters: the MATRIX_TRIAL_CASE_ID env var is the harness's
    # out-of-band grading key and outranks anything in transcript.json, which is
    # the artifact under test (a hostile transcript must not pick its own case).
    env_case = os.environ.get("MATRIX_TRIAL_CASE_ID", "").strip()
    if env_case:
        case = cases.get(env_case)
        assert case is not None, (
            f"MATRIX_TRIAL_CASE_ID={env_case!r} is not a case in ground_truth.json"
        )
        return case
    transcript_case = (
        transcript.get("caseId")
        or transcript.get("personaId")
        or transcript.get("persona_id")
    )
    if not transcript_case:
        return None
    return cases.get(str(transcript_case))


def _optional_score(feedback: dict[str, Any], key: str) -> int | None:
    value = feedback.get(key)
    if value is None:
        return None
    assert isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 10, (
        f"{key} must be an integer 1-10"
    )
    return value


def _enum_text(feedback: dict[str, Any], key: str) -> str | None:
    value = feedback.get(key)
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return "yes"
    if text in {"false", "0"}:
        return "no"
    assert text in {"yes", "partially", "no"}, f"{key} must be yes / partially / no"
    return text


def test_transcript_schema() -> None:
    # Never let a prior run's verdict survive this one: a failing verifier must
    # not leave a stale 'resolved' structured_output.json behind.
    stale = _verifier_dir() / "structured_output.json"
    if stale.exists():
        stale.unlink()

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

    # Persona runs have no pre-labeled answer key: the persona is the patient and
    # improvises their own history. What is still objectively checkable from the
    # transcript alone is whether the screener followed the protocol -- it must
    # ask about every applicable criterion before concluding, and its verdict must
    # follow from the criterion lists it reported.
    covered, uncovered = _criterion_coverage(messages, verdict)
    expected_label = _label_from_criteria(verdict)
    consistent = predicted == expected_label

    if uncovered:
        outcome_status = "unresolved"
        reason = (
            "The screener concluded without asking about every applicable criterion; "
            f"it never covered {', '.join(sorted(uncovered))}."
        )
    elif not consistent:
        outcome_status = "unresolved"
        reason = (
            f"The screener answered {predicted}, but the criteria it reported imply "
            f"{expected_label} (criteria_not_met={verdict['criteria_not_met']}, "
            f"criteria_unknown={verdict['criteria_unknown']})."
        )
    else:
        outcome_status = "resolved"
        reason = (
            f"The screener covered all {len(covered)} applicable criteria, gave the "
            f"preliminary-screen disclaimer, and returned {predicted}, which follows "
            "from the criteria it reported."
        )
    resolution_basis = "objective_check"

    # An offline QA sweep can additionally pin a labeled case; when it does, the
    # verdict must also match that answer key. Real persona runs skip this.
    ground_truth = _ground_truth(transcript)
    if ground_truth is not None and outcome_status == "resolved":
        if predicted != ground_truth["label"]:
            outcome_status = "unresolved"
            reason = (
                f"The screener's final assessment was {predicted}; the pinned case's "
                f"deterministic ground-truth label is {ground_truth['label']}."
            )
        else:
            reason += f" It also matches the pinned case label {ground_truth['label']}."

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
        # Emit every field the self-report schema collects: a user_feedback
        # context suppresses the platform's own synthesis, so anything omitted
        # here is silently dropped from aggregation and reports.
        facets = [
            {"key": "overall_experience_rating", "label": "Overall experience rating",
             "role": "score", "kind": "numerical", "value": rating},
            {"key": "feedback_reason", "label": "Feedback reason",
             "role": "explanation", "kind": "textual", "value": fb_reason},
        ]
        need = _enum_text(feedback, "needConstraintSatisfaction")
        if need is not None:
            facets.append({"key": "need_constraint_satisfaction",
                           "label": "Need or constraint satisfaction",
                           "role": "primary", "kind": "categorical", "value": need})
        preference = _enum_text(feedback, "personalPreferenceSatisfaction")
        if preference is not None:
            facets.append({"key": "personal_preference_satisfaction",
                           "label": "Personal preference satisfaction",
                           "role": "evidence", "kind": "categorical", "value": preference})
        clarify = feedback.get("askedUsefulClarificationQuestions")
        if isinstance(clarify, bool):
            facets.append({"key": "clarification_questions_useful",
                           "label": "Clarification questions useful",
                           "role": "primary", "kind": "categorical",
                           "value": "true" if clarify else "false"})
        notes = feedback.get("clarifyingNotes")
        if isinstance(notes, str) and notes.strip():
            facets.append({"key": "clarifying_notes", "label": "Clarifying notes",
                           "role": "explanation", "kind": "textual",
                           "value": notes.strip()})
        trust = _optional_score(feedback, "trustLevel")
        if trust is not None:
            facets.append({"key": "trust_level", "label": "Trust level",
                           "role": "score", "kind": "numerical", "value": trust})
        understood = feedback.get("feltUnderstood")
        if isinstance(understood, bool):
            facets.append({"key": "felt_understood", "label": "Felt understood",
                           "role": "evidence", "kind": "categorical",
                           "value": "true" if understood else "false"})
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

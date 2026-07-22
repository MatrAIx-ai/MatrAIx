from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

OUTPUT = Path("/app/output/selfhosted_note_tool_comparison.json")
USER_FEEDBACK = Path("/app/output/user_feedback.json")
SOURCE_URL = "https://awesome-selfhosted.net/tags/note-taking--editors.html"
CATEGORY_LABEL = "Note-taking & Editors"
BASIS_VALUES = {
    "price",
    "quality",
    "features",
    "convenience",
    "taste",
    "trust",
    "familiarity",
    "novelty",
    "fit",
    "other",
}
EXPLORATION_STYLES = {"compared_multiple", "deep_research"}
SATISFACTION_BUCKETS = {"yes", "partially", "no"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _nonempty(value: object, field: str, *, maximum_length: int | None = None) -> str:
    assert isinstance(value, str) and value.strip(), f"{field} must be non-empty"
    cleaned = value.strip()
    if maximum_length is not None:
        assert len(cleaned) <= maximum_length, (
            f"{field} must be at most {maximum_length} characters"
        )
    return cleaned


def _integer(value: object, field: str, *, minimum: int, maximum: int) -> int:
    assert isinstance(value, int) and not isinstance(value, bool), (
        f"{field} must be an integer"
    )
    assert minimum <= value <= maximum, (
        f"{field} must be between {minimum} and {maximum}"
    )
    return value


def _url(value: object, field: str) -> str:
    cleaned = _nonempty(value, field, maximum_length=1000)
    parsed = urlparse(cleaned)
    assert parsed.scheme in {"http", "https"} and parsed.netloc, (
        f"{field} must be an absolute HTTP(S) URL"
    )
    return cleaned


def _string_list(
    value: object,
    field: str,
    *,
    maximum_items: int = 20,
    maximum_item_length: int = 120,
) -> list[str]:
    assert isinstance(value, list) and value, f"{field} must be a non-empty array"
    assert len(value) <= maximum_items, f"{field} contains too many values"
    cleaned = [
        _nonempty(item, f"{field}[{index}]", maximum_length=maximum_item_length)
        for index, item in enumerate(value)
    ]
    assert len(cleaned) == len(set(cleaned)), f"{field} values must be distinct"
    return cleaned


def _validate_candidate(candidate: object, index: int) -> dict[str, object]:
    assert isinstance(candidate, dict), f"task_shortlist[{index}] must be an object"
    prefix = f"task_shortlist[{index}]"
    subject_id = _url(
        candidate.get("decision_subject_id"), f"{prefix}.decision_subject_id"
    )
    source_code_url = _url(
        candidate.get("task_source_code_url"), f"{prefix}.task_source_code_url"
    )
    assert subject_id == source_code_url, (
        f"{prefix}.decision_subject_id must equal task_source_code_url"
    )
    project_url = _url(candidate.get("task_project_url"), f"{prefix}.task_project_url")
    evidence_url = _url(
        candidate.get("task_detail_evidence_url"),
        f"{prefix}.task_detail_evidence_url",
    )
    assert evidence_url in {project_url, source_code_url}, (
        f"{prefix}.task_detail_evidence_url must equal the recorded Website or "
        "Source Code URL"
    )

    last_update = _nonempty(
        candidate.get("task_last_update"),
        f"{prefix}.task_last_update",
        maximum_length=10,
    )
    assert last_update == "?" or DATE_PATTERN.fullmatch(last_update), (
        f"{prefix}.task_last_update must be YYYY-MM-DD or ?"
    )

    return {
        "decision_subject_id": subject_id,
        "decision_subject_label": _nonempty(
            candidate.get("decision_subject_label"),
            f"{prefix}.decision_subject_label",
            maximum_length=160,
        ),
        "task_project_url": project_url,
        "task_source_code_url": source_code_url,
        "task_detail_evidence_url": evidence_url,
        "task_description": _nonempty(
            candidate.get("task_description"),
            f"{prefix}.task_description",
            maximum_length=1200,
        ),
        "task_platforms": _string_list(
            candidate.get("task_platforms"), f"{prefix}.task_platforms"
        ),
        "task_licenses": _string_list(
            candidate.get("task_licenses"), f"{prefix}.task_licenses"
        ),
        "task_last_update": last_update,
        "task_fit_note": _nonempty(
            candidate.get("task_fit_note"),
            f"{prefix}.task_fit_note",
            maximum_length=1600,
        ),
        "task_tradeoff_note": _nonempty(
            candidate.get("task_tradeoff_note"),
            f"{prefix}.task_tradeoff_note",
            maximum_length=1600,
        ),
    }


def _verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path

    container_default = Path("/logs/verifier")
    try:
        container_default.mkdir(parents=True, exist_ok=True)
        return container_default
    except OSError:
        pass

    raise RuntimeError(
        "HARBOR_VERIFIER_DIR is required when running outside a Harbor trial "
        "container. Point it at jobs/<job>/<trial>/verifier for local harness runs."
    )


def _write_structured_output(payload: dict[str, object]) -> None:
    path = _verifier_dir() / "structured_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> dict[str, object]:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert isinstance(data, dict), (
        "selfhosted_note_tool_comparison.json root must be an object"
    )
    return data


def _load_user_feedback() -> dict[str, object] | None:
    if not USER_FEEDBACK.is_file():
        return None
    data = json.loads(USER_FEEDBACK.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "user_feedback.json root must be an object"

    need = data.get("needConstraintSatisfaction")
    assert need in SATISFACTION_BUCKETS, (
        "needConstraintSatisfaction must use a supported bucket"
    )
    preference = data.get("personalPreferenceSatisfaction")
    assert preference in SATISFACTION_BUCKETS, (
        "personalPreferenceSatisfaction must use a supported bucket"
    )
    reason = _nonempty(data.get("reason"), "feedback reason", maximum_length=2000)
    overall = _integer(
        data.get("overallExperienceRating"),
        "overallExperienceRating",
        minimum=1,
        maximum=10,
    )

    payload: dict[str, object] = {
        "need_constraint_satisfaction": need,
        "personal_preference_satisfaction": preference,
        "overall_experience_rating": overall,
        "feedback_reason": reason,
    }
    for source_key, target_key in (
        ("trustLevel", "trust_level"),
        ("effortRating", "effort_rating"),
    ):
        value = data.get(source_key)
        if value is not None:
            payload[target_key] = _integer(value, source_key, minimum=1, maximum=10)

    clarity = data.get("clarityOfNextStep")
    if clarity is not None:
        assert isinstance(clarity, bool), "clarityOfNextStep must be boolean"
        payload["clarity_of_next_step"] = "true" if clarity else "false"
    return payload


def _execution_contexts(
    *, subject_id: str, subject_label: str, reviewed_count: int
) -> list[dict[str, object]]:
    return [
        {
            "key": "task_outcome.primary",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": [
                {
                    "key": "outcome_status",
                    "label": "Outcome status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "passed",
                },
                {
                    "key": "goal_completion_ratio",
                    "label": "Goal completion ratio",
                    "role": "score",
                    "kind": "numerical",
                    "value": 1.0,
                },
                {
                    "key": "goal_completion_bucket",
                    "label": "Goal completion bucket",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "complete",
                },
                {
                    "key": "verifier_mode",
                    "label": "Verifier mode",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": "artifact_exact",
                },
                {
                    "key": "primary_failure_reason",
                    "label": "Primary failure reason",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "none",
                },
                {
                    "key": "outcome_explanation",
                    "label": "Outcome explanation",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The user compared three self-hosted note-taking projects "
                        f"after reviewing {reviewed_count} category listings."
                    ),
                },
                {
                    "key": "completion_evidence",
                    "label": "Completion evidence",
                    "role": "evidence",
                    "kind": "textual",
                    "value": (
                        f"Saved {OUTPUT.name} with a schema-valid, internally "
                        "consistent three-project comparison."
                    ),
                },
            ],
        },
        {
            "key": "web_artifact.primary",
            "label": "Web artifact",
            "contextType": "web_artifact",
            "facets": [
                {
                    "key": "artifact_type",
                    "label": "Artifact type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "selection",
                },
                {
                    "key": "artifact_status",
                    "label": "Artifact status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "correct",
                },
                {
                    "key": "artifact_subject_label",
                    "label": "Artifact subject label",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": subject_label,
                },
                {
                    "key": "artifact_subject_id",
                    "label": "Artifact subject ID",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": subject_id,
                },
                {
                    "key": "artifact_evidence",
                    "label": "Artifact evidence",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The selected project label and Source Code URL match "
                        "exactly one entry in the three-project shortlist."
                    ),
                },
            ],
        },
        {
            "key": "web_interaction.primary",
            "label": "Web interaction",
            "contextType": "web_interaction",
            "facets": [
                {
                    "key": "navigation_path_type",
                    "label": "Navigation path type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "compare_then_commit",
                },
                {
                    "key": "web_interaction_notes",
                    "label": "Web interaction notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The submission records a category-browse and detailed "
                        "three-project comparison before one selection."
                    ),
                },
            ],
        },
    ]


def test_output_exists() -> None:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema() -> None:
    data = _load()
    feedback = _load_user_feedback()

    subject_id = _url(data.get("decision_subject_id"), "decision_subject_id")
    subject_label = _nonempty(
        data.get("decision_subject_label"),
        "decision_subject_label",
        maximum_length=160,
    )
    assert data.get("decision_outcome") == "selected", (
        "decision_outcome must be selected"
    )

    basis_primary = data.get("basis_primary")
    assert basis_primary in BASIS_VALUES, "basis_primary must use a supported bucket"
    basis_secondary = data.get("basis_secondary")
    if basis_secondary is not None:
        assert basis_secondary in BASIS_VALUES, (
            "basis_secondary must use a supported bucket"
        )
        assert basis_secondary != basis_primary, (
            "basis_secondary must differ from basis_primary"
        )

    exploration_style = data.get("exploration_style")
    assert exploration_style in EXPLORATION_STYLES, (
        "exploration_style must be compared_multiple or deep_research"
    )
    reason = _nonempty(data.get("reason"), "reason", maximum_length=2400)
    assert data.get("task_source_url") == SOURCE_URL, (
        f"task_source_url must be {SOURCE_URL}"
    )
    assert data.get("task_category_label") == CATEGORY_LABEL, (
        f"task_category_label must be {CATEGORY_LABEL}"
    )
    reviewed_count = _integer(
        data.get("task_projects_reviewed_count"),
        "task_projects_reviewed_count",
        minimum=5,
        maximum=200,
    )

    raw_shortlist = data.get("task_shortlist")
    assert isinstance(raw_shortlist, list), "task_shortlist must be an array"
    assert len(raw_shortlist) == 3, "task_shortlist must contain exactly three projects"
    shortlist = [
        _validate_candidate(item, index) for index, item in enumerate(raw_shortlist)
    ]

    ids = [str(candidate["decision_subject_id"]) for candidate in shortlist]
    labels = [str(candidate["decision_subject_label"]) for candidate in shortlist]
    project_urls = [str(candidate["task_project_url"]) for candidate in shortlist]
    assert len(ids) == len(set(ids)), "shortlisted Source Code URLs must be distinct"
    assert len(labels) == len(set(labels)), (
        "shortlisted project labels must be distinct"
    )
    assert len(project_urls) == len(set(project_urls)), (
        "shortlisted Website URLs must be distinct"
    )

    selected_matches = [
        candidate
        for candidate in shortlist
        if candidate["decision_subject_id"] == subject_id
    ]
    assert len(selected_matches) == 1, (
        "selected project must appear exactly once in task_shortlist"
    )
    selected = selected_matches[0]
    assert selected["decision_subject_label"] == subject_label, (
        "selected project label must match the shortlisted project"
    )

    source_artifacts: dict[str, object] = {"taskOutput": str(OUTPUT)}
    contexts = _execution_contexts(
        subject_id=subject_id,
        subject_label=subject_label,
        reviewed_count=reviewed_count,
    )

    decision_facets: list[dict[str, object]] = [
        {
            "key": "decision_outcome",
            "label": "Decision outcome",
            "role": "primary",
            "kind": "categorical",
            "value": "selected",
        },
        {
            "key": "basis_primary",
            "label": "Primary basis",
            "role": "primary",
            "kind": "categorical",
            "value": basis_primary,
        },
        {
            "key": "reason",
            "label": "Reason",
            "role": "explanation",
            "kind": "textual",
            "explainsFacetKey": "decision_subject_label",
            "value": reason,
        },
        {
            "key": "decision_subject_id",
            "label": "Decision subject ID",
            "role": "evidence",
            "kind": "categorical",
            "value": subject_id,
        },
        {
            "key": "decision_subject_label",
            "label": "Decision subject label",
            "role": "evidence",
            "kind": "categorical",
            "value": subject_label,
        },
        {
            "key": "task_selected_platforms",
            "label": "Selected project platforms",
            "role": "evidence",
            "kind": "categorical",
            "value": " | ".join(selected["task_platforms"]),
        },
        {
            "key": "task_selected_licenses",
            "label": "Selected project licenses",
            "role": "evidence",
            "kind": "categorical",
            "value": " | ".join(selected["task_licenses"]),
        },
        {
            "key": "task_last_update",
            "label": "Selected project last update",
            "role": "evidence",
            "kind": "categorical",
            "value": selected["task_last_update"],
        },
    ]
    if basis_secondary is not None:
        decision_facets.append(
            {
                "key": "basis_secondary",
                "label": "Secondary basis",
                "role": "primary",
                "kind": "categorical",
                "value": basis_secondary,
            }
        )

    contexts.extend(
        [
            {
                "key": "decision.primary",
                "label": "Primary decision",
                "contextType": "decision",
                "facets": decision_facets,
            },
            {
                "key": "decision.process",
                "label": "Decision process",
                "contextType": "decision_process",
                "facets": [
                    {
                        "key": "exploration_style",
                        "label": "Exploration style",
                        "role": "primary",
                        "kind": "categorical",
                        "value": exploration_style,
                    },
                    {
                        "key": "options_considered_count",
                        "label": "Options considered count",
                        "role": "score",
                        "kind": "numerical",
                        "value": reviewed_count,
                    },
                    {
                        "key": "comparison_notes",
                        "label": "Comparison notes",
                        "role": "explanation",
                        "kind": "textual",
                        "explainsFacetKey": "exploration_style",
                        "value": (
                            f"The user reviewed {reviewed_count} listings and "
                            "recorded fit and tradeoff notes for three projects."
                        ),
                    },
                ],
            },
        ]
    )

    if feedback is not None:
        source_artifacts["userFeedback"] = str(USER_FEEDBACK)
        feedback_facets: list[dict[str, object]] = [
            {
                "key": "overall_experience_rating",
                "label": "Overall experience rating",
                "role": "score",
                "kind": "numerical",
                "value": feedback["overall_experience_rating"],
            },
            {
                "key": "feedback_reason",
                "label": "Feedback reason",
                "role": "explanation",
                "kind": "textual",
                "explainsFacetKey": "overall_experience_rating",
                "value": feedback["feedback_reason"],
            },
            {
                "key": "need_constraint_satisfaction",
                "label": "Need or constraint satisfaction",
                "role": "evidence",
                "kind": "categorical",
                "value": feedback["need_constraint_satisfaction"],
            },
            {
                "key": "personal_preference_satisfaction",
                "label": "Personal preference satisfaction",
                "role": "evidence",
                "kind": "categorical",
                "value": feedback["personal_preference_satisfaction"],
            },
        ]
        for key, label in (
            ("trust_level", "Choice confidence"),
            ("effort_rating", "Effort rating"),
        ):
            if key in feedback:
                feedback_facets.append(
                    {
                        "key": key,
                        "label": label,
                        "role": "score",
                        "kind": "numerical",
                        "value": feedback[key],
                    }
                )
        if "clarity_of_next_step" in feedback:
            feedback_facets.append(
                {
                    "key": "clarity_of_next_step",
                    "label": "Clarity of choice",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": feedback["clarity_of_next_step"],
                }
            )
        contexts.append(
            {
                "key": "user_feedback.primary",
                "label": "User feedback",
                "contextType": "user_feedback",
                "facets": feedback_facets,
            }
        )

    _write_structured_output(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "web",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": [OUTPUT.name],
                "missingArtifacts": [],
            },
            "sourceArtifacts": source_artifacts,
            "contexts": contexts,
        }
    )

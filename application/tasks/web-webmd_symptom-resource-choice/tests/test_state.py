from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

OUTPUT = Path("/app/output/symptom_resource_choice.json")
USER_FEEDBACK = Path("/app/output/user_feedback.json")
SOURCE_URL = "https://www.webmd.com/"
WEBMD_HOST = "www.webmd.com"
MIN_CANDIDATES = 3
BASIS_VALUES = {
    "trust",
    "fit",
    "quality",
    "features",
    "convenience",
    "familiarity",
    "novelty",
    "other",
}
EXPLORATION_STYLES = {"compared_multiple", "deep_research"}
SATISFACTION_BUCKETS = {"yes", "partially", "no"}
GOAL_COMPONENT_WEIGHT = 0.2
ARTICLE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _canonical_slug_from_path(path: str) -> str:
    parts = [segment for segment in path.strip("/").split("/") if segment]
    slug_segments = [
        re.sub(r"\.(htm|html)$", "", segment, flags=re.IGNORECASE) for segment in parts
    ]
    return "-".join(slug_segments).lower().replace("_", "-")


def _nonempty(value: object, field: str, *, maximum_length: int | None = None) -> str:
    assert isinstance(value, str) and value.strip(), f"{field} must be non-empty"
    cleaned = value.strip()
    if maximum_length is not None:
        assert len(cleaned) <= maximum_length, (
            f"{field} must be at most {maximum_length} characters"
        )
    return cleaned


def _article_slug(url: object, field: str) -> str:
    article_url = _nonempty(url, field, maximum_length=500)
    parsed = urlparse(article_url)
    assert parsed.scheme == "https", f"{field} must use https"
    assert parsed.netloc == WEBMD_HOST, f"{field} must use {WEBMD_HOST}"
    assert not parsed.query and not parsed.fragment, (
        f"{field} must not contain a query or fragment"
    )
    parts = [segment for segment in parsed.path.strip("/").split("/") if segment]
    assert parts, f"{field} must point to a WebMD article path"
    slug = _canonical_slug_from_path(parsed.path)
    assert ARTICLE_SLUG.fullmatch(slug), f"{field} produced an invalid article slug"
    return slug


def _validate_candidate(candidate: object, index: int) -> dict[str, str]:
    assert isinstance(candidate, dict), f"task_options_considered[{index}] must be an object"
    prefix = f"task_options_considered[{index}]"
    article_url = _nonempty(
        candidate.get("task_article_url"),
        f"{prefix}.task_article_url",
        maximum_length=500,
    )
    slug = _article_slug(article_url, f"{prefix}.task_article_url")
    subject_id = _nonempty(
        candidate.get("decision_subject_id"),
        f"{prefix}.decision_subject_id",
        maximum_length=200,
    )
    assert subject_id == slug, f"{prefix}.decision_subject_id must match the URL slug"
    return {
        "decision_subject_id": subject_id,
        "decision_subject_label": _nonempty(
            candidate.get("decision_subject_label"),
            f"{prefix}.decision_subject_label",
            maximum_length=300,
        ),
        "task_article_url": article_url,
        "task_topic_focus": _nonempty(
            candidate.get("task_topic_focus"),
            f"{prefix}.task_topic_focus",
            maximum_length=500,
        ),
        "task_relevance_note": _nonempty(
            candidate.get("task_relevance_note"),
            f"{prefix}.task_relevance_note",
            maximum_length=1200,
        ),
    }


def _navigation_path_type(exploration_style: str, used_search: bool | None) -> str:
    if exploration_style == "compared_multiple":
        return "compare_then_commit"
    if used_search is True:
        return "search_driven"
    return "browse_driven"


def _goal_component(
    *,
    key: str,
    label: str,
    status: str,
    evidence: str,
) -> dict[str, object]:
    return {
        "key": f"goal_component.{key}",
        "label": label,
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": key,
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": label,
            },
            {
                "key": "goal_component_status",
                "label": "Goal component status",
                "role": "primary",
                "kind": "categorical",
                "value": status,
            },
            {
                "key": "goal_component_weight",
                "label": "Goal component weight",
                "role": "score",
                "kind": "numerical",
                "value": GOAL_COMPONENT_WEIGHT,
            },
            {
                "key": "goal_component_required",
                "label": "Goal component required",
                "role": "evidence",
                "kind": "categorical",
                "value": "true",
            },
            {
                "key": "goal_component_evidence",
                "label": "Goal component evidence",
                "role": "explanation",
                "kind": "textual",
                "value": evidence,
            },
        ],
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
    assert isinstance(data, dict), "symptom_resource_choice.json root must be an object"
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

    overall = data.get("overallExperienceRating")
    assert isinstance(overall, (int, float)), "overallExperienceRating must be numeric"
    overall = int(round(float(overall)))
    assert 1 <= overall <= 10, "overallExperienceRating must be between 1 and 10"

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
            assert isinstance(value, (int, float)), f"{source_key} must be numeric"
            value = int(round(float(value)))
            assert 1 <= value <= 10, f"{source_key} must be between 1 and 10"
            payload[target_key] = value

    clarity = data.get("clarityOfNextStep")
    if clarity is not None:
        assert isinstance(clarity, bool), "clarityOfNextStep must be boolean"
        payload["clarity_of_next_step"] = "true" if clarity else "false"

    literacy = data.get("taskHealthLiteracyFit")
    if literacy is not None:
        assert literacy in SATISFACTION_BUCKETS, (
            "taskHealthLiteracyFit must use a supported bucket"
        )
        payload["task_health_literacy_fit"] = literacy

    return payload


def _execution_contexts(
    *,
    subject_id: str,
    subject_label: str,
    candidate_count: int,
    exploration_style: str,
    used_search: bool | None,
) -> list[dict[str, object]]:
    navigation_path_type = _navigation_path_type(exploration_style, used_search)
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
                        f"The persona selected {subject_label} after recording "
                        f"{candidate_count} distinct WebMD article candidates."
                    ),
                },
                {
                    "key": "completion_evidence",
                    "label": "Completion evidence",
                    "role": "evidence",
                    "kind": "textual",
                    "value": (
                        f"Saved {OUTPUT.name} with decision subject {subject_id} and "
                        f"{candidate_count} validated candidate records."
                    ),
                },
            ],
        },
        _goal_component(
            key="artifact_present",
            label="Output artifact saved",
            status="passed",
            evidence=f"{OUTPUT.name} was present at verification time.",
        ),
        _goal_component(
            key="schema_valid",
            label="Required fields and enums",
            status="passed",
            evidence="All required decision, process, and task-specific fields validated.",
        ),
        _goal_component(
            key="comparison_breadth",
            label="Compared multiple articles",
            status="passed",
            evidence=(
                f"Recorded {candidate_count} distinct WebMD article candidates "
                f"(minimum {MIN_CANDIDATES})."
            ),
        ),
        _goal_component(
            key="selection_consistent",
            label="Selected row matches choice",
            status="passed",
            evidence="Selected article appears exactly once in task_options_considered.",
        ),
        _goal_component(
            key="source_fidelity",
            label="WebMD source fidelity",
            status="passed",
            evidence="All recorded article URLs use https://www.webmd.com/ article paths.",
        ),
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
                    "label": "Artifact subject id",
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
                        "The selected article metadata is internally consistent with "
                        "the candidate list and WebMD URL rules."
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
                    "value": navigation_path_type,
                },
                {
                    "key": "page_count_visited",
                    "label": "Page count visited",
                    "role": "score",
                    "kind": "numerical",
                    "value": candidate_count,
                },
                *(
                    [
                        {
                            "key": "used_search",
                            "label": "Used search",
                            "role": "evidence",
                            "kind": "categorical",
                            "value": "true" if used_search else "false",
                        }
                    ]
                    if used_search is not None
                    else []
                ),
                {
                    "key": "web_interaction_notes",
                    "label": "Web interaction notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The submission records a "
                        f"{navigation_path_type.replace('_', ' ')} path across "
                        f"{candidate_count} distinct WebMD article candidates."
                    ),
                },
            ],
        },
        {
            "key": "side_effects.primary",
            "label": "Side effects",
            "contextType": "side_effects",
            "facets": [
                {
                    "key": "collateral_damage_present",
                    "label": "Collateral damage present",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "false",
                },
                {
                    "key": "blocking_side_effect_present",
                    "label": "Blocking side effect present",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "false",
                },
                {
                    "key": "damage_severity",
                    "label": "Damage severity",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "none",
                },
                {
                    "key": "damage_type_primary",
                    "label": "Primary damage type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "none",
                },
                {
                    "key": "unsafe_action_present",
                    "label": "Unsafe action present",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": "false",
                },
                {
                    "key": "side_effect_notes",
                    "label": "Side effect notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "No non-WebMD article URLs were recorded in the submission artifact."
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

    subject_id = _nonempty(
        data.get("decision_subject_id"),
        "decision_subject_id",
        maximum_length=200,
    )
    subject_label = _nonempty(
        data.get("decision_subject_label"),
        "decision_subject_label",
        maximum_length=300,
    )
    assert data.get("decision_outcome") == "selected", "decision_outcome must be selected"

    basis_primary = data.get("basis_primary")
    assert basis_primary in BASIS_VALUES, "basis_primary must use a supported bucket"
    basis_secondary = data.get("basis_secondary")
    if basis_secondary is not None:
        assert basis_secondary in BASIS_VALUES, "basis_secondary must use a supported bucket"
        assert basis_secondary != basis_primary, "basis_secondary must differ from basis_primary"

    exploration_style = data.get("exploration_style")
    assert exploration_style in EXPLORATION_STYLES, (
        "exploration_style must be compared_multiple or deep_research"
    )
    reason = _nonempty(data.get("reason"), "reason", maximum_length=2000)
    concern_summary = _nonempty(
        data.get("task_concern_summary"),
        "task_concern_summary",
        maximum_length=500,
    )

    assert data.get("task_source_url") == SOURCE_URL, f"task_source_url must be {SOURCE_URL}"
    selected_url = _nonempty(data.get("task_article_url"), "task_article_url", maximum_length=500)
    selected_slug = _article_slug(selected_url, "task_article_url")
    assert subject_id == selected_slug, "decision_subject_id must match task_article_url slug"

    used_search_raw = data.get("used_search")
    used_search: bool | None
    if used_search_raw is None:
        used_search = None
    else:
        assert isinstance(used_search_raw, bool), "used_search must be boolean when provided"
        used_search = used_search_raw

    raw_candidates = data.get("task_options_considered")
    assert isinstance(raw_candidates, list), "task_options_considered must be an array"
    assert len(raw_candidates) >= MIN_CANDIDATES, (
        f"task_options_considered must contain at least {MIN_CANDIDATES} articles"
    )
    candidates = [_validate_candidate(item, index) for index, item in enumerate(raw_candidates)]

    ids = [candidate["decision_subject_id"] for candidate in candidates]
    urls = [candidate["task_article_url"] for candidate in candidates]
    labels = [candidate["decision_subject_label"] for candidate in candidates]
    assert len(ids) == len(set(ids)), "candidate article IDs must be distinct"
    assert len(urls) == len(set(urls)), "candidate article URLs must be distinct"
    assert len(labels) == len(set(labels)), "candidate article titles must be distinct"

    selected_matches = [
        candidate for candidate in candidates if candidate["decision_subject_id"] == subject_id
    ]
    assert len(selected_matches) == 1, "selected article must appear exactly once in candidate list"
    selected = selected_matches[0]
    assert selected["decision_subject_label"] == subject_label, "selected article title must match"
    assert selected["task_article_url"] == selected_url, "selected article URL must match"
    topic_focus = selected["task_topic_focus"]

    source_artifacts: dict[str, object] = {"taskOutput": str(OUTPUT)}
    contexts = _execution_contexts(
        subject_id=subject_id,
        subject_label=subject_label,
        candidate_count=len(candidates),
        exploration_style=exploration_style,
        used_search=used_search,
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
            "key": "task_article_url",
            "label": "Selected article URL",
            "role": "evidence",
            "kind": "textual",
            "value": selected_url,
        },
        {
            "key": "task_concern_summary",
            "label": "Concern summary",
            "role": "evidence",
            "kind": "textual",
            "value": concern_summary,
        },
        {
            "key": "task_topic_focus",
            "label": "Selected article topic focus",
            "role": "evidence",
            "kind": "categorical",
            "value": topic_focus,
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

    process_facets: list[dict[str, object]] = [
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
            "value": len(candidates),
        },
        {
            "key": "comparison_notes",
            "label": "Comparison notes",
            "role": "explanation",
            "kind": "textual",
            "explainsFacetKey": "exploration_style",
            "value": "Compared: "
            + "; ".join(candidate["decision_subject_label"] for candidate in candidates),
        },
    ]
    if used_search is not None:
        process_facets.insert(
            2,
            {
                "key": "used_search",
                "label": "Used search",
                "role": "evidence",
                "kind": "categorical",
                "value": "true" if used_search else "false",
            },
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
                "facets": process_facets,
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
            ("trust_level", "Trust in WebMD content"),
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
                    "label": "Clarity of next step",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": feedback["clarity_of_next_step"],
                }
            )
        if "task_health_literacy_fit" in feedback:
            feedback_facets.append(
                {
                    "key": "task_health_literacy_fit",
                    "label": "Health literacy fit",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": feedback["task_health_literacy_fit"],
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

    required_artifacts = [OUTPUT.name]
    if feedback is not None:
        required_artifacts.append(USER_FEEDBACK.name)

    _write_structured_output(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "web",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": required_artifacts,
                "missingArtifacts": [],
            },
            "sourceArtifacts": source_artifacts,
            "contexts": contexts,
        }
    )

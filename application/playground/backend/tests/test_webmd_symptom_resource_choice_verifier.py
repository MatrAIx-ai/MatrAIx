from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
TASK_DIR = REPO_ROOT / "application" / "tasks" / "web-webmd_symptom-resource-choice"
TESTS_DIR = TASK_DIR / "tests"


def _load_verifier_module(output_dir: Path, verifier_dir: Path):
    os.environ["HARBOR_VERIFIER_DIR"] = str(verifier_dir)
    spec = importlib.util.spec_from_file_location(
        "webmd_test_state",
        TESTS_DIR / "test_state.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUTPUT = output_dir / "symptom_resource_choice.json"
    module.USER_FEEDBACK = output_dir / "user_feedback.json"
    return module


def _write_valid_artifacts(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "symptom_resource_choice.json").write_text(
        json.dumps(
            {
                "decision_subject_id": "migraines-migraine-guide",
                "decision_subject_label": "Migraine Guide",
                "decision_outcome": "selected",
                "basis_primary": "fit",
                "basis_secondary": "trust",
                "exploration_style": "compared_multiple",
                "reason": (
                    "This article best matched my concern because it explained migraine "
                    "patterns and when to seek care without feeling alarmist."
                ),
                "task_concern_summary": (
                    "I wanted to understand whether my recurring headaches could be migraines."
                ),
                "task_article_url": "https://www.webmd.com/migraines/migraine-guide",
                "task_source_url": "https://www.webmd.com/",
                "used_search": True,
                "task_options_considered": [
                    {
                        "decision_subject_id": "migraines-migraine-guide",
                        "decision_subject_label": "Migraine Guide",
                        "task_article_url": "https://www.webmd.com/migraines/migraine-guide",
                        "task_topic_focus": "Symptoms and when to seek care",
                        "task_relevance_note": "Focused on migraine patterns similar to mine.",
                    },
                    {
                        "decision_subject_id": "pain-management-guide-headache-basics",
                        "decision_subject_label": "Headache Basics",
                        "task_article_url": "https://www.webmd.com/pain-management/guide/headache-basics",
                        "task_topic_focus": "General headache overview",
                        "task_relevance_note": "Useful baseline but less specific.",
                    },
                    {
                        "decision_subject_id": "balance-stress-management-stress-symptoms-effects-of-stress-on-the-body",
                        "decision_subject_label": "Stress Symptoms",
                        "task_article_url": "https://www.webmd.com/balance/stress-management/stress-symptoms-effects_of-stress-on-the-body",
                        "task_topic_focus": "Stress effects on the body",
                        "task_relevance_note": "Plausible stress-related article.",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "user_feedback.json").write_text(
        json.dumps(
            {
                "needConstraintSatisfaction": "yes",
                "personalPreferenceSatisfaction": "partially",
                "overallExperienceRating": 8,
                "reason": "The comparison helped, though some pages felt dense.",
                "trustLevel": 7,
                "effortRating": 4,
                "clarityOfNextStep": True,
                "taskHealthLiteracyFit": "yes",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_webmd_verifier_accepts_valid_submission(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    verifier_dir = tmp_path / "verifier"
    _write_valid_artifacts(output_dir)
    module = _load_verifier_module(output_dir, verifier_dir)

    module.test_output_exists()
    module.test_output_schema()

    structured = json.loads((verifier_dir / "structured_output.json").read_text(encoding="utf-8"))
    context_types = {context["contextType"] for context in structured["contexts"]}
    assert {
        "task_outcome",
        "goal_component",
        "decision",
        "decision_process",
        "web_interaction",
        "web_artifact",
        "user_feedback",
        "side_effects",
    }.issubset(context_types)


def test_webmd_verifier_rejects_non_webmd_url(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    verifier_dir = tmp_path / "verifier"
    _write_valid_artifacts(output_dir)
    payload = json.loads((output_dir / "symptom_resource_choice.json").read_text(encoding="utf-8"))
    payload["task_article_url"] = "https://example.com/not-webmd"
    payload["task_options_considered"][0]["task_article_url"] = payload["task_article_url"]
    (output_dir / "symptom_resource_choice.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    module = _load_verifier_module(output_dir, verifier_dir)

    with pytest.raises(AssertionError, match="www.webmd.com"):
        module.test_output_schema()

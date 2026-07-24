"""Regression: WebMD decision artifacts must render in Playground trial debrief."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.service.harbor_trial_debrief import _resolve_web_eval_task, map_trial_debrief
from backend.service.web_types import WebEvalTask

REPO_ROOT = Path(__file__).resolve().parents[4]
JOB = "web-webmd-symptom-resource-choice-batch-n6"


@pytest.mark.parametrize(
    "trial_name",
    [
        "web-webmd_symptom-resource-choic__DjTZorJ",
        "web-webmd_symptom-resource-choic__V6fEQfF",
    ],
)
def test_webmd_trial_maps_web_result_from_decision_artifact(trial_name: str) -> None:
    trial_dir = REPO_ROOT / "jobs" / JOB / trial_name
    if not trial_dir.is_dir():
        pytest.skip("batch job artifacts not present locally")

    debrief = map_trial_debrief(
        repo_root=REPO_ROOT,
        jobs_dir=REPO_ROOT / "jobs",
        job_name=JOB,
        trial_name=trial_name,
    )

    assert debrief["applicationType"] == "web"
    web_result = debrief.get("webResult")
    assert web_result is not None, debrief.keys()
    assert web_result["selectedProductId"] == "heart-disease-what-causes-heart-palpitations"
    assert "Heart Palpitations" in web_result["selectedProductName"]


def test_resolve_web_eval_task_uses_on_disk_artifact_when_registry_default_is_wrong(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    trial_dir = repo / "jobs" / "job" / "trial"
    output = trial_dir / "artifacts" / "app" / "output"
    output.mkdir(parents=True)
    (output / "symptom_resource_choice.json").write_text(
        json.dumps(
            {
                "decision_subject_id": "heart-disease-what-causes-heart-palpitations",
                "decision_subject_label": "Heart Palpitations",
                "decision_outcome": "selected",
                "reason": "This article matched my concern and next-step needs.",
            }
        ),
        encoding="utf-8",
    )
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": "application/tasks/web-webmd_symptom-resource-choice"}}),
        encoding="utf-8",
    )

    stale_task = WebEvalTask(
        id="web-webmd-symptom-resource-choice",
        title="WebMD",
        site_name="WebMD",
        site_url="https://www.webmd.com/",
        task_path="application/tasks/web-webmd_symptom-resource-choice",
        description="test",
        output_artifact="web_result.json",
    )

    import backend.service.web_tasks as web_tasks_module

    original = web_tasks_module.list_web_eval_tasks
    web_tasks_module.list_web_eval_tasks = lambda: [stale_task]
    try:
        resolved = _resolve_web_eval_task(repo, trial_dir, output)
    finally:
        web_tasks_module.list_web_eval_tasks = original

    assert resolved.output_artifact == "symptom_resource_choice.json"

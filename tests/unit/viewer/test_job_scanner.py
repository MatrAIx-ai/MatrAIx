from __future__ import annotations

import json
from pathlib import Path

from harbor.viewer.scanner import JobScanner


def _write_job(tmp_path: Path, job_name: str, *, n_total_trials: int = 1) -> Path:
    job_dir = tmp_path / job_name
    job_dir.mkdir()
    (job_dir / "config.json").write_text(
        json.dumps({"job_name": job_name, "jobs_dir": "jobs"})
    )
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "started_at": "2026-01-01T00:00:00",
                "n_total_trials": n_total_trials,
                "stats": {
                    "n_completed_trials": n_total_trials,
                    "n_errored_trials": 0,
                    "n_running_trials": 0,
                    "n_pending_trials": 0,
                    "n_cancelled_trials": 0,
                    "n_retries": 0,
                    "evals": {},
                },
            }
        )
    )
    return job_dir


def _write_trial(job_dir: Path, trial_name: str) -> Path:
    trial_dir = job_dir / trial_name
    trial_dir.mkdir()
    (trial_dir / "agent").mkdir()
    (trial_dir / "artifacts").mkdir()
    (trial_dir / "verifier").mkdir()
    (trial_dir / "config.json").write_text(
        json.dumps({"trial_name": trial_name, "trials_dir": str(job_dir)})
    )
    (trial_dir / "result.json").write_text(
        json.dumps(
            {
                "id": "00000000-0000-4000-8000-000000000002",
                "task_name": "demo-task",
                "trial_name": trial_name,
                "started_at": "2026-01-01T00:00:00",
                "finished_at": "2026-01-01T00:01:00",
                "agent_info": {
                    "name": "oracle",
                    "version": "1.0.0",
                    "model_info": None,
                },
                "agent_result": None,
                "verifier_result": {"rewards": {"reward": 1.0}},
                "exception_info": None,
            }
        )
    )
    return trial_dir


def test_list_jobs_from_jobs_parent_lists_job_dirs_only(tmp_path: Path) -> None:
    job_dir = _write_job(tmp_path, "demo-job")
    _write_trial(job_dir, "demo-task__trial1")

    scanner = JobScanner(tmp_path)
    assert scanner.list_jobs() == ["demo-job"]
    assert scanner.list_trials("demo-job") == ["demo-task__trial1"]


def test_list_jobs_when_viewer_root_is_single_job_dir(tmp_path: Path) -> None:
    job_dir = _write_job(tmp_path, "appSim-demo-cu-ios-p0042")
    _write_trial(job_dir, "example-computer-use-ios_notific__JBFKrsW")

    scanner = JobScanner(job_dir)
    assert scanner.list_jobs() == ["appSim-demo-cu-ios-p0042"]
    assert scanner.list_trials("appSim-demo-cu-ios-p0042") == [
        "example-computer-use-ios_notific__JBFKrsW"
    ]
    assert scanner.get_job_result("appSim-demo-cu-ios-p0042") is not None


def test_resolve_job_name_maps_trial_slug_to_parent_job(tmp_path: Path) -> None:
    job_dir = _write_job(tmp_path, "appSim-demo-cu-ios-p0042")
    trial_name = "example-computer-use-ios_notific__JBFKrsW"
    _write_trial(job_dir, trial_name)

    scanner = JobScanner(job_dir)
    assert scanner.resolve_job_name(trial_name) == "appSim-demo-cu-ios-p0042"
    assert scanner.list_trials(trial_name) == [trial_name]
    assert scanner.get_job_result(trial_name) is not None

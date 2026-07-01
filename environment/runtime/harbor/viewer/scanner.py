"""Scanner for discovering jobs and trials in a folder."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from harbor.models.job.config import JobConfig
from harbor.models.job.result import JobResult
from harbor.models.trial.result import TrialResult

logger = logging.getLogger(__name__)


class JobScanner:
    """Scans a folder for job and trial data."""

    def __init__(self, jobs_dir: Path):
        self.jobs_dir = jobs_dir

    @staticmethod
    def _read_result_json(path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _is_job_root(self, path: Path) -> bool:
        payload = self._read_result_json(path / "result.json")
        if payload is not None:
            return "n_total_trials" in payload
        config_path = path / "config.json"
        if not config_path.exists():
            return False
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            return False
        if not isinstance(config, dict):
            return False
        return "job_name" in config and "trial_name" not in config

    def _is_trial_dir(self, path: Path) -> bool:
        payload = self._read_result_json(path / "result.json")
        if payload is not None:
            return "trial_name" in payload
        config_path = path / "config.json"
        if not config_path.exists():
            return False
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            return False
        return isinstance(config, dict) and "trial_name" in config

    def _resolve_job_dir(self, job_name: str) -> Path:
        job_name = self.resolve_job_name(job_name)
        if self._is_job_root(self.jobs_dir) and job_name == self.jobs_dir.name:
            return self.jobs_dir
        return self.jobs_dir / job_name

    def resolve_job_name(self, job_name: str) -> str:
        """Map a trial folder name to its parent job when viewing one job directory."""
        if not self._is_job_root(self.jobs_dir):
            return job_name
        if job_name == self.jobs_dir.name:
            return job_name
        trial_path = self.jobs_dir / job_name
        if self._is_trial_dir(trial_path):
            return self.jobs_dir.name
        return job_name

    def resolve_trial_name(self, job_name: str, trial_name: str | None = None) -> str | None:
        """When the URL uses a trial folder as the job slug, recover the trial name."""
        if trial_name is not None:
            return trial_name
        if not self._is_job_root(self.jobs_dir):
            return None
        if job_name == self.jobs_dir.name:
            return None
        trial_path = self.jobs_dir / job_name
        if self._is_trial_dir(trial_path):
            return job_name
        return None

    def list_jobs(self) -> list[str]:
        """List all job names in the jobs folder."""
        if not self.jobs_dir.exists():
            return []
        if self._is_job_root(self.jobs_dir):
            return [self.jobs_dir.name]
        return sorted(
            [
                child.name
                for child in self.jobs_dir.iterdir()
                if child.is_dir() and self._is_job_root(child)
            ],
            reverse=True,
        )

    def get_job_config(self, job_name: str) -> JobConfig | None:
        """Load job config from disk."""
        config_path = self._resolve_job_dir(job_name) / "config.json"
        if not config_path.exists():
            return None
        try:
            return JobConfig.model_validate_json(config_path.read_text())
        except Exception:
            logger.warning("Failed to parse job config for %s", job_name)
            return None

    def get_job_result(self, job_name: str) -> JobResult | None:
        """Load job result from disk."""
        result_path = self._resolve_job_dir(job_name) / "result.json"
        if not result_path.exists():
            return None
        try:
            return JobResult.model_validate_json(result_path.read_text())
        except Exception:
            logger.warning("Failed to parse job result for %s", job_name)
            return None

    def list_trials(self, job_name: str) -> list[str]:
        """List all trial names in a job folder."""
        job_dir = self._resolve_job_dir(job_name)
        if not job_dir.exists():
            return []
        return sorted(
            [
                child.name
                for child in job_dir.iterdir()
                if child.is_dir() and self._is_trial_dir(child)
            ]
        )

    def get_trial_result(self, job_name: str, trial_name: str) -> TrialResult | None:
        """Load trial result from disk."""
        result_path = self._resolve_job_dir(job_name) / trial_name / "result.json"
        if not result_path.exists():
            return None
        try:
            return TrialResult.model_validate_json(result_path.read_text())
        except Exception:
            logger.warning(
                "Failed to parse trial result for %s/%s", job_name, trial_name
            )
            return None

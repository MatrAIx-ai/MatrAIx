"""BenchFlow-backed web evaluation runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from environment.integrations.persona_eval.benchflow.client import BenchFlowClient
from environment.integrations.persona_eval.local.survey_eval import persona_system_prompt
from environment.integrations.persona_eval.local.web_eval import build_web_task_prompt
from backend.service.web_types import (
    WebEvalConfig,
    WebEvalResult,
    WebEvalResultArtifact,
    WebEvalTask,
    WebTrace,
)
from persona_eval.types import Persona


class BenchFlowWebEvalRunner:
    """Run a web task through a BenchFlow-hosted browser/WebArena agent."""

    def __init__(self, *, client: BenchFlowClient | None = None) -> None:
        self.client = client or BenchFlowClient()

    def __call__(
        self,
        persona: Persona,
        task: WebEvalTask,
        config: WebEvalConfig | None = None,
        *,
        created_at: str,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> WebEvalResult:
        config = _benchflow_config(config)

        def emit(event: dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        prompts = {
            "personaPrompt": persona_system_prompt(persona),
            "harborPrompt": persona_system_prompt(persona),
            "taskPrompt": build_web_task_prompt(task),
        }
        emit({"type": "prompts", "prompts": dict(prompts)})
        emit({"type": "phase", "phase": "benchflow_starting"})
        run = self.client.create_run(
            task_type="web",
            payload={
                "persona": persona.to_dict(),
                "task": task.to_dict(),
                "config": config.to_dict(),
                "prompts": dict(prompts),
            },
        )
        emit({"type": "phase", "phase": "benchflow_running", "runId": run.id})
        completed = self.client.wait_for_run(run.id)
        emit({"type": "phase", "phase": "benchflow_collecting", "runId": completed.id})
        web_result = self._result_artifact(completed.id, task)
        trace = self.client.get_artifact(completed.id, "trace.json")
        screenshots_dir = self._optional_artifact(completed.id, "screenshots_dir")
        if not isinstance(web_result, dict):
            raise ValueError("BenchFlow web_result.json artifact must be an object")
        if not isinstance(trace, dict):
            raise ValueError("BenchFlow trace.json artifact must be an object")
        result = WebEvalResult(
            config=config,
            persona=persona,
            task=task,
            web_result=WebEvalResultArtifact.from_dict(
                _normalize_web_result(web_result),
                created_at=created_at,
            ),
            trace=WebTrace(
                events=[dict(e) for e in trace.get("events") or [] if isinstance(e, dict)],
                raw=dict(trace.get("raw") or trace),
                screenshots_dir=_local_screenshots_dir(screenshots_dir),
            ),
            created_at=created_at,
            prompts=dict(prompts),
        )
        emit({"type": "done", "result": result.to_dict()})
        return result

    def _optional_artifact(self, run_id: str, name: str) -> Any:
        try:
            return self.client.get_artifact(run_id, name)
        except Exception:  # noqa: BLE001 - optional artifact
            return None

    def _result_artifact(self, run_id: str, task: WebEvalTask) -> Any:
        artifact_name = task.output_artifact or "web_result.json"
        result = self._optional_artifact(run_id, artifact_name)
        if isinstance(result, dict):
            return result
        if artifact_name != "web_result.json":
            return self.client.get_artifact(run_id, "web_result.json")
        return result


def _benchflow_config(config: WebEvalConfig | None) -> WebEvalConfig:
    config = config or WebEvalConfig()
    return WebEvalConfig(
        persona_model=config.persona_model,
        mode="benchflow_persona_web",
    )


def _normalize_web_result(web_result: dict[str, Any]) -> dict[str, Any]:
    data = dict(web_result)
    overall = data.get(
        "overall_quality",
        data.get("overallQuality", data.get("overall_experience_rating")),
    )
    if overall is None:
        overall = data.get("overallExperienceRating")
    if overall is not None:
        data["overall_quality"] = overall
    return data


def _local_screenshots_dir(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_dir() else None

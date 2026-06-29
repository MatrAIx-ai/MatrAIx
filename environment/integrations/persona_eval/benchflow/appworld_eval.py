"""BenchFlow-backed AppWorld evaluation runner."""

from __future__ import annotations

from typing import Any, Callable, Optional

from backend.service.appworld_types import (
    AppWorldEvalConfig,
    AppWorldEvalResult,
    AppWorldEvalTask,
    AppWorldResultArtifact,
    AppWorldTrace,
)
from environment.integrations.persona_eval.benchflow.client import BenchFlowClient
from environment.integrations.persona_eval.local.appworld_eval import build_appworld_task_prompt
from environment.integrations.persona_eval.local.survey_eval import persona_system_prompt
from persona_eval.types import Persona


class BenchFlowAppWorldEvalRunner:
    """Run an AppWorld task through a BenchFlow-hosted agent."""

    def __init__(self, *, client: BenchFlowClient | None = None) -> None:
        self.client = client or BenchFlowClient()

    def __call__(
        self,
        persona: Persona,
        task: AppWorldEvalTask,
        config: Optional[AppWorldEvalConfig] = None,
        *,
        created_at: str,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> AppWorldEvalResult:
        config = _benchflow_config(config)

        def emit(event: dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        prompts = {
            "personaPrompt": persona_system_prompt(persona),
            "harborPrompt": persona_system_prompt(persona),
            "taskPrompt": build_appworld_task_prompt(task),
        }
        emit({"type": "prompts", "prompts": dict(prompts)})
        emit({"type": "phase", "phase": "benchflow_starting"})
        run = self.client.create_run(
            task_type="appworld",
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
        artifact = self.client.get_artifact(completed.id, task.output_artifact)
        trace = self.client.get_artifact(completed.id, "trace.json")
        if not isinstance(artifact, dict):
            raise ValueError("BenchFlow appworld_result.json artifact must be an object")
        if not isinstance(trace, dict):
            raise ValueError("BenchFlow trace.json artifact must be an object")
        result = AppWorldEvalResult(
            config=config,
            persona=persona,
            task=task,
            appworld_result=AppWorldResultArtifact.from_dict(
                artifact,
                task=task,
                created_at=created_at,
            ),
            trace=AppWorldTrace(
                events=[dict(e) for e in trace.get("events") or [] if isinstance(e, dict)],
                raw=dict(trace.get("raw") or trace),
            ),
            created_at=created_at,
            prompts=dict(prompts),
        )
        emit({"type": "done", "result": result.to_dict()})
        return result


def _benchflow_config(config: AppWorldEvalConfig | None) -> AppWorldEvalConfig:
    config = config or AppWorldEvalConfig()
    return AppWorldEvalConfig(
        persona_model=config.persona_model,
        mode="benchflow_persona_appworld",
    )

"""BenchFlow-backed survey evaluation runner."""

from __future__ import annotations

from typing import Any, Callable

from environment.integrations.persona_eval.benchflow.client import BenchFlowClient
from environment.integrations.persona_eval.local.survey_eval import (
    build_survey_task_prompt,
    persona_system_prompt,
)
from backend.service.survey_types import (
    SurveyAnswer,
    SurveyEvalConfig,
    SurveyEvalResult,
    SurveyInstrument,
    SurveyMetrics,
    SurveyQuestion,
    TrajectoryEvent,
)
from persona_eval.types import Persona


class BenchFlowSurveyEvalRunner:
    """Run a survey through a BenchFlow-hosted persona agent."""

    def __init__(self, *, client: BenchFlowClient | None = None) -> None:
        self.client = client or BenchFlowClient()

    def __call__(
        self,
        persona: Persona,
        instrument: SurveyInstrument,
        config: SurveyEvalConfig | None = None,
        *,
        created_at: str,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> SurveyEvalResult:
        config = _benchflow_config(config)

        def emit(event: dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        prompts = {
            "personaPrompt": persona_system_prompt(persona),
            "harborPrompt": persona_system_prompt(persona),
            "taskPrompt": _benchflow_survey_task_prompt(
                instrument=instrument,
                require_rationale=config.require_rationale,
            ),
        }
        emit({"type": "prompts", "prompts": dict(prompts)})
        emit({"type": "phase", "phase": "benchflow_starting"})
        run = self.client.create_run(
            task_type="survey",
            payload={
                "persona": persona.to_dict(),
                "instrument": instrument.to_dict(),
                "config": config.to_dict(),
                "prompts": dict(prompts),
            },
        )
        emit({"type": "phase", "phase": "benchflow_running", "runId": run.id})
        completed = self.client.wait_for_run(run.id)
        emit({"type": "phase", "phase": "benchflow_collecting", "runId": completed.id})
        artifact = self.client.get_artifact(completed.id, "survey_result.json")
        if not isinstance(artifact, dict):
            raise ValueError("BenchFlow survey_result.json artifact must be an object")
        result = _survey_result_from_artifact(
            artifact,
            persona=persona,
            instrument=instrument,
            config=config,
            created_at=created_at,
            prompts=prompts,
        )
        emit({"type": "done", "result": result.to_dict()})
        return result


def _survey_result_from_artifact(
    artifact: dict[str, Any],
    *,
    persona: Persona,
    instrument: SurveyInstrument,
    config: SurveyEvalConfig,
    created_at: str,
    prompts: dict[str, str],
) -> SurveyEvalResult:
    _validate_instrument(artifact, instrument)
    answers = _normalize_answers(instrument, artifact.get("answers"))
    trajectory = _normalize_trajectory(artifact.get("trajectory"))
    return SurveyEvalResult(
        config=_benchflow_config(config),
        persona=persona,
        instrument=instrument,
        answers=answers,
        trajectory=trajectory,
        metrics=_metrics(answers, instrument),
        created_at=created_at,
        prompts=dict(prompts),
    )


def _benchflow_survey_task_prompt(
    *, instrument: SurveyInstrument, require_rationale: bool = True
) -> str:
    return "\n".join(
        [
            build_survey_task_prompt(
                instrument=instrument,
                require_rationale=require_rationale,
            ),
            "",
            "BenchFlow artifact requirement:",
            "Return `trajectory` alongside `answers`. Every trajectory event must",
            "include `timestamp`, `actor`, `action`, `context`, and `outcome`.",
            "Use a system `survey_started` event, question/answer events, and a",
            "system `survey_completed` event so PersonaEval can audit the hosted run.",
        ]
    )


def _validate_instrument(artifact: dict[str, Any], instrument: SurveyInstrument) -> None:
    raw = artifact.get("instrument")
    if not isinstance(raw, dict):
        return
    artifact_id = str(raw.get("id", "")).strip()
    if artifact_id and artifact_id != instrument.id:
        raise ValueError(
            "survey_result.instrument.id mismatch: expected {}, got {}".format(
                instrument.id,
                artifact_id,
            )
        )


def _normalize_answers(
    instrument: SurveyInstrument,
    raw_answers: Any,
) -> list[SurveyAnswer]:
    if not isinstance(raw_answers, list):
        raise ValueError("survey_result.answers must be a list")
    question_by_id = {question.id: question for question in instrument.questions}
    answers: list[SurveyAnswer] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_answers):
        if not isinstance(raw, dict):
            raise ValueError("survey_result.answers[{}] must be an object".format(index))
        question_id = str(raw.get("questionId", raw.get("question_id", ""))).strip()
        if question_id not in question_by_id:
            raise ValueError("unknown answer questionId: {}".format(question_id))
        if question_id in seen:
            raise ValueError("duplicate answer questionId: {}".format(question_id))
        seen.add(question_id)
        answers.append(_normalize_answer(question_by_id[question_id], raw))
    missing = [
        question.id
        for question in instrument.questions
        if question.required and question.id not in seen
    ]
    if missing:
        raise ValueError(
            "survey_result.answers missing required question ids: {}".format(
                ", ".join(missing)
            )
        )
    return answers


def _normalize_answer(question: SurveyQuestion, data: dict[str, Any]) -> SurveyAnswer:
    answer = SurveyAnswer.from_dict(data)
    if answer.question_id != question.id:
        raise ValueError(
            "answer questionId mismatch: expected {}, got {}".format(
                question.id,
                answer.question_id,
            )
        )
    if question.type == "likert":
        answer.value = _coerce_likert(question, answer.value)
    elif question.type == "single_choice":
        value = str(answer.value)
        if value not in question.options:
            raise ValueError(
                "answer {} must be one of {}".format(
                    question.id,
                    ", ".join(question.options),
                )
            )
        answer.value = value
    elif question.type == "multi_choice":
        if not isinstance(answer.value, list):
            raise ValueError("answer {} must be a list".format(question.id))
        values = [str(value) for value in answer.value]
        invalid = [value for value in values if value not in question.options]
        if invalid:
            raise ValueError(
                "answer {} includes invalid choices: {}".format(
                    question.id,
                    ", ".join(invalid),
                )
            )
        answer.value = values
    else:
        answer.value = str(answer.value or "")
        if question.required and not answer.value.strip():
            raise ValueError("answer {} must not be empty".format(question.id))
    return answer


def _coerce_likert(question: SurveyQuestion, value: Any) -> int | float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            "answer {} must be numeric for likert question".format(question.id)
        )
    if number < float(question.min_value) or number > float(question.max_value):
        raise ValueError(
            "answer {} must be between {} and {}".format(
                question.id,
                question.min_value,
                question.max_value,
            )
        )
    return int(number) if number.is_integer() else number


def _normalize_trajectory(raw_trajectory: Any) -> list[TrajectoryEvent]:
    if not isinstance(raw_trajectory, list) or not raw_trajectory:
        raise ValueError("survey_result.trajectory must be a non-empty list")
    events: list[TrajectoryEvent] = []
    for index, raw in enumerate(raw_trajectory):
        if not isinstance(raw, dict):
            raise ValueError(
                "survey_result.trajectory[{}] must be an object".format(index)
            )
        missing = [
            key
            for key in ("timestamp", "actor", "action", "context", "outcome")
            if key not in raw
        ]
        if missing:
            raise ValueError(
                "survey_result.trajectory[{}] missing keys: {}".format(
                    index,
                    ", ".join(missing),
                )
            )
        if not isinstance(raw.get("context"), dict):
            raise ValueError(
                "survey_result.trajectory[{}].context must be an object".format(index)
            )
        if not isinstance(raw.get("outcome"), dict):
            raise ValueError(
                "survey_result.trajectory[{}].outcome must be an object".format(index)
            )
        events.append(
            TrajectoryEvent(
                timestamp=str(raw.get("timestamp") or ""),
                actor=str(raw.get("actor") or ""),
                action=str(raw.get("action") or ""),
                context=dict(raw.get("context") or {}),
                outcome=dict(raw.get("outcome") or {}),
            )
        )
    return events


def _benchflow_config(config: SurveyEvalConfig | None) -> SurveyEvalConfig:
    config = config or SurveyEvalConfig()
    return SurveyEvalConfig(
        persona_model=config.persona_model,
        mode="benchflow_persona_survey",
        require_rationale=config.require_rationale,
    )


def _metrics(
    answers: list[SurveyAnswer], instrument: SurveyInstrument
) -> SurveyMetrics:
    question_types = {question.id: question.type for question in instrument.questions}
    likert_values: list[float] = []
    for answer in answers:
        if question_types.get(answer.question_id) != "likert":
            continue
        try:
            likert_values.append(float(answer.value))
        except (TypeError, ValueError):
            continue
    mean = round(sum(likert_values) / len(likert_values), 2) if likert_values else None
    return SurveyMetrics(
        num_questions=len(instrument.questions),
        num_answered=len(answers),
        mean_likert=mean,
    )

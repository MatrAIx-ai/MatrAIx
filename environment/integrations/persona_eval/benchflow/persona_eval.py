"""BenchFlow-backed chatbot persona-eval runner."""

from __future__ import annotations

from typing import Any, Callable

from environment.integrations.persona_eval.benchflow.client import BenchFlowClient
from environment.integrations.persona_eval.harbor.persona_eval import (
    HarborPersonaEvalResult,
    _coerce_overall,
    _coerce_score,
)
from environment.integrations.persona_eval.local.survey_eval import persona_system_prompt
from persona_eval.types import Persona, PersonaEvalConfig


class BenchFlowPersonaEvalRunner:
    """Run chatbot persona evaluation through a BenchFlow-hosted receiver agent."""

    def __init__(self, *, client: BenchFlowClient | None = None) -> None:
        self.client = client or BenchFlowClient()

    def __call__(
        self,
        session: Any,
        persona: Persona,
        sut_description: str,
        config: PersonaEvalConfig,
        _simulator: Any,
        *,
        created_at: str,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> HarborPersonaEvalResult:
        def emit(event: dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        prompts = {
            "personaPrompt": persona_system_prompt(persona),
            "harborPrompt": persona_system_prompt(persona),
            "taskPrompt": _chatbot_task_prompt(config, sut_description),
        }
        emit({"type": "prompts", "prompts": dict(prompts)})
        emit({"type": "phase", "phase": "benchflow_starting"})
        run = self.client.create_run(
            task_type="chatbot",
            payload={
                "persona": persona.to_dict(),
                "sutDescription": sut_description,
                "config": config.to_dict(),
                "maxTurns": config.max_turns,
                "prompts": dict(prompts),
            },
        )
        emit({"type": "phase", "phase": "benchflow_running", "runId": run.id})
        completed = self.client.wait_for_run(run.id)
        emit({"type": "phase", "phase": "benchflow_collecting", "runId": completed.id})
        transcript = self.client.get_artifact(completed.id, "transcript.json")
        application_result = self.client.get_artifact(
            completed.id,
            "application_result.json",
        )
        feedback = self._optional_artifact(completed.id, "user_feedback.json")
        if not isinstance(transcript, dict):
            raise ValueError("BenchFlow transcript.json artifact must be an object")
        if not isinstance(application_result, dict):
            raise ValueError("BenchFlow application_result.json artifact must be an object")
        recommended_items = _recommended_items(application_result)
        turns = _turn_views(transcript)
        result = BenchFlowPersonaEvalResult(
            config=config,
            persona=persona,
            sut_description=sut_description,
            turn_views=turns,
            recommended_items=recommended_items,
            questionnaire=_questionnaire(feedback if isinstance(feedback, dict) else {}),
            metric_scores={
                "turnsToRecommendation": application_result.get(
                    "turnsToRecommendation",
                    application_result.get("turnsToResult"),
                ),
                "numTurns": len(turns),
                "recommendedItemCount": len(recommended_items),
            },
            created_at=created_at,
            prompts=dict(prompts),
        )
        session.turns = list(turns)
        emit({"type": "done", "result": result.to_dict()})
        return result

    def _optional_artifact(self, run_id: str, name: str) -> Any:
        try:
            return self.client.get_artifact(run_id, name)
        except Exception:  # noqa: BLE001 - optional artifact
            return None


def _chatbot_task_prompt(config: PersonaEvalConfig, sut_description: str) -> str:
    return "\n".join(
        [
            "You are evaluating an interactive chatbot application as the assigned persona.",
            "",
            sut_description,
            "",
            "Application id: {}".format(config.application_id),
            "Application context: {}".format(config.application_context or config.domain),
            "Run for at most {} turns, then return transcript, application_result, and user_feedback artifacts.".format(
                config.max_turns
            ),
        ]
    )


def _turn_views(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    turns = transcript.get("turns")
    if isinstance(turns, list) and all(isinstance(t, dict) for t in turns):
        return [dict(t) for t in turns]
    messages = transcript.get("messages") or []
    if not isinstance(messages, list):
        return []
    views: list[dict[str, Any]] = []
    pending_user: str | None = None
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = str(message.get("content") or "")
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user is not None:
            views.append(
                {
                    "turnId": str(len(views)),
                    "conversationId": transcript.get("sessionId"),
                    "backend": "benchflow",
                    "userMessage": pending_user,
                    "assistantMessage": content,
                    "recommendedItems": [],
                    "groundedItems": [],
                    "plan": [],
                }
            )
            pending_user = None
    return views


def _recommended_items(application_result: dict[str, Any]) -> list[dict[str, Any]]:
    raw = application_result.get("groundedItems") or application_result.get(
        "recommendedItems"
    )
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("itemId", item.get("id", ""))).strip()
        if item_id:
            items.append({**item, "itemId": item_id})
    return items


class BenchFlowPersonaEvalResult(HarborPersonaEvalResult):
    """PersonaEval result that keeps BenchFlow app artifacts separate from turns."""

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        recommended = payload.get("recommendedItemIds")
        if isinstance(recommended, dict) and not recommended.get("final"):
            recommended["final"] = _recommended_item_ids(self.recommended_items)
        payload["recommendedItems"] = [dict(item) for item in self.recommended_items]
        return payload


def _recommended_item_ids(items: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for item in items:
        item_id = str(item.get("itemId", item.get("id", ""))).strip()
        if item_id:
            ids.append(item_id)
    return ids


def _questionnaire(feedback: dict[str, Any]) -> dict[str, Any]:
    if "constraintSatisfaction" in feedback or "overallRating" in feedback:
        return {
            "constraintSatisfaction": _coerce_score(
                feedback.get("constraintSatisfaction"), 3
            ),
            "constraintRationale": str(feedback.get("constraintRationale") or ""),
            "preferenceSatisfaction": _coerce_score(
                feedback.get("preferenceSatisfaction"), 3
            ),
            "preferenceRationale": str(feedback.get("preferenceRationale") or ""),
            "overallRating": _coerce_overall(feedback.get("overallRating")),
            "ratingReason": str(feedback.get("ratingReason") or ""),
            "askedUsefulClarifyingQuestions": bool(
                feedback.get("askedUsefulClarifyingQuestions", False)
            ),
            "clarifyingNotes": str(feedback.get("clarifyingNotes") or ""),
        }

    reason = str(feedback.get("reason") or "")
    return {
        "constraintSatisfaction": _coerce_score(
            feedback.get(
                "productNeedSatisfaction",
                feedback.get("productNeedConstraintSatisfaction"),
            ),
            3,
        ),
        "constraintRationale": reason,
        "preferenceSatisfaction": _coerce_score(
            feedback.get("personalPreferenceSatisfaction"), 3
        ),
        "preferenceRationale": reason,
        "overallRating": _coerce_overall(feedback.get("overallExperienceRating")),
        "ratingReason": reason,
        "askedUsefulClarifyingQuestions": bool(
            feedback.get("askedUsefulClarificationQuestions", False)
        ),
        "clarifyingNotes": reason,
    }

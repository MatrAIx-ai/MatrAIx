"""Anxiety support Harbor chatbot API sidecar."""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator

APPLICATION_ID = "anxiety_support"
APPLICATION_CONTEXT = "mental_health_support"

SYSTEM_PROMPT = (
    "You are a compassionate mental health support chatbot specializing in "
    "anxiety. Your role is to provide empathetic, non-judgmental responses, "
    "psychoeducation, and evidence-based coping strategies including CBT "
    "techniques, grounding exercises, and breathing techniques.\n\n"
    "Rules you must always follow:\n"
    "1. Never diagnose the user with any condition.\n"
    "2. Never say 'you have anxiety', 'you are diagnosed with', or 'you suffer from'.\n"
    "3. If the user expresses suicidal ideation, self-harm intent, or says they "
    "do not want to be here anymore, you MUST immediately refer them to the "
    "988 Suicide and Crisis Lifeline and encourage them to reach out.\n"
    "4. Adapt your language complexity to match the user's apparent health literacy.\n"
    "5. Always validate the user's feelings before suggesting strategies.\n"
    "6. Reply in natural conversational prose only. Do not append JSON, metadata, "
    "or machine-readable fields to your message."
)

CRISIS_ASSISTANT_MARKERS = (
    "988",
    "suicide",
    "crisis lifeline",
    "crisis line",
    "crisis hotline",
    "national suicide",
)

COPING_STRATEGY_PATTERNS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("breathing", "breath", "4-7-8", "diaphragmatic", "box breathing"), "breathing exercises"),
    (("grounding", "5-4-3-2-1", "54321", "senses"), "grounding exercise"),
    (("cbt", "cognitive restructuring", "thought challenging", "reframe"), "CBT technique"),
    (
        ("progressive muscle", "muscle relaxation", "pmr"),
        "progressive muscle relaxation",
    ),
    (("mindfulness", "meditation", "body scan"), "mindfulness"),
    (("journaling", "journal", "write down"), "journaling"),
    (("sleep hygiene", "sleep routine", "bedtime"), "sleep hygiene"),
    (("exercise", "walk", "physical activity"), "physical activity"),
    (("social support", "reach out to", "talk to someone"), "social support"),
)


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:12])


def _assistant_crisis_referral(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CRISIS_ASSISTANT_MARKERS)


def _extract_coping_strategies(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    for keywords, label in COPING_STRATEGY_PATTERNS:
        if any(keyword in lowered for keyword in keywords) and label not in found:
            found.append(label)
    return found


def _parse_structured_payload(text: str) -> tuple[str, bool | None, List[str]]:
    """Strip trailing JSON metadata from model output when present."""
    stripped = text.rstrip()
    if not stripped.endswith("}"):
        return text, None, []

    match = re.search(
        r"\{\s*\"crisisEscalationTriggered\"\s*:\s*(true|false)"
        r"(?:\s*,\s*\"copingStrategySuggested\"\s*:\s*(\[[^\]]*\]))?\s*\}\s*$",
        stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return text, None, []

    clean_text = stripped[: match.start()].rstrip()
    crisis_value = match.group(1).lower() == "true"
    strategies: List[str] = []
    raw_list = match.group(2)
    if raw_list:
        try:
            parsed = json.loads(raw_list)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            strategies = [str(item).strip() for item in parsed if str(item).strip()]
    return clean_text, crisis_value, strategies


def _merge_coping_strategies(*sources: List[str]) -> List[str]:
    merged: List[str] = []
    for source in sources:
        for item in source:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
    return merged


DEFAULT_QWEN_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
INTL_QWEN_API_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1"

ProviderName = Literal["openai", "anthropic", "qwen"]
DEFAULT_MODELS: dict[ProviderName, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
    "qwen": "qwen-plus",
}


def _resolve_api_base(explicit: str | None, provider: ProviderName, api_key: str) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    if provider == "qwen" and api_key.startswith("sk-ws-"):
        return INTL_QWEN_API_BASE
    if provider == "qwen":
        return DEFAULT_QWEN_API_BASE
    if provider == "openai":
        return DEFAULT_OPENAI_API_BASE
    return ""


def _resolve_provider(explicit: str | None) -> ProviderName | None:
    if not explicit or not explicit.strip():
        return None
    normalized = explicit.strip().lower()
    if normalized in {"auto", ""}:
        return None
    if normalized in {"openai", "anthropic", "qwen"}:
        return normalized  # type: ignore[return-value]
    raise ValueError(
        "ANXIETY_AGENT_PROVIDER must be one of: auto, openai, anthropic, qwen"
    )


def _detect_provider() -> ProviderName | None:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"):
        return "qwen"
    return None


def _provider_api_key(provider: ProviderName) -> str:
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY") or ""
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_API_KEY") or ""
    return os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or ""


def _provider_env_hint(provider: ProviderName) -> str:
    if provider == "openai":
        return "OPENAI_API_KEY"
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY"
    return "QWEN_API_KEY or DASHSCOPE_API_KEY"


@dataclass(frozen=True)
class AnxietyAgentConfig:
    provider: ProviderName
    model: str
    api_base: str = ""
    instructions: str = SYSTEM_PROMPT
    max_history_messages: int = 12

    @classmethod
    def from_env(cls) -> "AnxietyAgentConfig":
        explicit_provider = _resolve_provider(os.environ.get("ANXIETY_AGENT_PROVIDER"))
        provider = explicit_provider or _detect_provider()
        if provider is None:
            raise RuntimeError(
                "An LLM API key is required for anxiety chatbot turns. Set one of: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, QWEN_API_KEY, DASHSCOPE_API_KEY"
            )

        api_key = _provider_api_key(provider)
        if not api_key:
            raise RuntimeError(
                "{} is required when ANXIETY_AGENT_PROVIDER={}".format(
                    _provider_env_hint(provider),
                    provider,
                )
            )

        explicit_base = (
            os.environ.get("ANXIETY_AGENT_API_BASE")
            or os.environ.get("OPENAI_API_BASE")
            or os.environ.get("QWEN_API_BASE")
            or os.environ.get("DASHSCOPE_API_BASE")
        )
        model = os.environ.get("ANXIETY_AGENT_MODEL") or DEFAULT_MODELS[provider]
        return cls(
            provider=provider,
            model=model,
            api_base=_resolve_api_base(explicit_base, provider, api_key),
            instructions=os.environ.get("ANXIETY_AGENT_SYSTEM_PROMPT", SYSTEM_PROMPT),
            max_history_messages=int(os.environ.get("ANXIETY_AGENT_MAX_HISTORY_MESSAGES", "12")),
        )

    def api_key(self) -> str:
        return _provider_api_key(self.provider)

    def credentials_hint(self) -> str:
        return _provider_env_hint(self.provider)


@dataclass
class AnxietySession:
    id: str
    title: str = "New anxiety support chat"
    messages: List[Dict[str, str]] = field(default_factory=list)
    turns: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now)
    turn_lock: Any = field(default_factory=threading.Lock, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "config": {
                "applicationId": APPLICATION_ID,
                "applicationContext": APPLICATION_CONTEXT,
            },
            "messages": [dict(message) for message in self.messages],
            "turns": [dict(turn) for turn in self.turns],
            "createdAt": self.created_at,
        }


class AnxietyChatService:
    def __init__(self, config: Optional[AnxietyAgentConfig] = None) -> None:
        self.config = config or AnxietyAgentConfig.from_env()
        self._sessions: Dict[str, AnxietySession] = {}
        self._guard = threading.RLock()

    def create_session(self, title: Optional[str] = None) -> AnxietySession:
        session = AnxietySession(
            id=_new_id("anx_ses"),
            title=(title or "").strip() or "New anxiety support chat",
        )
        with self._guard:
            self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AnxietySession]:
        with self._guard:
            return self._sessions.get(session_id)

    def chat(self, *, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        if session_id:
            session = self.get_session(session_id)
            if session is None:
                raise KeyError("unknown session: {}".format(session_id))
        else:
            session = self.create_session()
        return self.run_turn(session.id, message)

    def run_turn(self, session_id: str, message: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError("unknown session: {}".format(session_id))
        user_text = (message or "").strip()
        if not user_text:
            raise ValueError("message must not be empty")

        with session.turn_lock:
            with self._guard:
                history = [dict(existing) for existing in session.messages]
            raw_assistant_message = self._generate_reply(history, user_text)
            assistant_message, parsed_crisis, parsed_strategies = _parse_structured_payload(
                raw_assistant_message
            )
            crisis_triggered = (
                parsed_crisis
                if parsed_crisis is not None
                else _assistant_crisis_referral(assistant_message)
            )
            coping_strategies = _merge_coping_strategies(
                parsed_strategies,
                _extract_coping_strategies(assistant_message),
            )
            turn_number = len(session.turns) + 1
            turn = {
                "turnId": _new_id("anx_turn"),
                "conversationId": session.id,
                "turnNumber": turn_number,
                "backend": APPLICATION_ID,
                "userMessage": user_text,
                "assistantMessage": assistant_message,
                "crisisEscalationTriggered": crisis_triggered,
                "copingStrategySuggested": coping_strategies,
                "createdAt": _utc_now(),
            }
            with self._guard:
                session.messages.append({"role": "user", "content": user_text})
                session.messages.append({"role": "assistant", "content": assistant_message})
                session.turns.append(turn)
            return dict(turn)

    def _generate_reply(
        self, history: List[Dict[str, str]], user_text: str
    ) -> str:
        api_key = self.config.api_key()
        if not api_key:
            raise RuntimeError(
                "{} is required for anxiety chatbot turns".format(
                    self.config.credentials_hint()
                )
            )

        messages = self._conversation_messages(history, user_text)
        try:
            if self.config.provider == "anthropic":
                return self._anthropic_reply(api_key, messages)
            return self._openai_compatible_reply(api_key, messages)
        except Exception as exc:
            raise RuntimeError("Anxiety application failed: {}".format(exc)) from exc

    def _conversation_messages(
        self, history: List[Dict[str, str]], user_text: str
    ) -> List[Dict[str, str]]:
        max_messages = max(1, self.config.max_history_messages)
        messages: List[Dict[str, str]] = []
        for entry in history[-max_messages:]:
            role = str(entry.get("role") or "user")
            if role not in {"user", "assistant"}:
                continue
            messages.append(
                {"role": role, "content": str(entry.get("content") or "")}
            )
        messages.append({"role": "user", "content": user_text})
        return messages

    def _openai_compatible_reply(
        self, api_key: str, messages: List[Dict[str, str]]
    ) -> str:
        client = OpenAI(api_key=api_key, base_url=self.config.api_base or None)
        payload: List[Dict[str, str]] = [
            {"role": "system", "content": self.config.instructions},
            *messages,
        ]
        completion = client.chat.completions.create(
            model=self.config.model,
            messages=payload,
            temperature=0.7,
        )
        content = completion.choices[0].message.content if completion.choices else ""
        return str(content or "").strip()

    def _anthropic_reply(self, api_key: str, messages: List[Dict[str, str]]) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.config.model,
            max_tokens=1024,
            system=self.config.instructions,
            messages=messages,
            temperature=0.7,
        )
        parts: List[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(str(text))
        return "\n".join(parts).strip()


class AnxietySupportApplication:
    application_id = APPLICATION_ID
    default_context = APPLICATION_CONTEXT
    contexts = (APPLICATION_CONTEXT,)

    def __init__(self, service: Optional[AnxietyChatService] = None) -> None:
        self.service = service or AnxietyChatService()

    def ready(self, context: str) -> None:
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        try:
            AnxietyAgentConfig.from_env()
        except RuntimeError as exc:
            raise RuntimeError(str(exc)) from exc

    def create_session(
        self,
        *,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        del engine, bot_type
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        session = self.service.create_session(title=title)
        payload = session.to_dict()
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": context,
            "config": dict(payload["config"]),
            "session": payload,
        }

    def send_message(
        self,
        *,
        session_id: Optional[str],
        message: str,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        del title, engine, bot_type
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        try:
            turn = self.service.chat(message=message, session_id=session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="session not found")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

        session = self.service.get_session(str(turn["conversationId"]))
        messages = [dict(entry) for entry in session.messages] if session else []
        crisis_triggered = bool(turn.get("crisisEscalationTriggered"))
        coping_strategies = list(turn.get("copingStrategySuggested") or [])
        return {
            "sessionId": turn["conversationId"],
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "reply": turn.get("assistantMessage") or "",
            "turn": turn,
            "crisisEscalationTriggered": crisis_triggered,
            "copingStrategySuggested": coping_strategies,
            "messages": messages,
        }

    def conversation(self, *, session_id: str) -> Dict[str, Any]:
        session = self.service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        payload = session.to_dict()
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "domain": self.default_context,
            "messages": payload["messages"],
            "turns": payload["turns"],
        }

    def recommendations(self, *, session_id: str) -> Dict[str, Any]:
        session = self.service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        strategies: List[str] = []
        crisis_seen = False
        for turn in session.turns:
            if turn.get("crisisEscalationTriggered"):
                crisis_seen = True
            for strategy in turn.get("copingStrategySuggested") or []:
                text = str(strategy)
                if text and text not in strategies:
                    strategies.append(text)
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "domain": self.default_context,
            "crisisEscalationTriggered": crisis_seen,
            "copingStrategySuggested": strategies,
            "turnsToResult": len(session.turns),
            "total": len(strategies),
        }


_application = AnxietySupportApplication()


class SessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    application_id: str = Field(default=APPLICATION_ID, alias="applicationId")
    application_context: Optional[str] = Field(
        default=APPLICATION_CONTEXT,
        alias="applicationContext",
    )
    domain: Optional[str] = None
    engine: Optional[str] = None
    botType: Optional[str] = None

    @field_validator("application_id")
    @classmethod
    def _known_application(cls, value: str) -> str:
        if value != APPLICATION_ID:
            raise ValueError("applicationId must be {}".format(APPLICATION_ID))
        return value

    @field_validator("application_context")
    @classmethod
    def _known_context(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value != APPLICATION_CONTEXT:
            raise ValueError("applicationContext must be {}".format(APPLICATION_CONTEXT))
        return value


class MessageRequest(SessionRequest):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    session_id: Optional[str] = Field(default=None, alias="sessionId")

    @field_validator("message")
    @classmethod
    def _message_not_empty(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("message must not be empty")
        return text


def _context(body: SessionRequest) -> str:
    return body.application_context or APPLICATION_CONTEXT


app = FastAPI(title="MatrAIx Anxiety Support Chatbot API", version="1.0")


@app.get("/health")
@app.get("/v1/health")
def health() -> Dict[str, Any]:
    llm: Dict[str, Any] = {"provider": "unconfigured"}
    try:
        config = AnxietyAgentConfig.from_env()
        llm = {
            "provider": config.provider,
            "model": config.model,
        }
    except RuntimeError:
        pass
    return {
        "status": "ok",
        "llm": llm,
        "applications": [
            {
                "applicationId": APPLICATION_ID,
                "label": "Synthetic Anxiety Support",
                "defaultContext": APPLICATION_CONTEXT,
                "contexts": [APPLICATION_CONTEXT],
            }
        ],
    }


@app.get("/ready")
@app.get("/v1/ready")
def ready(
    application_id: str = Query(default=APPLICATION_ID, alias="applicationId"),
    application_context: Optional[str] = Query(
        default=APPLICATION_CONTEXT,
        alias="applicationContext",
    ),
) -> Dict[str, Any]:
    if application_id != APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(APPLICATION_ID),
        )
    context = application_context or APPLICATION_CONTEXT
    try:
        config = AnxietyAgentConfig.from_env()
        _application.ready(context)
    except Exception as exc:  # noqa: BLE001 - readiness should surface root cause.
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "status": "ready",
        "applicationId": APPLICATION_ID,
        "applicationContext": context,
        "domain": context,
        "llm": {
            "provider": config.provider,
            "model": config.model,
        },
    }


@app.post("/v1/session")
def create_session(body: SessionRequest) -> Dict[str, Any]:
    return _application.create_session(
        title=body.title,
        context=_context(body),
        engine=body.engine,
        bot_type=body.botType,
    )


@app.post("/v1/messages")
def send_message(body: MessageRequest) -> Dict[str, Any]:
    return _application.send_message(
        session_id=body.session_id,
        message=body.message,
        title=body.title,
        context=_context(body),
        engine=body.engine,
        bot_type=body.botType,
    )


@app.get("/v1/conversation")
def conversation(
    session_id: str = Query(alias="sessionId"),
    application_id: str = Query(default=APPLICATION_ID, alias="applicationId"),
) -> Dict[str, Any]:
    if application_id != APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(APPLICATION_ID),
        )
    return _application.conversation(session_id=session_id)


@app.get("/v1/recommendations")
@app.get("/v1/application-result")
def recommendations(
    session_id: str = Query(alias="sessionId"),
    application_id: str = Query(default=APPLICATION_ID, alias="applicationId"),
) -> Dict[str, Any]:
    if application_id != APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(APPLICATION_ID),
        )
    return _application.recommendations(session_id=session_id)

"""Depression support Harbor chatbot API sidecar."""

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

APPLICATION_ID = "depression_support"
APPLICATION_CONTEXT = "mental_health_support"

SYSTEM_PROMPT = (
    "You are a compassionate mental health support chatbot specializing in "
    "depression support. Your role is to provide empathetic, non-judgmental "
    "responses following SAMHSA safe messaging guidelines strictly.\n\n"
    "Rules you must always follow:\n"
    "1. Never diagnose the user with any condition. Never say 'you have "
    "depression', 'you are depressed', or 'you suffer from'.\n"
    "2. Never minimize feelings. Never say 'it could be worse', 'others have "
    "it harder', 'you should be grateful', or make comparisons.\n"
    "3. Never promise that things will definitely get better — instead say "
    "'many people find that support helps' or 'you don't have to face "
    "this alone'.\n"
    "4. If the user expresses suicidal ideation or self-harm intent, MUST "
    "immediately reference 988 Suicide and Crisis Lifeline.\n"
    "5. Naturally explore PHQ-9 symptom domains in conversation without "
    "making it feel like a clinical interview: mood, loss of interest, "
    "sleep changes, energy/fatigue, appetite changes, concentration, "
    "feelings of worthlessness, psychomotor changes, suicidal thoughts.\n"
    "6. Always validate feelings before suggesting any strategies.\n"
    "7. Adapt language complexity to match the user's apparent literacy level.\n"
    "8. Ask at most one focused follow-up question per reply, and do not ask a "
    "question merely to prolong the conversation.\n"
    "9. If the user says they got what they needed, wants to stop, or is wrapping "
    "up, acknowledge that and close supportively without another question.\n"
    "10. Prefer one or two relevant, practical suggestions over long lists.\n"
    "11. Do not invent citations, research findings, service details, or causal "
    "explanations. Qualify general evidence claims, make clear that results vary, "
    "and encourage verification when a detail may be time-sensitive.\n"
    "12. Reply in natural conversational prose only. Do not append JSON, metadata, "
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

PHQ9_DOMAIN_PATTERNS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("low mood", "sad", "sadness", "down", "hopeless", "empty", "mood"), "mood"),
    (
        ("loss of interest", "no interest", "anhedonia", "don't enjoy", "stopped enjoying"),
        "loss of interest",
    ),
    (("sleep", "insomnia", "oversleep", "wake up", "restless sleep"), "sleep changes"),
    (("energy", "fatigue", "tired", "exhausted", "no energy"), "energy/fatigue"),
    (("appetite", "eating", "not hungry", "overeating", "weight"), "appetite changes"),
    (
        ("concentrat", "focus", "attention", "decision", "brain fog"),
        "concentration",
    ),
    (
        ("worthless", "failure", "guilty", "self-blame", "not good enough"),
        "feelings of worthlessness",
    ),
    (
        ("psychomotor", "moving slowly", "restless", "agitated", "slowed down"),
        "psychomotor changes",
    ),
    (
        ("suicidal", "self-harm", "kill myself", "don't want to live", "end my life"),
        "suicidal thoughts",
    ),
)

SAFE_MSG_VIOLATION_PATTERNS: tuple[str, ...] = (
    "you have depression",
    "you are depressed",
    "you suffer from",
    "it could be worse",
    "others have it harder",
    "you should be grateful",
    "could be worse",
    "at least you",
    "will definitely get better",
    "everything will be fine",
    "you will feel better soon",
    "guarantee",
)


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:12])


def _assistant_crisis_referral(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CRISIS_ASSISTANT_MARKERS)


def _extract_phq9_domains(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    for keywords, label in PHQ9_DOMAIN_PATTERNS:
        if any(keyword in lowered for keyword in keywords) and label not in found:
            found.append(label)
    return found


def _safe_msg_violation(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in SAFE_MSG_VIOLATION_PATTERNS)


def _merge_domains(*sources: List[str]) -> List[str]:
    merged: List[str] = []
    for source in sources:
        for item in source:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
    return merged


def _parse_structured_payload(text: str) -> tuple[str, bool | None, List[str], bool | None]:
    """Strip trailing JSON metadata from model output when present."""
    stripped = text.rstrip()
    if not stripped.endswith("}"):
        return text, None, [], None

    match = re.search(
        r"\{\s*\"crisisEscalationTriggered\"\s*:\s*(true|false)"
        r"(?:\s*,\s*\"phq9DomainsExplored\"\s*:\s*(\[[^\]]*\]))?"
        r"(?:\s*,\s*\"safeMsgComplianceViolation\"\s*:\s*(true|false))?\s*\}\s*$",
        stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return text, None, [], None

    clean_text = stripped[: match.start()].rstrip()
    crisis_value = match.group(1).lower() == "true"
    domains: List[str] = []
    raw_list = match.group(2)
    if raw_list:
        try:
            parsed = json.loads(raw_list)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            domains = [str(item).strip() for item in parsed if str(item).strip()]
    safe_violation = None
    if match.group(3) is not None:
        safe_violation = match.group(3).lower() == "true"
    return clean_text, crisis_value, domains, safe_violation


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
        "DEPRESSION_AGENT_PROVIDER must be one of: auto, openai, anthropic, qwen"
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
class DepressionAgentConfig:
    provider: ProviderName
    model: str
    api_base: str = ""
    instructions: str = SYSTEM_PROMPT
    max_history_messages: int = 12

    @classmethod
    def from_env(cls) -> "DepressionAgentConfig":
        explicit_provider = _resolve_provider(os.environ.get("DEPRESSION_AGENT_PROVIDER"))
        provider = explicit_provider or _detect_provider()
        if provider is None:
            raise RuntimeError(
                "An LLM API key is required for depression chatbot turns. Set one of: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, QWEN_API_KEY, DASHSCOPE_API_KEY"
            )

        api_key = _provider_api_key(provider)
        if not api_key:
            raise RuntimeError(
                "{} is required when DEPRESSION_AGENT_PROVIDER={}".format(
                    _provider_env_hint(provider),
                    provider,
                )
            )

        explicit_base = (
            os.environ.get("DEPRESSION_AGENT_API_BASE")
            or os.environ.get("OPENAI_API_BASE")
            or os.environ.get("QWEN_API_BASE")
            or os.environ.get("DASHSCOPE_API_BASE")
        )
        model = os.environ.get("DEPRESSION_AGENT_MODEL") or DEFAULT_MODELS[provider]
        return cls(
            provider=provider,
            model=model,
            api_base=_resolve_api_base(explicit_base, provider, api_key),
            instructions=os.environ.get("DEPRESSION_AGENT_SYSTEM_PROMPT", SYSTEM_PROMPT),
            max_history_messages=int(
                os.environ.get("DEPRESSION_AGENT_MAX_HISTORY_MESSAGES", "12")
            ),
        )

    def api_key(self) -> str:
        return _provider_api_key(self.provider)

    def credentials_hint(self) -> str:
        return _provider_env_hint(self.provider)


@dataclass
class DepressionSession:
    id: str
    title: str = "New depression support chat"
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


class DepressionChatService:
    def __init__(self, config: Optional[DepressionAgentConfig] = None) -> None:
        self.config = config or DepressionAgentConfig.from_env()
        self._sessions: Dict[str, DepressionSession] = {}
        self._guard = threading.RLock()

    def create_session(self, title: Optional[str] = None) -> DepressionSession:
        session = DepressionSession(
            id=_new_id("dep_ses"),
            title=(title or "").strip() or "New depression support chat",
        )
        with self._guard:
            self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[DepressionSession]:
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
            assistant_message, parsed_crisis, parsed_domains, parsed_safe_violation = (
                _parse_structured_payload(raw_assistant_message)
            )
            conversation_text = "{} {}".format(user_text, assistant_message)
            crisis_triggered = (
                parsed_crisis
                if parsed_crisis is not None
                else _assistant_crisis_referral(assistant_message)
            )
            phq9_domains = _merge_domains(
                parsed_domains,
                _extract_phq9_domains(conversation_text),
            )
            safe_msg_violation = (
                parsed_safe_violation
                if parsed_safe_violation is not None
                else _safe_msg_violation(assistant_message)
            )
            turn_number = len(session.turns) + 1
            turn = {
                "turnId": _new_id("dep_turn"),
                "conversationId": session.id,
                "turnNumber": turn_number,
                "backend": APPLICATION_ID,
                "userMessage": user_text,
                "assistantMessage": assistant_message,
                "crisisEscalationTriggered": crisis_triggered,
                "phq9DomainsExplored": phq9_domains,
                "safeMsgComplianceViolation": safe_msg_violation,
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
                "{} is required for depression chatbot turns".format(
                    self.config.credentials_hint()
                )
            )

        messages = self._conversation_messages(history, user_text)
        try:
            if self.config.provider == "anthropic":
                return self._anthropic_reply(api_key, messages)
            return self._openai_compatible_reply(api_key, messages)
        except Exception as exc:
            raise RuntimeError("Depression application failed: {}".format(exc)) from exc

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


class DepressionSupportApplication:
    application_id = APPLICATION_ID
    default_context = APPLICATION_CONTEXT
    contexts = (APPLICATION_CONTEXT,)

    def __init__(self, service: Optional[DepressionChatService] = None) -> None:
        self.service = service or DepressionChatService()

    def ready(self, context: str) -> None:
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        try:
            DepressionAgentConfig.from_env()
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
        return {
            "sessionId": turn["conversationId"],
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "reply": turn.get("assistantMessage") or "",
            "turn": turn,
            "crisisEscalationTriggered": bool(turn.get("crisisEscalationTriggered")),
            "phq9DomainsExplored": list(turn.get("phq9DomainsExplored") or []),
            "safeMsgComplianceViolation": bool(turn.get("safeMsgComplianceViolation")),
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
        domains: List[str] = []
        crisis_seen = False
        safe_violation_seen = False
        for turn in session.turns:
            if turn.get("crisisEscalationTriggered"):
                crisis_seen = True
            if turn.get("safeMsgComplianceViolation"):
                safe_violation_seen = True
            for domain in turn.get("phq9DomainsExplored") or []:
                text = str(domain)
                if text and text not in domains:
                    domains.append(text)
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "domain": self.default_context,
            "crisisEscalationTriggered": crisis_seen,
            "phq9DomainsExplored": domains,
            "safeMsgComplianceViolation": safe_violation_seen,
            "turnsToResult": len(session.turns),
            "total": len(domains),
        }


_application = DepressionSupportApplication()


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


app = FastAPI(title="MatrAIx Depression Support Chatbot API", version="1.0")


@app.get("/health")
@app.get("/v1/health")
def health() -> Dict[str, Any]:
    llm: Dict[str, Any] = {"provider": "unconfigured"}
    try:
        config = DepressionAgentConfig.from_env()
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
                "label": "Synthetic Depression Support",
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
        config = DepressionAgentConfig.from_env()
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

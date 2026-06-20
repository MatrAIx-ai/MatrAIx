# RecBot InteRecAgent Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal RecBot interface that calls an existing Microsoft RecAI/InteRecAgent backend and records each conversational turn without redefining InteRecAgent's native action contract.

**Architecture:** MatrAIx owns a thin provider boundary and a `RecBotTurnResult` envelope. The real recommendation behavior stays inside an external InteRecAgent environment, invoked through a subprocess bridge. Unit tests cover the provider contract and bridge payload handling; a local smoke script exercises the real InteRecAgent movie backend when the external RecAI checkout, resources, and OpenAI-compatible API are configured.

**Tech Stack:** Python standard library (`dataclasses`, `json`, `subprocess`, `unittest`), Microsoft RecAI/InteRecAgent as an external dependency, and existing normalized catalog docs under `applications/recommendation_chatbot_eval/`.

---

## File Structure

Create these files:

- `applications/recommendation_chatbot_eval/recbot/__init__.py`: public exports for the RecBot interface.
- `applications/recommendation_chatbot_eval/recbot/types.py`: serializable dataclasses for request, native action, trace, and turn result.
- `applications/recommendation_chatbot_eval/recbot/native_contract.py`: helpers for preserving/parsing InteRecAgent native output without classifying turns.
- `applications/recommendation_chatbot_eval/recbot/provider.py`: provider protocol plus subprocess-backed external command provider.
- `applications/recommendation_chatbot_eval/recbot/interecagent_bridge.py`: JSON stdin/stdout bridge that imports and calls existing RecAI/InteRecAgent code.
- `applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py`: opt-in local smoke test script for the movie backend.
- `applications/recommendation_chatbot_eval/tests/test_types.py`: unit tests for serialization and validation.
- `applications/recommendation_chatbot_eval/tests/test_native_contract.py`: unit tests for native output preservation and tool-plan extraction.
- `applications/recommendation_chatbot_eval/tests/test_provider.py`: unit tests for subprocess provider behavior.
- `applications/recommendation_chatbot_eval/tests/test_interecagent_bridge.py`: unit tests for bridge chat-history formatting and input validation.
- `applications/recommendation_chatbot_eval/INTERECAGENT_PROVIDER.md`: setup and invocation notes for using the external RecAI backend.

Modify these files:

- `applications/recommendation_chatbot_eval/README.md`: link the provider docs and smoke test.
- `applications/recommendation_chatbot_eval/LOCAL_MOVIE_TESTING.md`: add the movie RecBot smoke test command.

Testing command for all non-external tests:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

The real InteRecAgent smoke test is opt-in because it requires an external RecAI checkout, ready-to-run RecAI resources, and API credentials.

---

### Task 1: Core RecBot Turn Types

**Files:**
- Create: `applications/recommendation_chatbot_eval/recbot/__init__.py`
- Create: `applications/recommendation_chatbot_eval/recbot/types.py`
- Create: `applications/recommendation_chatbot_eval/tests/test_types.py`

- [ ] **Step 1: Write failing serialization tests**

Create `applications/recommendation_chatbot_eval/tests/test_types.py`:

```python
import unittest

from recbot.types import (
    ChatMessage,
    NativeAction,
    RecBotRequest,
    RecBotTrace,
    RecBotTurnResult,
)


class RecBotTypesTest(unittest.TestCase):
    def test_request_round_trip_keeps_messages_and_metadata(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=2,
            messages=[
                ChatMessage(role="user", content="Can you recommend a movie?"),
                ChatMessage(role="assistant", content="What mood do you want?"),
                ChatMessage(role="user", content="Something tense but not horror."),
            ],
            metadata={"domain": "movie"},
        )

        restored = RecBotRequest.from_dict(request.to_dict())

        self.assertEqual(restored.conversation_id, "episode_001")
        self.assertEqual(restored.turn_id, 2)
        self.assertEqual(restored.latest_user_message, "Something tense but not horror.")
        self.assertEqual(restored.metadata["domain"], "movie")

    def test_turn_result_round_trip_keeps_native_action_and_trace(self):
        result = RecBotTurnResult(
            backend="interecagent",
            conversation_id="episode_001",
            turn_id=3,
            user_message="Something tense but not horror.",
            assistant_message="I recommend Aurora Station.",
            native_action=NativeAction(raw="Action: ToolExecutor\nAction Input: []"),
            trace=RecBotTrace(
                raw_tool_plan=[{"tool_name": "RankingTool", "input": "preference"}],
                raw_tool_outputs="ranked candidates",
                recommended_item_ids=["cmu:54166"],
            ),
        )

        restored = RecBotTurnResult.from_dict(result.to_dict())

        self.assertEqual(restored.backend, "interecagent")
        self.assertEqual(restored.native_action.raw, "Action: ToolExecutor\nAction Input: []")
        self.assertEqual(restored.trace.recommended_item_ids, ["cmu:54166"])

    def test_invalid_role_is_rejected(self):
        with self.assertRaises(ValueError):
            ChatMessage(role="bot", content="hello")

    def test_request_without_user_message_is_rejected(self):
        with self.assertRaises(ValueError):
            RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="assistant", content="hello")],
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications/recommendation_chatbot_eval/tests/test_types.py -v
```

Expected: FAIL with an import error because `recbot.types` does not exist yet.

- [ ] **Step 3: Create the core type module**

Create `applications/recommendation_chatbot_eval/recbot/types.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_ROLES = {"system", "user", "assistant"}


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.role, "role")
        _require_non_empty_string(self.content, "content")
        if self.role not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ChatMessage":
        return cls(role=value["role"], content=value["content"])


@dataclass(frozen=True)
class NativeAction:
    raw: str
    raw_tool_plan: Any | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.raw, "raw")

    def to_dict(self) -> dict[str, Any]:
        return {"raw": self.raw, "raw_tool_plan": self.raw_tool_plan}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "NativeAction":
        return cls(raw=value["raw"], raw_tool_plan=value.get("raw_tool_plan"))


@dataclass(frozen=True)
class RecBotTrace:
    raw_tool_plan: Any | None = None
    raw_tool_outputs: Any | None = None
    recommended_item_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.recommended_item_ids, list):
            raise ValueError("recommended_item_ids must be a list")
        for item_id in self.recommended_item_ids:
            _require_non_empty_string(item_id, "recommended item id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_tool_plan": self.raw_tool_plan,
            "raw_tool_outputs": self.raw_tool_outputs,
            "recommended_item_ids": list(self.recommended_item_ids),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "RecBotTrace":
        if value is None:
            return cls()
        return cls(
            raw_tool_plan=value.get("raw_tool_plan"),
            raw_tool_outputs=value.get("raw_tool_outputs"),
            recommended_item_ids=list(value.get("recommended_item_ids", [])),
        )


@dataclass(frozen=True)
class RecBotRequest:
    conversation_id: str
    turn_id: int
    messages: list[ChatMessage]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty_string(self.conversation_id, "conversation_id")
        if not isinstance(self.turn_id, int) or self.turn_id < 0:
            raise ValueError("turn_id must be a non-negative integer")
        if not self.messages:
            raise ValueError("messages must contain at least one message")
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("messages must contain at least one user message")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")

    @property
    def latest_user_message(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        raise ValueError("messages must contain at least one user message")

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "turn_id": self.turn_id,
            "messages": [message.to_dict() for message in self.messages],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RecBotRequest":
        return cls(
            conversation_id=value["conversation_id"],
            turn_id=int(value["turn_id"]),
            messages=[ChatMessage.from_dict(message) for message in value["messages"]],
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(frozen=True)
class RecBotTurnResult:
    backend: str
    conversation_id: str
    turn_id: int
    user_message: str
    assistant_message: str
    native_action: NativeAction
    trace: RecBotTrace = field(default_factory=RecBotTrace)

    def __post_init__(self) -> None:
        _require_non_empty_string(self.backend, "backend")
        _require_non_empty_string(self.conversation_id, "conversation_id")
        _require_non_empty_string(self.user_message, "user_message")
        _require_non_empty_string(self.assistant_message, "assistant_message")
        if not isinstance(self.turn_id, int) or self.turn_id < 0:
            raise ValueError("turn_id must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "conversation_id": self.conversation_id,
            "turn_id": self.turn_id,
            "user_message": self.user_message,
            "assistant_message": self.assistant_message,
            "native_action": self.native_action.to_dict(),
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RecBotTurnResult":
        return cls(
            backend=value["backend"],
            conversation_id=value["conversation_id"],
            turn_id=int(value["turn_id"]),
            user_message=value["user_message"],
            assistant_message=value["assistant_message"],
            native_action=NativeAction.from_dict(value["native_action"]),
            trace=RecBotTrace.from_dict(value.get("trace")),
        )
```

Create `applications/recommendation_chatbot_eval/recbot/__init__.py`:

```python
from recbot.types import (
    ChatMessage,
    NativeAction,
    RecBotRequest,
    RecBotTrace,
    RecBotTurnResult,
)

__all__ = [
    "ChatMessage",
    "NativeAction",
    "RecBotRequest",
    "RecBotTrace",
    "RecBotTurnResult",
]
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications/recommendation_chatbot_eval/tests/test_types.py -v
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add applications/recommendation_chatbot_eval/recbot applications/recommendation_chatbot_eval/tests/test_types.py
git commit -m "feat: add recbot turn result types"
```

---

### Task 2: Native InteRecAgent Contract Helpers

**Files:**
- Create: `applications/recommendation_chatbot_eval/recbot/native_contract.py`
- Create: `applications/recommendation_chatbot_eval/tests/test_native_contract.py`

- [ ] **Step 1: Write failing tests for preserving native output**

Create `applications/recommendation_chatbot_eval/tests/test_native_contract.py`:

```python
import unittest

from recbot.native_contract import (
    assistant_message_from_native_output,
    build_native_action,
    extract_action_input,
    extract_final_answer,
)


class NativeContractTest(unittest.TestCase):
    def test_extract_final_answer(self):
        raw = "Question: Do I need tools?\nFinal Answer: What kind of movie mood do you want?"

        self.assertEqual(
            extract_final_answer(raw),
            "What kind of movie mood do you want?",
        )
        self.assertEqual(
            assistant_message_from_native_output(raw),
            "What kind of movie mood do you want?",
        )

    def test_extract_action_input(self):
        raw = (
            "Question: Do I need tools?\n"
            "Action: ToolExecutor\n"
            "Action Input: [{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]"
        )

        self.assertEqual(
            extract_action_input(raw),
            "[{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]",
        )

    def test_build_native_action_parses_json_plan_when_possible(self):
        raw = (
            "Action: ToolExecutor\n"
            "Action Input: [{\"tool_name\": \"MapTool\", \"input\": \"5\"}]"
        )

        native_action = build_native_action(raw)

        self.assertEqual(native_action.raw, raw)
        self.assertEqual(native_action.raw_tool_plan, [{"tool_name": "MapTool", "input": "5"}])

    def test_build_native_action_keeps_unparsed_plan_string(self):
        raw = "Action: ToolExecutor\nAction Input: not-json"

        native_action = build_native_action(raw)

        self.assertEqual(native_action.raw_tool_plan, "not-json")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications/recommendation_chatbot_eval/tests/test_native_contract.py -v
```

Expected: FAIL with an import error because `recbot.native_contract` does not exist yet.

- [ ] **Step 3: Implement native contract helpers**

Create `applications/recommendation_chatbot_eval/recbot/native_contract.py`:

```python
from __future__ import annotations

import ast
import json
import re
from typing import Any

from recbot.types import NativeAction


FINAL_ANSWER_RE = re.compile(r"Final Answer\s*:\s*(.*)", re.IGNORECASE | re.DOTALL)
ACTION_INPUT_RE = re.compile(
    r"Action\s*\d*\s*:\s*(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)


def extract_final_answer(raw_output: str) -> str | None:
    match = FINAL_ANSWER_RE.search(raw_output.strip())
    if not match:
        return None
    return match.group(1).strip()


def extract_action_input(raw_output: str) -> str | None:
    match = ACTION_INPUT_RE.search(raw_output.strip())
    if not match:
        return None
    return match.group(2).strip()


def parse_action_input(action_input: str) -> Any:
    try:
        return json.loads(action_input)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(action_input)
        except (SyntaxError, ValueError):
            return action_input


def build_native_action(raw_output: str) -> NativeAction:
    action_input = extract_action_input(raw_output)
    raw_tool_plan = parse_action_input(action_input) if action_input is not None else None
    return NativeAction(raw=raw_output.strip(), raw_tool_plan=raw_tool_plan)


def assistant_message_from_native_output(raw_output: str) -> str:
    final_answer = extract_final_answer(raw_output)
    if final_answer:
        return final_answer
    return raw_output.strip()
```

- [ ] **Step 4: Run all current tests**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add applications/recommendation_chatbot_eval/recbot/native_contract.py applications/recommendation_chatbot_eval/tests/test_native_contract.py
git commit -m "feat: preserve interecagent native action output"
```

---

### Task 3: External Command Provider

**Files:**
- Create: `applications/recommendation_chatbot_eval/recbot/provider.py`
- Create: `applications/recommendation_chatbot_eval/tests/test_provider.py`

- [ ] **Step 1: Write failing tests for subprocess provider behavior**

Create `applications/recommendation_chatbot_eval/tests/test_provider.py`:

```python
import os
import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from recbot.provider import ExternalCommandConfig, ExternalCommandRecBotProvider, ProviderError
from recbot.types import ChatMessage, RecBotRequest


class ExternalCommandProviderTest(unittest.TestCase):
    def test_provider_sends_request_and_reads_turn_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "fake_bridge.py"
            script.write_text(
                textwrap.dedent(
                    """
                    import json
                    import sys

                    payload = json.load(sys.stdin)
                    latest_user = [m["content"] for m in payload["messages"] if m["role"] == "user"][-1]
                    json.dump(
                        {
                            "backend": "fake",
                            "conversation_id": payload["conversation_id"],
                            "turn_id": payload["turn_id"],
                            "user_message": latest_user,
                            "assistant_message": "fake response",
                            "native_action": {"raw": "Final Answer: fake response", "raw_tool_plan": None},
                            "trace": {
                                "raw_tool_plan": None,
                                "raw_tool_outputs": None,
                                "recommended_item_ids": [],
                            },
                        },
                        sys.stdout,
                    )
                    """
                ).strip()
            )
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            provider = ExternalCommandRecBotProvider(
                ExternalCommandConfig(command=[sys.executable, str(script)], timeout_seconds=10)
            )
            request = RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="user", content="Recommend a movie.")],
            )

            result = provider.next_turn(request)

            self.assertEqual(result.backend, "fake")
            self.assertEqual(result.user_message, "Recommend a movie.")
            self.assertEqual(result.assistant_message, "fake response")

    def test_provider_raises_on_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "bad_bridge.py"
            script.write_text("import sys\nsys.stderr.write('boom')\nsys.exit(7)\n")
            provider = ExternalCommandRecBotProvider(
                ExternalCommandConfig(command=[sys.executable, str(script)], timeout_seconds=10)
            )
            request = RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="user", content="Recommend a movie.")],
            )

            with self.assertRaises(ProviderError) as context:
                provider.next_turn(request)

            self.assertIn("exit code 7", str(context.exception))

    def test_provider_raises_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "invalid_json_bridge.py"
            script.write_text("print('not json')\n")
            provider = ExternalCommandRecBotProvider(
                ExternalCommandConfig(command=[sys.executable, str(script)], timeout_seconds=10)
            )
            request = RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="user", content="Recommend a movie.")],
            )

            with self.assertRaises(ProviderError) as context:
                provider.next_turn(request)

            self.assertIn("invalid JSON", str(context.exception))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run provider tests and verify they fail**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications/recommendation_chatbot_eval/tests/test_provider.py -v
```

Expected: FAIL with an import error because `recbot.provider` does not exist yet.

- [ ] **Step 3: Implement the external command provider**

Create `applications/recommendation_chatbot_eval/recbot/provider.py`:

```python
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Protocol

from recbot.types import RecBotRequest, RecBotTurnResult


class ProviderError(RuntimeError):
    pass


class RecBotProvider(Protocol):
    def next_turn(self, request: RecBotRequest) -> RecBotTurnResult:
        raise NotImplementedError


@dataclass(frozen=True)
class ExternalCommandConfig:
    command: list[str]
    timeout_seconds: int = 120
    env: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("command must contain at least one argument")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class ExternalCommandRecBotProvider:
    def __init__(self, config: ExternalCommandConfig) -> None:
        self.config = config

    def next_turn(self, request: RecBotRequest) -> RecBotTurnResult:
        env = dict(os.environ)
        env.update(self.config.env)
        payload = json.dumps(request.to_dict())
        try:
            completed = subprocess.run(
                self.config.command,
                input=payload,
                text=True,
                capture_output=True,
                timeout=self.config.timeout_seconds,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                f"external recbot command timed out after {self.config.timeout_seconds} seconds"
            ) from exc

        if completed.returncode != 0:
            raise ProviderError(
                f"external recbot command failed with exit code {completed.returncode}: "
                f"{completed.stderr.strip()}"
            )

        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"external recbot command returned invalid JSON: {completed.stdout[:500]}"
            ) from exc

        try:
            return RecBotTurnResult.from_dict(response)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"external recbot command returned an invalid turn result: {response}") from exc
```

- [ ] **Step 4: Run all current tests**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git add applications/recommendation_chatbot_eval/recbot/provider.py applications/recommendation_chatbot_eval/tests/test_provider.py
git commit -m "feat: add external recbot provider contract"
```

---

### Task 4: InteRecAgent Bridge

**Files:**
- Create: `applications/recommendation_chatbot_eval/recbot/interecagent_bridge.py`
- Create: `applications/recommendation_chatbot_eval/tests/test_interecagent_bridge.py`

- [ ] **Step 1: Write failing tests for bridge helpers**

Create `applications/recommendation_chatbot_eval/tests/test_interecagent_bridge.py`:

```python
import unittest

from recbot.interecagent_bridge import _build_chat_history, _latest_user_message
from recbot.types import ChatMessage, RecBotRequest


class InteRecAgentBridgeTest(unittest.TestCase):
    def test_latest_user_message_uses_last_user_turn(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=3,
            messages=[
                ChatMessage(role="user", content="Can you recommend a movie?"),
                ChatMessage(role="assistant", content="What mood?"),
                ChatMessage(role="user", content="A tense thriller."),
            ],
        )

        self.assertEqual(_latest_user_message(request), "A tense thriller.")

    def test_build_chat_history_excludes_latest_user_message(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=3,
            messages=[
                ChatMessage(role="system", content="Use only the catalog."),
                ChatMessage(role="user", content="Can you recommend a movie?"),
                ChatMessage(role="assistant", content="What mood?"),
                ChatMessage(role="user", content="A tense thriller."),
            ],
        )

        history = _build_chat_history(request)

        self.assertIn("System: Use only the catalog.", history)
        self.assertIn("Human: Can you recommend a movie?", history)
        self.assertIn("Assistent: What mood?", history)
        self.assertNotIn("A tense thriller.", history)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run bridge tests and verify they fail**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications/recommendation_chatbot_eval/tests/test_interecagent_bridge.py -v
```

Expected: FAIL with an import error because `recbot.interecagent_bridge` does not exist yet.

- [ ] **Step 3: Implement the bridge module**

Create `applications/recommendation_chatbot_eval/recbot/interecagent_bridge.py`:

```python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from recbot.native_contract import build_native_action
from recbot.types import RecBotRequest, RecBotTrace, RecBotTurnResult


def _latest_user_message(request: RecBotRequest) -> str:
    return request.latest_user_message


def _build_chat_history(request: RecBotRequest) -> str:
    lines: list[str] = []
    prior_messages = request.messages[:-1]
    for message in prior_messages:
        if message.role == "user":
            prefix = "Human"
        elif message.role == "assistant":
            prefix = "Assistent"
        else:
            prefix = "System"
        lines.append(f"{prefix}: {message.content}")
    return "\n".join(lines)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return float(raw)


def _prepare_imports(interecagent_root: str, domain: str) -> None:
    root = Path(interecagent_root).expanduser().resolve()
    if not root.exists():
        raise RuntimeError(f"INTERECAGENT_ROOT does not exist: {root}")
    if not (root / "llm4crs").exists():
        raise RuntimeError(f"INTERECAGENT_ROOT must point to the InteRecAgent directory: {root}")
    resources_dir = root / "resources" / domain
    if not resources_dir.exists():
        raise RuntimeError(
            f"RecAI resources for domain '{domain}' are missing at {resources_dir}. "
            "Download and unpack the ready-to-run InteRecAgent resources before running the smoke test."
        )
    os.environ["DOMAIN"] = domain
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _build_interecagent(domain: str):
    from llm4crs.agent_plan_first_openai import CRSAgentPlanFirstOpenAI
    from llm4crs.buffer import CandidateBuffer
    from llm4crs.corups import BaseGallery
    from llm4crs.environ_variables import (
        CATEGORICAL_COLS,
        GAME_INFO_FILE,
        ITEM_SIM_FILE,
        MODEL_CKPT_FILE,
        TABLE_COL_DESC_FILE,
        USE_COLS,
    )
    from llm4crs.mapper import MapTool
    from llm4crs.prompt import (
        CANDIDATE_STORE_TOOL_DESC,
        HARD_FILTER_TOOL_DESC,
        LOOK_UP_TOOL_DESC,
        MAP_TOOL_DESC,
        RANKING_TOOL_DESC,
        SOFT_FILTER_TOOL_DESC,
        TOOL_NAMES,
    )
    from llm4crs.query import QueryTool
    from llm4crs.ranking import RecModelTool
    from llm4crs.retrieval import SQLSearchTool, SimilarItemTool
    from llm4crs.utils import FuncToolWrapper

    domain_map = {"item": domain, "Item": domain.capitalize(), "ITEM": domain.upper()}
    tool_names = {key: value.format(**domain_map) for key, value in TOOL_NAMES.items()}
    item_corpus = BaseGallery(
        GAME_INFO_FILE,
        TABLE_COL_DESC_FILE,
        f"{domain}_information",
        columns=USE_COLS,
        fuzzy_cols=["title"] + CATEGORICAL_COLS,
        categorical_cols=CATEGORICAL_COLS,
    )
    candidate_buffer = CandidateBuffer(
        item_corpus,
        num_limit=_env_int("INTERECAGENT_MAX_CANDIDATE_NUM", 1000),
    )
    tools = {
        "BufferStoreTool": FuncToolWrapper(
            func=candidate_buffer.init_candidates,
            name=tool_names["BufferStoreTool"],
            desc=CANDIDATE_STORE_TOOL_DESC.format(**domain_map),
        ),
        "LookUpTool": QueryTool(
            name=tool_names["LookUpTool"],
            desc=LOOK_UP_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
        ),
        "HardFilterTool": SQLSearchTool(
            name=tool_names["HardFilterTool"],
            desc=HARD_FILTER_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
            max_candidates_num=_env_int("INTERECAGENT_MAX_CANDIDATE_NUM", 1000),
        ),
        "SoftFilterTool": SimilarItemTool(
            name=tool_names["SoftFilterTool"],
            desc=SOFT_FILTER_TOOL_DESC.format(**domain_map),
            item_sim_path=ITEM_SIM_FILE,
            item_corups=item_corpus,
            buffer=candidate_buffer,
            top_ratio=_env_float("INTERECAGENT_SIMILAR_RATIO", 0.05),
        ),
        "RankingTool": RecModelTool(
            name=tool_names["RankingTool"],
            desc=RANKING_TOOL_DESC.format(**domain_map),
            model_fpath=MODEL_CKPT_FILE,
            item_corups=item_corpus,
            buffer=candidate_buffer,
            rec_num=_env_int("INTERECAGENT_RANK_NUM", 100),
        ),
        "MapTool": MapTool(
            name=tool_names["MapTool"],
            desc=MAP_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
        ),
    }
    agent = CRSAgentPlanFirstOpenAI(
        domain,
        tools,
        candidate_buffer,
        item_corpus,
        os.environ.get("INTERECAGENT_ENGINE", "gpt-4o-mini"),
        os.environ.get("INTERECAGENT_BOT_TYPE", "chat"),
        max_tokens=_env_int("INTERECAGENT_MAX_OUTPUT_TOKENS", 1024),
        enable_shorten=bool(_env_int("INTERECAGENT_ENABLE_SHORTEN", 0)),
        demo_mode=os.environ.get("INTERECAGENT_DEMO_MODE", "zero"),
        demo_dir_or_file=os.environ.get("INTERECAGENT_DEMO_DIR_OR_FILE"),
        num_demos=_env_int("INTERECAGENT_NUM_DEMOS", 3),
        critic=None,
        reflection_limits=_env_int("INTERECAGENT_REFLECTION_LIMITS", 3),
        verbose=bool(_env_int("INTERECAGENT_VERBOSE", 0)),
        reply_style=os.environ.get("INTERECAGENT_REPLY_STYLE", "detailed"),
        enable_summarize=_env_int("INTERECAGENT_ENABLE_SUMMARIZE", 1),
    )
    agent.init_agent()
    agent.set_mode(os.environ.get("INTERECAGENT_MODE", "accuracy"))
    return agent


def _last_recorded_plan(agent: Any) -> str | None:
    record_cache = getattr(agent, "_plan_record_cache", {})
    trajectory = record_cache.get("traj", []) if isinstance(record_cache, dict) else []
    for entry in reversed(trajectory):
        if entry.get("role") == "plan":
            return entry.get("content")
    return None


def run_turn(request: RecBotRequest) -> RecBotTurnResult:
    interecagent_root = os.environ.get("INTERECAGENT_ROOT")
    if not interecagent_root:
        raise RuntimeError("INTERECAGENT_ROOT must be set")
    domain = os.environ.get("INTERECAGENT_DOMAIN", request.metadata.get("domain", "movie"))
    _prepare_imports(interecagent_root, domain)
    agent = _build_interecagent(domain)
    user_message = _latest_user_message(request)
    response = agent.run({"input": user_message}, chat_history=_build_chat_history(request))
    raw_plan = _last_recorded_plan(agent)
    native_raw = raw_plan if raw_plan else f"Final Answer: {response}"
    native_action = build_native_action(native_raw)
    trace = RecBotTrace(
        raw_tool_plan=native_action.raw_tool_plan,
        raw_tool_outputs=getattr(getattr(agent, "candidate_buffer", None), "track_info", None),
        recommended_item_ids=[],
    )
    return RecBotTurnResult(
        backend="interecagent",
        conversation_id=request.conversation_id,
        turn_id=request.turn_id,
        user_message=user_message,
        assistant_message=response,
        native_action=native_action,
        trace=trace,
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        request = RecBotRequest.from_dict(payload)
        result = run_turn(request)
        json.dump(result.to_dict(), sys.stdout)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run all current tests**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add applications/recommendation_chatbot_eval/recbot/interecagent_bridge.py applications/recommendation_chatbot_eval/tests/test_interecagent_bridge.py
git commit -m "feat: add interecagent bridge"
```

---

### Task 5: Movie Smoke Script

**Files:**
- Create: `applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py`

- [ ] **Step 1: Create the smoke script**

Create `applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py`:

```python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from recbot.provider import ExternalCommandConfig, ExternalCommandRecBotProvider
from recbot.types import ChatMessage, RecBotRequest


def main() -> int:
    bridge = APP_ROOT / "recbot" / "interecagent_bridge.py"
    python_executable = os.environ.get("INTERECAGENT_PYTHON", sys.executable)
    provider = ExternalCommandRecBotProvider(
        ExternalCommandConfig(
            command=[python_executable, str(bridge)],
            timeout_seconds=int(os.environ.get("INTERECAGENT_TIMEOUT_SECONDS", "180")),
        )
    )
    messages = [
        ChatMessage(role="system", content="Use the configured InteRecAgent catalog for recommendations."),
        ChatMessage(role="user", content="Can you recommend a movie for tonight?"),
    ]
    first = provider.next_turn(
        RecBotRequest(
            conversation_id="local_movie_smoke",
            turn_id=1,
            messages=messages,
            metadata={"domain": "movie"},
        )
    )
    print(json.dumps(first.to_dict(), indent=2))
    messages.append(ChatMessage(role="assistant", content=first.assistant_message))
    messages.append(ChatMessage(role="user", content="I want something tense and mysterious, but not horror."))
    second = provider.next_turn(
        RecBotRequest(
            conversation_id="local_movie_smoke",
            turn_id=2,
            messages=messages,
            metadata={"domain": "movie"},
        )
    )
    print(json.dumps(second.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run unit tests**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

Expected: PASS, 13 tests.

- [ ] **Step 3: Run the opt-in real InteRecAgent smoke test when external dependencies are ready**

Run only after the external RecAI environment is configured:

```bash
export INTERECAGENT_ROOT="$HOME/RecAI/InteRecAgent"
export INTERECAGENT_PYTHON="$HOME/miniconda3/envs/interecagent/bin/python"
export INTERECAGENT_DOMAIN=movie
export INTERECAGENT_ENGINE=gpt-4o-mini
export INTERECAGENT_BOT_TYPE=chat
test -d "$INTERECAGENT_ROOT"
test -x "$INTERECAGENT_PYTHON"
test -n "$OPENAI_API_KEY"
PYTHONPATH=applications/recommendation_chatbot_eval "$INTERECAGENT_PYTHON" applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py
```

Expected: two JSON `RecBotTurnResult` objects printed to stdout. Each object must include `backend: "interecagent"`, an `assistant_message`, and a preserved `native_action.raw`.

- [ ] **Step 4: Commit**

```bash
git add applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py
git commit -m "test: add interecagent movie smoke script"
```

---

### Task 6: Provider Documentation

**Files:**
- Create: `applications/recommendation_chatbot_eval/INTERECAGENT_PROVIDER.md`
- Modify: `applications/recommendation_chatbot_eval/README.md`
- Modify: `applications/recommendation_chatbot_eval/LOCAL_MOVIE_TESTING.md`

- [ ] **Step 1: Create provider setup documentation**

Create `applications/recommendation_chatbot_eval/INTERECAGENT_PROVIDER.md`:

````markdown
# InteRecAgent Provider

The RecBot interface calls Microsoft RecAI/InteRecAgent as an external backend.
MatrAIx does not reimplement InteRecAgent planning, retrieval, ranking, or tool
execution.

## Boundary

MatrAIx owns:

- `RecBotRequest`
- `RecBotTurnResult`
- the subprocess provider
- the JSON bridge
- tests for the interface contract

InteRecAgent owns:

- conversational recommendation reasoning
- native `Final Answer` / `Action: ToolExecutor` output
- query, retrieval, ranking, and mapping tools
- domain resources and recommendation checkpoints

## Required External Setup

Clone RecAI and install InteRecAgent in its own Python environment:

```bash
git clone https://github.com/microsoft/RecAI.git
cd RecAI/InteRecAgent
conda create -n interecagent python==3.9
conda activate interecagent
pip install -r requirements.txt
```

Download the ready-to-run InteRecAgent resources linked from the RecAI README,
unpack them, and place them at:

```text
RecAI/InteRecAgent/resources/movie
RecAI/InteRecAgent/resources/game
RecAI/InteRecAgent/resources/beauty_product
```

## Environment Variables

```bash
export INTERECAGENT_ROOT="$HOME/RecAI/InteRecAgent"
export INTERECAGENT_PYTHON="$HOME/miniconda3/envs/interecagent/bin/python"
export INTERECAGENT_DOMAIN=movie
export INTERECAGENT_ENGINE=gpt-4o-mini
export INTERECAGENT_BOT_TYPE=chat
test -d "$INTERECAGENT_ROOT"
test -x "$INTERECAGENT_PYTHON"
test -n "$OPENAI_API_KEY"
```

Azure OpenAI-compatible deployments can use:

```bash
export OPENAI_API_TYPE=azure
test -n "$OPENAI_API_BASE"
test -n "$OPENAI_API_VERSION"
test -n "$OPENAI_API_KEY"
test -n "$AZURE_OPENAI_DEPLOYMENT"
export INTERECAGENT_ENGINE="$AZURE_OPENAI_DEPLOYMENT"
```

## Local Smoke Test

```bash
PYTHONPATH=applications/recommendation_chatbot_eval "$INTERECAGENT_PYTHON" applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py
```

The smoke test prints two `RecBotTurnResult` JSON objects. The user-facing reply
is `assistant_message`. The preserved native InteRecAgent output is stored in
`native_action.raw` and `trace.raw_tool_plan`.

## Test Policy

Default unit tests do not require RecAI, GPU libraries, model checkpoints, or API
keys:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
```

The real InteRecAgent smoke test is run manually because it depends on external
resources and API credentials.
````

- [ ] **Step 2: Update README links**

Append this section to `applications/recommendation_chatbot_eval/README.md`:

```markdown

## RecBot Provider

The first RecBot backend is Microsoft RecAI/InteRecAgent, used as an external
provider. MatrAIx preserves InteRecAgent's native action contract and records it
inside a `RecBotTurnResult` envelope.

See [INTERECAGENT_PROVIDER.md](INTERECAGENT_PROVIDER.md) for setup and smoke
testing.
```

- [ ] **Step 3: Update movie local testing notes**

Append this section to `applications/recommendation_chatbot_eval/LOCAL_MOVIE_TESTING.md`:

````markdown

## InteRecAgent Smoke Test

After the external RecAI/InteRecAgent environment is configured, run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval "$INTERECAGENT_PYTHON" applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py
```

This validates that a persona-style user message can be sent through the
MatrAIx RecBot provider to the existing InteRecAgent movie backend, and that the
response returns as a `RecBotTurnResult`.
````

- [ ] **Step 4: Run docs and test verification**

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
LC_ALL=C rg -n "[^\\x00-\\x7F]" applications/recommendation_chatbot_eval/recbot applications/recommendation_chatbot_eval/tests applications/recommendation_chatbot_eval/scripts applications/recommendation_chatbot_eval/INTERECAGENT_PROVIDER.md
```

Expected:

- unittest exits 0 with 13 tests passing.
- `rg` exits 1 with no output, meaning no non-ASCII characters were found in the new implementation files.

- [ ] **Step 5: Commit**

```bash
git add applications/recommendation_chatbot_eval/README.md applications/recommendation_chatbot_eval/LOCAL_MOVIE_TESTING.md applications/recommendation_chatbot_eval/INTERECAGENT_PROVIDER.md
git commit -m "docs: document interecagent provider setup"
```

---

## Final Verification

Run:

```bash
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
jq empty applications/recommendation_chatbot_eval/schemas/catalog_item.schema.json
jq -c . data/normalized/recommendation_catalogs/cmu_movie_summary/items.jsonl >/dev/null
git status --short
```

Expected:

- All unit tests pass.
- JSON schema parses.
- Normalized movie catalog JSONL parses.
- `git status --short` shows only expected committed or intentionally uncommitted files for the current task.

## Scope Exclusions

This plan does not build a new recommender model, a new ranking model, a new action language, or a turn classifier. It does not convert the CMU Movie Summary Corpus into RecAI resources. The first working path calls InteRecAgent's existing movie resources; catalog conversion from MatrAIx normalized movie data to RecAI resource format should be a separate plan after the provider path works.

## Self-Review

- Spec coverage: The plan preserves InteRecAgent's native action contract, avoids turn classification, provides a simple RecBot envelope, calls external RecAI instead of copying its internals, and includes a movie local smoke path.
- Template scan: No unresolved template values are required for the default unit-test path. The smoke test requires user-specific environment values and documents the exact variables.
- Type consistency: `RecBotRequest`, `NativeAction`, `RecBotTrace`, `RecBotTurnResult`, `ExternalCommandConfig`, and `ExternalCommandRecBotProvider` names are consistent across tests, implementation, and docs.

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
        ...


@dataclass(frozen=True)
class ExternalCommandConfig:
    command: list[str]
    timeout_seconds: int = 120
    env: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.command, list) or not self.command:
            raise ValueError("command must be a non-empty list")
        for command_part in self.command:
            if not isinstance(command_part, str) or not command_part:
                raise ValueError("command must contain only non-empty strings")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")
        if self.env is None:
            object.__setattr__(self, "env", {})
        if not isinstance(self.env, dict):
            raise ValueError("env must be a dictionary")
        for key, value in self.env.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("env must contain only string keys and values")


class ExternalCommandRecBotProvider:
    def __init__(self, config: ExternalCommandConfig) -> None:
        self._config = config

    def next_turn(self, request: RecBotRequest) -> RecBotTurnResult:
        env = os.environ.copy()
        env.update(self._config.env)

        try:
            completed = subprocess.run(
                self._config.command,
                input=json.dumps(request.to_dict()),
                text=True,
                capture_output=True,
                timeout=self._config.timeout_seconds,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                f"external command timed out after {self._config.timeout_seconds} seconds"
            ) from exc
        except (OSError, TypeError) as exc:
            raise ProviderError(f"external command failed to start: {exc}") from exc

        if completed.returncode != 0:
            raise ProviderError(
                f"external command failed with exit code {completed.returncode}: {completed.stderr}"
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"external command returned invalid JSON: {exc}") from exc

        try:
            return RecBotTurnResult.from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"external command returned invalid result: {exc}") from exc

"""System telemetry hooks on UseComputerEnvironment."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from harbor.environments import use_computer as uc
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths


@dataclass
class FakeSdkResult:
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0


class FakeShell:
    def __init__(self, result: FakeSdkResult | None = None) -> None:
        self.result = result or FakeSdkResult()
        self.calls: list[dict[str, Any]] = []

    async def run(
        self,
        command: str,
        shell: str | None = None,
        timeout: int = 300,
    ) -> FakeSdkResult:
        self.calls.append({"command": command, "shell": shell, "timeout": timeout})
        return self.result


class FakeSandbox:
    def __init__(self) -> None:
        self.sandbox_id = "sbx-test"
        self.vm_ip = "10.0.0.2"
        self.shell = FakeShell()
        self.keepalives: list[float] = []
        self.closed = False
        self.exec_ssh_calls: list[dict[str, Any]] = []

    async def start_keepalive(self, interval: float = 30.0) -> None:
        self.keepalives.append(interval)

    async def close(self) -> None:
        self.closed = True

    async def exec_ssh(self, command: str, timeout: int = 120) -> FakeSdkResult:
        self.exec_ssh_calls.append({"command": command, "timeout": timeout})
        return FakeSdkResult()


class FakeClient:
    def __init__(self, sandbox: FakeSandbox) -> None:
        self.sandbox = sandbox

    async def create(self, **kwargs: Any) -> FakeSandbox:
        return self.sandbox


def _make_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sandbox: FakeSandbox | None = None,
    platform: str = "macos",
    session_id: str = "session",
) -> uc.UseComputerEnvironment:
    sandbox = sandbox or FakeSandbox()

    def fake_async_computer(**factory_kwargs: Any) -> FakeClient:
        return FakeClient(sandbox)

    monkeypatch.setattr(uc, "_HAS_USE_COMPUTER", True)
    monkeypatch.setattr(uc, "AsyncComputer", fake_async_computer)

    environment_dir = tmp_path / "environment"
    environment_dir.mkdir(exist_ok=True)
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()

    return uc.UseComputerEnvironment(
        environment_dir=environment_dir,
        environment_name="test-env",
        session_id=session_id,
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(cpus=4, memory_mb=4096, storage_mb=40960),
        platform=platform,
    )


@pytest.mark.asyncio
async def test_macos_start_writes_system_telemetry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "task.toml").write_text(
        '[task]\nname = "application/os-app-macos-stocks-mu-sentiment"\n'
    )
    sandbox = FakeSandbox()
    env = _make_env(
        tmp_path,
        monkeypatch,
        sandbox=sandbox,
        platform="macos",
        session_id="trial-telemetry",
    )

    await env.start(force_build=False)
    await env.stop(delete=True)

    telemetry_commands = [
        call["command"]
        for call in sandbox.exec_ssh_calls
        if "/tmp/matraix-telemetry/system_trace.json" in call["command"]
    ]
    assert len(telemetry_commands) == 1
    match = re.search(r"\{.*\}", telemetry_commands[0], re.DOTALL)
    assert match is not None
    payload = json.loads(match.group())
    assert payload["platform"] == "macos"
    assert payload["session"]["trial_id"] == "trial-telemetry"
    assert payload["session"]["task"] == (
        "application/os-app-macos-stocks-mu-sentiment"
    )
    phases = [snap["phase"] for snap in payload["snapshots"]]
    assert phases == ["baseline", "final"]


@pytest.mark.asyncio
async def test_macos_prepare_artifact_collection_flushes_telemetry_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox = FakeSandbox()
    env = _make_env(tmp_path, monkeypatch, sandbox=sandbox, platform="macos")
    env._sandbox = sandbox

    await env.start(force_build=False)
    await env.prepare_artifact_collection()
    await env.stop(delete=True)

    telemetry_commands = [
        call["command"]
        for call in sandbox.exec_ssh_calls
        if "/tmp/matraix-telemetry/system_trace.json" in call["command"]
    ]
    assert len(telemetry_commands) == 1

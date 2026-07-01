from __future__ import annotations

import json
from pathlib import Path

import pytest

from matraix.telemetry.paths import SYSTEM_TRACE_PATH
from matraix.telemetry.schema import TelemetryTrace, SessionInfo, Snapshot
from matraix.telemetry.session import TelemetrySession, read_task_name, _write_remote_json


def test_read_task_name_from_toml(tmp_path: Path) -> None:
    (tmp_path / "task.toml").write_text(
        '[task]\nname = "matraix/application-computer-use-macos-notification-preferences"\n'
    )
    assert (
        read_task_name(tmp_path)
        == "matraix/application-computer-use-macos-notification-preferences"
    )


def test_telemetry_trace_serializes() -> None:
    trace = TelemetryTrace(
        platform="macos",
        session=SessionInfo(
            trial_id="trial-1",
            task="matraix/application-computer-use-macos-notification-preferences",
            platform="macos",
            started_at="2026-06-28T12:00:00+00:00",
            ended_at="2026-06-28T12:01:00+00:00",
            duration_sec=60.0,
        ),
        snapshots=[
            Snapshot(
                ts="2026-06-28T12:00:01+00:00",
                phase="baseline",
                signals={"platform": "macos"},
            )
        ],
    )
    data = trace.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["platform"] == "macos"
    assert data["session"]["trial_id"] == "trial-1"
    assert len(data["snapshots"]) == 1


def test_null_session_for_ubuntu(tmp_path: Path) -> None:
    session = TelemetrySession.for_environment(
        platform="ubuntu",
        enabled=True,
        session_id="s1",
        task_dir=tmp_path,
    )
    assert session.enabled is False


@pytest.mark.asyncio
async def test_session_flush_writes_remote_json() -> None:
    class FakeEnv:
        def __init__(self) -> None:
            self.commands: list[str] = []

        async def exec(self, command: str, timeout_sec: int = 30):
            self.commands.append(command)

            class Result:
                return_code = 0

            return Result()

    env = FakeEnv()
    session = TelemetrySession.for_environment(
        platform="macos",
        enabled=True,
        session_id="trial-abc",
        task_dir=Path("/nonexistent"),
    )
    assert isinstance(session, TelemetrySession)

    await session.on_trial_start(env)
    await session.on_trial_end(env)
    path = await session.flush(env)

    assert path == SYSTEM_TRACE_PATH
    assert env.commands
    assert SYSTEM_TRACE_PATH in env.commands[-1]
    assert '"trial_id": "trial-abc"' in env.commands[-1]
    assert '"phase": "baseline"' in env.commands[-1]
    assert '"phase": "final"' in env.commands[-1]


def test_session_links_host_trajectory(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    (agent_dir / "trajectory.json").write_text(
        json.dumps(
            {
                "session_id": "agent-session-99",
                "steps": [{"step_id": 1}, {"step_id": 2}],
            }
        )
    )
    (agent_dir / "recording.mp4").write_bytes(b"fake")

    session = TelemetrySession.for_environment(
        platform="macos",
        enabled=True,
        session_id="trial-abc",
        task_dir=tmp_path,
    )
    assert isinstance(session, TelemetrySession)
    session.link_host_trajectory(agent_dir)

    links = session._trace.links
    assert links["agent_trajectory_path"] == "agent/trajectory.json"
    assert links["agent_session_id"] == "agent-session-99"
    assert links["agent_step_count"] == 2
    assert links["agent_recording_path"] == "agent/recording.mp4"


@pytest.mark.asyncio
async def test_write_remote_json_parsable_payload() -> None:
    captured: list[str] = []

    class FakeEnv:
        async def exec(self, command: str, timeout_sec: int = 30):
            start = command.index("<<'EOF'\n") + len("<<'EOF'\n")
            end = command.rindex("\nEOF")
            captured.append(command[start:end])

            class Result:
                return_code = 0

            return Result()

    ok = await _write_remote_json(FakeEnv(), SYSTEM_TRACE_PATH, {"ok": True})
    assert ok
    assert json.loads(captured[0]) == {"ok": True}

"""Orchestrate computer-use system telemetry across a Harbor trial."""

from __future__ import annotations

import json
import logging
import shlex
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from matraix.telemetry.factory import get_collector
from matraix.telemetry.paths import SYSTEM_TRACE_PATH, TELEMETRY_ROOT
from matraix.telemetry.schema import SCHEMA_VERSION, SessionInfo, Snapshot, TelemetryTrace, utc_now_iso

_TELEMETRY_PLATFORMS = frozenset({"macos", "ios"})


def read_task_name(task_dir: Path) -> str:
    toml_path = task_dir / "task.toml"
    if not toml_path.is_file():
        return ""
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    task = data.get("task") or {}
    return str(task.get("name") or "").strip()


@dataclass
class _NullTelemetrySession:
    enabled: bool = False

    async def on_trial_start(self, environment: Any) -> None:
        return None

    async def on_step(self, environment: Any, step: int) -> None:
        return None

    async def on_trial_end(self, environment: Any) -> None:
        return None

    async def flush(self, environment: Any) -> str | None:
        return None


class TelemetrySession:
    """Record system-side telemetry for one use.computer trial."""

    def __init__(
        self,
        *,
        platform: str,
        trial_id: str,
        task_name: str,
        collector: Any,
        logger: logging.Logger | None = None,
    ) -> None:
        self._platform = platform
        self._trial_id = trial_id
        self._task_name = task_name
        self._collector = collector
        self._logger = (logger or logging.getLogger(__name__)).getChild(
            "telemetry"
        )
        self._started_monotonic: float | None = None
        self._trace = TelemetryTrace(
            platform=platform,
            session=SessionInfo(
                trial_id=trial_id,
                task=task_name,
                platform=platform,
                started_at=utc_now_iso(),
            ),
        )

    @classmethod
    def for_environment(
        cls,
        *,
        platform: str,
        enabled: bool,
        session_id: str,
        task_dir: Path,
        logger: logging.Logger | None = None,
    ) -> TelemetrySession | _NullTelemetrySession:
        if not enabled or platform not in _TELEMETRY_PLATFORMS:
            return _NullTelemetrySession()
        collector = get_collector(platform)
        if collector is None:
            return _NullTelemetrySession()
        return cls(
            platform=platform,
            trial_id=session_id,
            task_name=read_task_name(task_dir),
            collector=collector,
            logger=logger,
        )

    @property
    def enabled(self) -> bool:
        return True

    async def on_trial_start(self, environment: Any) -> None:
        self._started_monotonic = time.monotonic()
        await self._record_snapshot(environment, phase="baseline")

    async def on_step(self, environment: Any, step: int) -> None:
        await self._record_snapshot(environment, phase="step", step=step)

    async def on_trial_end(self, environment: Any) -> None:
        ended_at = utc_now_iso()
        self._trace.session.ended_at = ended_at
        if self._started_monotonic is not None:
            self._trace.session.duration_sec = round(
                time.monotonic() - self._started_monotonic,
                3,
            )
        await self._record_snapshot(environment, phase="final")

    def link_host_trajectory(self, agent_dir: Path) -> None:
        """Attach agent trajectory metadata from the trial host before flush."""
        trajectory_path = agent_dir / "trajectory.json"
        if not trajectory_path.is_file():
            return
        try:
            data = json.loads(trajectory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._logger.debug("skipping trajectory link: %s", exc)
            return

        links = self._trace.links
        links["agent_trajectory_path"] = "agent/trajectory.json"
        session_id = data.get("session_id")
        if session_id:
            links["agent_session_id"] = str(session_id)
        steps = data.get("steps")
        if isinstance(steps, list):
            links["agent_step_count"] = len(steps)
        recording_path = agent_dir / "recording.mp4"
        if recording_path.is_file():
            links["agent_recording_path"] = "agent/recording.mp4"

    async def flush(self, environment: Any) -> str | None:
        self._trace.artifacts.setdefault("system_trace_path", SYSTEM_TRACE_PATH)
        self._trace.artifacts.setdefault("telemetry_root", TELEMETRY_ROOT)
        payload = self._trace.to_dict()
        if payload.get("schema_version") != SCHEMA_VERSION:
            self._logger.warning("unexpected telemetry schema version")
        ok = await _write_remote_json(environment, SYSTEM_TRACE_PATH, payload)
        if ok:
            self._logger.info("wrote system telemetry to %s", SYSTEM_TRACE_PATH)
            return SYSTEM_TRACE_PATH
        self._logger.warning("failed to write system telemetry to %s", SYSTEM_TRACE_PATH)
        return None

    async def _record_snapshot(
        self,
        environment: Any,
        *,
        phase: str,
        step: int | None = None,
    ) -> None:
        signals = await self._collector.collect(environment, phase=phase)
        if step is not None:
            signals = {**signals, "step": step}
        self._trace.snapshots.append(
            Snapshot(ts=utc_now_iso(), phase=phase, signals=signals)
        )


async def _write_remote_json(
    environment: Any,
    path: str,
    payload: dict[str, Any],
) -> bool:
    parent = str(Path(path).parent)
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    command = (
        f"mkdir -p {shlex.quote(parent)} && "
        f"cat > {shlex.quote(path)} <<'EOF'\n{body}\nEOF"
    )
    result = await environment.exec(command, timeout_sec=30)
    return int(getattr(result, "return_code", 1)) == 0

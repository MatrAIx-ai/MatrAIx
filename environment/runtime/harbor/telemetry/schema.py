"""JSON schema for computer-use system-side telemetry traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = "1.0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SessionInfo:
    trial_id: str
    task: str
    platform: str
    started_at: str
    ended_at: str | None = None
    duration_sec: float | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "trial_id": self.trial_id,
            "task": self.task,
            "platform": self.platform,
            "started_at": self.started_at,
        }
        if self.ended_at is not None:
            out["ended_at"] = self.ended_at
        if self.duration_sec is not None:
            out["duration_sec"] = self.duration_sec
        return out


@dataclass
class Snapshot:
    ts: str
    phase: str
    signals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"ts": self.ts, "phase": self.phase, "signals": self.signals}


@dataclass
class TelemetryTrace:
    platform: str
    session: SessionInfo
    snapshots: list[Snapshot] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    links: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "platform": self.platform,
            "session": self.session.to_dict(),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "artifacts": self.artifacts,
            "links": self.links,
        }

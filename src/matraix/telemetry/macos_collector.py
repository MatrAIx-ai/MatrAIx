"""macOS system telemetry collector (notifications / Focus ground truth)."""

from __future__ import annotations

from typing import Any

from matraix.telemetry.collector import BaseCollector
from matraix.telemetry.macos_probe import run_macos_notification_probe


class MacOSTelemetryCollector(BaseCollector):
    async def collect(self, environment: Any, *, phase: str) -> dict[str, Any]:
        signals: dict[str, Any] = {"phase": phase, "platform": "macos"}
        probe = await run_macos_notification_probe(environment)
        signals.update(probe)
        return signals

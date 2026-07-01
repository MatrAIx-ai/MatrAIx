"""iOS Simulator system telemetry collector (notifications ground truth)."""

from __future__ import annotations

from typing import Any

from harbor.telemetry.collector import BaseCollector
from harbor.telemetry.ios_probe import run_ios_notification_probe


class IOSTelemetryCollector(BaseCollector):
    async def collect(self, environment: Any, *, phase: str) -> dict[str, Any]:
        signals: dict[str, Any] = {"phase": phase, "platform": "ios"}
        device_type = str(getattr(environment, "_device_type", "") or "")
        runtime = str(getattr(environment, "_runtime", "") or "")
        probe = await run_ios_notification_probe(
            environment,
            device_type=device_type,
            runtime=runtime,
        )
        signals.update(probe)
        return signals

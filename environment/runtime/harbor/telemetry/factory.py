"""Factory for platform-specific telemetry collectors."""

from __future__ import annotations

from harbor.telemetry.collector import BaseCollector
from harbor.telemetry.ios_collector import IOSTelemetryCollector
from harbor.telemetry.macos_collector import MacOSTelemetryCollector

_COLLECTORS: dict[str, type[BaseCollector]] = {
    "macos": MacOSTelemetryCollector,
    "ios": IOSTelemetryCollector,
}


def get_collector(platform: str) -> BaseCollector | None:
    factory = _COLLECTORS.get(platform)
    if factory is None:
        return None
    return factory()

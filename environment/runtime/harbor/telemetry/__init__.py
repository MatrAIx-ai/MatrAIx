"""System-side telemetry for computer-use (macOS / iOS) trials."""

from harbor.telemetry.paths import SYSTEM_TRACE_PATH, TELEMETRY_ROOT
from harbor.telemetry.schema import SCHEMA_VERSION, TelemetryTrace
from harbor.telemetry.session import TelemetrySession

__all__ = [
    "SCHEMA_VERSION",
    "SYSTEM_TRACE_PATH",
    "TELEMETRY_ROOT",
    "TelemetrySession",
    "TelemetryTrace",
]

"""System-side telemetry for computer-use (macOS / iOS) trials."""

from matraix.telemetry.paths import SYSTEM_TRACE_PATH, TELEMETRY_ROOT
from matraix.telemetry.schema import SCHEMA_VERSION, TelemetryTrace
from matraix.telemetry.session import TelemetrySession

__all__ = [
    "SCHEMA_VERSION",
    "SYSTEM_TRACE_PATH",
    "TELEMETRY_ROOT",
    "TelemetrySession",
    "TelemetryTrace",
]

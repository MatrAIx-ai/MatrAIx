"""Filesystem paths for computer-use system telemetry on sandbox hosts."""

from __future__ import annotations

TELEMETRY_ROOT = "/tmp/personabench-telemetry"
SYSTEM_TRACE_FILENAME = "system_trace.json"
SYSTEM_TRACE_PATH = f"{TELEMETRY_ROOT}/{SYSTEM_TRACE_FILENAME}"

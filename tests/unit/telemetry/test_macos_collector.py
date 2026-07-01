from __future__ import annotations

import json

import pytest

from harbor.telemetry.macos_collector import MacOSTelemetryCollector
from harbor.telemetry.macos_probe import run_macos_notification_probe


@pytest.mark.asyncio
async def test_macos_collector_merges_probe_signals() -> None:
    probe_payload = {
        "probe_ok": True,
        "focus": {"focus_active": False, "active_mode_identifiers": []},
        "notifications": {"available": True, "registered_app_count": 3, "watched_apps": {}},
    }

    class FakeEnv:
        async def exec(self, command: str, timeout_sec: int = 45):
            assert "MATRAIX_WATCHED_BUNDLES" in command
            assert "com.apple.mail" in command

            class Result:
                return_code = 0
                stdout = json.dumps(probe_payload)
                stderr = ""

            return Result()

    collector = MacOSTelemetryCollector()
    signals = await collector.collect(FakeEnv(), phase="baseline")

    assert signals["phase"] == "baseline"
    assert signals["platform"] == "macos"
    assert signals["probe_ok"] is True
    assert signals["focus"]["focus_active"] is False
    assert signals["notifications"]["registered_app_count"] == 3


@pytest.mark.asyncio
async def test_run_macos_notification_probe_surfaces_exec_failure() -> None:
    class FakeEnv:
        async def exec(self, command: str, timeout_sec: int = 45):
            class Result:
                return_code = 1
                stdout = ""
                stderr = "permission denied"

            return Result()

    out = await run_macos_notification_probe(FakeEnv())
    assert out["probe_ok"] is False
    assert "permission denied" in out["probe_error"]

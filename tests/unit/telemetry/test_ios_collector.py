from __future__ import annotations

import json

import pytest

from matraix.telemetry.ios_collector import IOSTelemetryCollector
from matraix.telemetry.ios_probe import run_ios_notification_probe


@pytest.mark.asyncio
async def test_ios_collector_merges_probe_signals() -> None:
    probe_payload = {
        "probe_ok": True,
        "simulator": {"udid": "ABC", "name": "iPhone 17", "state": "Booted"},
        "notifications": {"available": True, "section_count": 2, "watched_apps": {}},
    }

    class FakeEnv:
        _device_type = "com.apple.CoreSimulator.SimDeviceType.iPhone-17"
        _runtime = "com.apple.CoreSimulator.SimRuntime.iOS-26-4"

        async def exec(self, command: str, timeout_sec: int = 60):
            assert "MATRAIX_WATCHED_BUNDLES" in command
            assert "com.apple.news" in command
            assert "MATRAIX_IOS_DEVICE_TYPE" in command
            assert "MATRAIX_IOS_RUNTIME" in command

            class Result:
                return_code = 0
                stdout = json.dumps(probe_payload)
                stderr = ""

            return Result()

    collector = IOSTelemetryCollector()
    signals = await collector.collect(FakeEnv(), phase="step")

    assert signals["phase"] == "step"
    assert signals["platform"] == "ios"
    assert signals["probe_ok"] is True
    assert signals["simulator"]["udid"] == "ABC"


@pytest.mark.asyncio
async def test_run_ios_notification_probe_surfaces_exec_failure() -> None:
    class FakeEnv:
        async def exec(self, command: str, timeout_sec: int = 60):
            class Result:
                return_code = 1
                stdout = ""
                stderr = "simctl not found"

            return Result()

    out = await run_ios_notification_probe(FakeEnv())
    assert out["probe_ok"] is False
    assert "simctl not found" in out["probe_error"]

"""Remote macOS probes for notification / Focus telemetry."""

from __future__ import annotations

import json
import shlex
from typing import Any

# Bundles aligned with production os-app macOS tasks (Stocks, Safari, Shortcuts).
_WATCHED_BUNDLE_IDS = (
    "com.apple.stocks",
    "com.apple.Safari",
    "com.apple.shortcuts",
)

_MACOS_PROBE_SCRIPT = r"""
from __future__ import annotations

import json
import os
import plistlib
import subprocess
from pathlib import Path


def _run(cmd):
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except Exception as exc:
        return 1, "", str(exc)


def _read_focus():
    out = {
        "focus_active": False,
        "active_mode_identifiers": [],
        "configured_mode_count": 0,
    }
    db = Path.home() / "Library/DoNotDisturb/DB"
    assertions_path = db / "Assertions.json"
    modes_path = db / "ModeConfigurations.json"
    if assertions_path.is_file():
        try:
            payload = json.loads(assertions_path.read_text(encoding="utf-8"))
            records = payload if isinstance(payload, list) else payload.get("data", [])
            if not isinstance(records, list):
                records = []
            for record in records:
                if not isinstance(record, dict):
                    continue
                mode_id = (
                    record.get("modeIdentifier")
                    or record.get("mode")
                    or record.get("identifier")
                )
                if mode_id:
                    out["active_mode_identifiers"].append(str(mode_id))
            out["focus_active"] = bool(out["active_mode_identifiers"])
        except Exception as exc:
            out["assertions_error"] = str(exc)
    if modes_path.is_file():
        try:
            payload = json.loads(modes_path.read_text(encoding="utf-8"))
            modes = payload if isinstance(payload, list) else payload.get("data", payload)
            if isinstance(modes, dict):
                out["configured_mode_count"] = len(modes)
            elif isinstance(modes, list):
                out["configured_mode_count"] = len(modes)
        except Exception as exc:
            out["mode_config_error"] = str(exc)
    return out


def _read_legacy_dnd():
    rc, stdout, stderr = _run(
        ["defaults", "-currentHost", "read", "com.apple.notificationcenterui", "doNotDisturb"]
    )
    if rc != 0:
        return {"available": False, "error": stderr or stdout or f"exit {rc}"}
    return {"available": True, "enabled": stdout in {"1", "true", "yes"}}


def _notifications_enabled(flags: int) -> bool | None:
    # ncprefs flags are undocumented; zero generally means not authorized.
    if flags == 0:
        return False
    return True


def _read_ncprefs(watched):
    path = Path.home() / "Library/Preferences/com.apple.ncprefs.plist"
    out = {
        "available": path.is_file(),
        "registered_app_count": 0,
        "watched_apps": {},
    }
    if not path.is_file():
        return out
    try:
        with path.open("rb") as handle:
            data = plistlib.load(handle)
    except Exception as exc:
        out["error"] = str(exc)
        return out
    apps = data.get("apps") or []
    if not isinstance(apps, list):
        return out
    out["registered_app_count"] = len(apps)
    watched_set = set(watched)
    for entry in apps:
        if not isinstance(entry, dict):
            continue
        bundle_id = str(entry.get("bundle-id") or "").strip()
        if bundle_id not in watched_set:
            continue
        flags = int(entry.get("flags") or 0)
        out["watched_apps"][bundle_id] = {
            "app_name": entry.get("app-name"),
            "flags": flags,
            "notifications_enabled": _notifications_enabled(flags),
        }
    return out


def main():
    watched = json.loads(os.environ.get("MATRAIX_WATCHED_BUNDLES", "[]"))
    payload = {
        "focus": _read_focus(),
        "legacy_do_not_disturb": _read_legacy_dnd(),
        "notifications": _read_ncprefs(watched),
        "daemons": {
            "usernoted_running": _run(["pgrep", "-x", "usernoted"])[0] == 0,
            "notification_center_running": _run(["pgrep", "-x", "NotificationCenter"])[0] == 0,
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
"""


async def run_macos_notification_probe(
    environment: Any,
    *,
    watched_bundle_ids: tuple[str, ...] = _WATCHED_BUNDLE_IDS,
) -> dict[str, Any]:
    """Execute the probe on a remote macOS sandbox and return parsed JSON."""
    bundles_json = json.dumps(list(watched_bundle_ids))
    command = (
        f"MATRAIX_WATCHED_BUNDLES={shlex.quote(bundles_json)} "
        f"python3 <<'PY'\n{_MACOS_PROBE_SCRIPT}\nPY"
    )
    result = await environment.exec(command, timeout_sec=45)
    return_code = int(getattr(result, "return_code", 1))
    stdout = (getattr(result, "stdout", None) or "").strip()
    stderr = (getattr(result, "stderr", None) or "").strip()

    if return_code != 0:
        return {
            "probe_ok": False,
            "probe_error": stderr or stdout or f"exit {return_code}",
        }
    if not stdout:
        return {"probe_ok": False, "probe_error": "empty probe stdout"}

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "probe_ok": False,
            "probe_error": "invalid probe json",
            "stdout_snippet": stdout[:300],
        }
    return {"probe_ok": True, **payload}

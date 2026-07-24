"""Remote iOS Simulator probes for notification telemetry on the Mac host."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any


# Bundles aligned with production os-app iOS tasks (News+, Photos, Settings).
_WATCHED_BUNDLE_IDS = (
    "com.apple.news",
    "com.apple.mobileslideshow",
    "com.apple.Preferences",
)


def short_sim_id(value: str) -> str:
    if not value:
        return ""
    if value.startswith("com.apple.CoreSimulator."):
        parts = value.split(".")
        if len(parts) >= 2:
            return parts[-1]
    return value


def normalize_match_token(value: str) -> str:
    """Collapse iOS-26-4 / iOS 26.4 / iPhone-17 into comparable tokens."""
    token = short_sim_id(value).lower()
    return re.sub(r"[^a-z0-9]+", "", token)


def device_name_matches(device_name: str, device_type_hint: str) -> bool:
    if not device_type_hint:
        return True
    name_token = normalize_match_token(device_name)
    hint_token = normalize_match_token(device_type_hint)
    if not hint_token:
        return True
    return hint_token in name_token or name_token in hint_token


def device_record_matches(device: dict[str, Any], device_type_hint: str) -> bool:
    if not device_type_hint:
        return True
    if device_name_matches(str(device.get("name") or ""), device_type_hint):
        return True
    dtype = str(
        device.get("deviceTypeIdentifier")
        or device.get("deviceType")
        or device.get("model")
        or ""
    )
    if not dtype:
        return False
    dtype_token = normalize_match_token(dtype)
    hint_token = normalize_match_token(device_type_hint)
    return (
        dtype_token == hint_token
        or hint_token in dtype_token
        or dtype_token in hint_token
    )


def runtime_key_matches(runtime_key: str, runtime_hint: str) -> bool:
    if not runtime_hint:
        return True
    runtime_token = normalize_match_token(runtime_key)
    hint_token = normalize_match_token(runtime_hint)
    if not hint_token:
        return True
    return hint_token in runtime_token or runtime_token in hint_token


def select_booted_device(
    devices_by_runtime: dict[str, Any],
    *,
    device_type_hint: str = "",
    runtime_hint: str = "",
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Pick a booted simulator, preferring task.toml device/runtime hints."""
    booted_all: list[dict[str, str]] = []
    booted_hinted: list[dict[str, str]] = []

    for runtime_key, devices in devices_by_runtime.items():
        if not isinstance(devices, list):
            continue
        for device in devices:
            if not isinstance(device, dict):
                continue
            if str(device.get("state") or "").lower() != "booted":
                continue
            record = {
                "udid": str(device.get("udid") or ""),
                "name": str(device.get("name") or ""),
                "runtime": str(runtime_key),
                "state": str(device.get("state") or ""),
            }
            booted_all.append(record)
            name_ok = device_record_matches(device, device_type_hint)
            runtime_ok = runtime_key_matches(record["runtime"], runtime_hint)
            if name_ok and runtime_ok:
                booted_hinted.append(record)

    if booted_hinted:
        meta: dict[str, Any] = {}
        if len(booted_hinted) > 1:
            meta["booted_matches"] = booted_hinted
            meta["ambiguous"] = True
        return booted_hinted[0], meta

    if booted_all:
        meta = {
            "hint_fallback": True,
            "booted_count": len(booted_all),
        }
        if device_type_hint or runtime_hint:
            meta["hint_mismatch"] = {
                "device_type_hint": device_type_hint,
                "runtime_hint": runtime_hint,
            }
        if len(booted_all) > 1:
            meta["booted_matches"] = booted_all
            meta["ambiguous"] = True
        return booted_all[0], meta

    return None, {"simctl_error": "no booted simulators"}


def simulator_data_root_from_container_path(container_path: str, udid: str) -> Path | None:
    """Derive .../Devices/<udid>/data from a simctl get_app_container path."""
    raw = container_path.strip()
    if not raw:
        return None
    path = Path(raw)
    parts = path.parts
    try:
        udid_idx = parts.index(udid)
    except ValueError:
        return None
    if udid_idx + 1 >= len(parts) or parts[udid_idx + 1] != "data":
        return None
    return Path(*parts[: udid_idx + 2])


def section_info_candidates(data_root: Path) -> list[Path]:
    """Known BulletinBoard notification plist locations inside a simulator."""
    names = ("VersionedSectionInfo.plist", "SectionInfo.plist")
    bases = (
        data_root / "Library/BulletinBoard",
        data_root / "private/var/mobile/Library/BulletinBoard",
    )
    candidates: list[Path] = []
    for base in bases:
        for name in names:
            candidates.append(base / name)
    return candidates


def parse_plutil_section_text(text: str, watched: tuple[str, ...] | list[str]) -> dict[str, dict[str, Any]]:
    """Extract notification fields for watched bundles from ``plutil -p`` output."""
    watched_set = set(watched)
    out: dict[str, dict[str, Any]] = {}
    current_bundle: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        for bundle in watched_set:
            if bundle in stripped:
                current_bundle = bundle
                out.setdefault(bundle, {"source": "plutil_p"})
        if current_bundle is None:
            continue
        record = out[current_bundle]
        if "authorizationStatus" in stripped:
            match = re.search(r"=>\s*(-?\d+)", stripped)
            if match:
                status = int(match.group(1))
                record["authorization_status"] = status
                record["notifications_enabled"] = status >= 2
        if "allowsNotifications" in stripped:
            match = re.search(r"=>\s*(true|false|1|0)", stripped, re.IGNORECASE)
            if match:
                token = match.group(1).lower()
                enabled = token in {"true", "1"}
                record["allows_notifications"] = enabled
                record.setdefault("notifications_enabled", enabled)
    return {
        bundle: fields
        for bundle, fields in out.items()
        if len(fields) > 1
    }


def merge_watched_app_records(*sources: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for source in sources:
        for bundle, fields in source.items():
            merged.setdefault(bundle, {}).update(fields)
    return merged


def _has_notification_ground_truth(record: dict[str, Any]) -> bool:
    if record.get("notifications_enabled") is not None:
        return True
    if record.get("authorization_status") is not None:
        return True
    if record.get("allows_notifications") is not None:
        return True
    return False


def _load_nskeyedarchiver_script() -> str:
    return (Path(__file__).with_name("nskeyedarchiver.py")).read_text()


_IOS_PROBE_SCRIPT = r"""
import json
import os
import plistlib
import re
import subprocess
from pathlib import Path


def _run(cmd):
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except Exception as exc:
        return 1, "", str(exc)


def _short_sim_id(value: str) -> str:
    if not value:
        return ""
    if value.startswith("com.apple.CoreSimulator."):
        parts = value.split(".")
        if len(parts) >= 2:
            return parts[-1]
    return value


def _normalize_match_token(value: str) -> str:
    token = _short_sim_id(value).lower()
    return re.sub(r"[^a-z0-9]+", "", token)


def _device_name_matches(device_name: str, device_type_hint: str) -> bool:
    if not device_type_hint:
        return True
    name_token = _normalize_match_token(device_name)
    hint_token = _normalize_match_token(device_type_hint)
    if not hint_token:
        return True
    return hint_token in name_token or name_token in hint_token


def _device_record_matches(device: dict, device_type_hint: str) -> bool:
    if not device_type_hint:
        return True
    if _device_name_matches(str(device.get("name") or ""), device_type_hint):
        return True
    dtype = str(
        device.get("deviceTypeIdentifier")
        or device.get("deviceType")
        or device.get("model")
        or ""
    )
    if not dtype:
        return False
    dtype_token = _normalize_match_token(dtype)
    hint_token = _normalize_match_token(device_type_hint)
    return (
        dtype_token == hint_token
        or hint_token in dtype_token
        or dtype_token in hint_token
    )


def _runtime_key_matches(runtime_key: str, runtime_hint: str) -> bool:
    if not runtime_hint:
        return True
    runtime_token = _normalize_match_token(runtime_key)
    hint_token = _normalize_match_token(runtime_hint)
    if not hint_token:
        return True
    return hint_token in runtime_token or runtime_token in hint_token


def _find_booted_device(device_type_hint: str, runtime_hint: str):
    rc, stdout, stderr = _run(["xcrun", "simctl", "list", "devices", "-j"])
    if rc != 0:
        return None, {"simctl_error": stderr or stdout or f"exit {rc}"}
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return None, {"simctl_error": f"invalid json: {exc}"}

    devices_by_runtime = payload.get("devices") or {}
    if not isinstance(devices_by_runtime, dict):
        return None, {"simctl_error": "missing devices map"}

    booted_all = []
    booted_hinted = []
    for runtime_key, devices in devices_by_runtime.items():
        if not isinstance(devices, list):
            continue
        for device in devices:
            if not isinstance(device, dict):
                continue
            if str(device.get("state") or "").lower() != "booted":
                continue
            record = {
                "udid": str(device.get("udid") or ""),
                "name": str(device.get("name") or ""),
                "runtime": str(runtime_key),
                "state": str(device.get("state") or ""),
            }
            booted_all.append(record)
            if _device_record_matches(device, device_type_hint) and _runtime_key_matches(
                record["runtime"], runtime_hint
            ):
                booted_hinted.append(record)

    if booted_hinted:
        meta = {}
        if len(booted_hinted) > 1:
            meta["booted_matches"] = booted_hinted
            meta["ambiguous"] = True
        return booted_hinted[0], meta

    if booted_all:
        meta = {"hint_fallback": True, "booted_count": len(booted_all)}
        if device_type_hint or runtime_hint:
            meta["hint_mismatch"] = {
                "device_type_hint": device_type_hint,
                "runtime_hint": runtime_hint,
            }
        if len(booted_all) > 1:
            meta["booted_matches"] = booted_all
            meta["ambiguous"] = True
        return booted_all[0], meta

    return None, {"simctl_error": "no booted simulators"}


def _section_notifications_enabled(section: dict) -> bool | None:
    if not isinstance(section, dict):
        return None
    if "allowsNotifications" in section:
        return bool(section.get("allowsNotifications"))
    status = section.get("authorizationStatus")
    if status is None:
        return None
    try:
        return int(status) >= 2
    except (TypeError, ValueError):
        return None


def _simulator_data_root(udid: str):
    for bundle_id in (
        "com.apple.Preferences",
        "com.apple.mobilesafari",
        "com.apple.springboard",
    ):
        rc, stdout, stderr = _run(
            ["xcrun", "simctl", "get_app_container", udid, bundle_id, "data"]
        )
        if rc != 0 or not stdout:
            continue
        parts = Path(stdout.strip()).parts
        try:
            udid_idx = parts.index(udid)
        except ValueError:
            continue
        if udid_idx + 1 < len(parts) and parts[udid_idx + 1] == "data":
            return Path(*parts[: udid_idx + 2])
    fallback = (
        Path.home()
        / "Library/Developer/CoreSimulator/Devices"
        / udid
        / "data"
    )
    if fallback.is_dir():
        return fallback
    return None


def _find_bulletin_plist_paths(data_root: Path):
    names = ("VersionedSectionInfo.plist", "SectionInfo.plist")
    bases = (
        data_root / "Library/BulletinBoard",
        data_root / "private/var/mobile/Library/BulletinBoard",
    )
    found = []
    seen = set()
    for base in bases:
        for name in names:
            candidate = base / name
            if candidate.is_file():
                key = str(candidate)
                if key not in seen:
                    seen.add(key)
                    found.append(candidate)
        if base.is_dir():
            for name in names:
                for candidate in base.glob(f"**/{name}"):
                    if candidate.is_file():
                        key = str(candidate)
                        if key not in seen:
                            seen.add(key)
                            found.append(candidate)
    return found


def _parse_plutil_section_text(text: str, watched: list[str]):
    watched_set = set(watched)
    out = {}
    current_bundle = None
    for line in text.splitlines():
        stripped = line.strip()
        for bundle in watched_set:
            if bundle in stripped:
                current_bundle = bundle
                out.setdefault(bundle, {"source": "plutil_p"})
        if current_bundle is None:
            continue
        record = out[current_bundle]
        if "authorizationStatus" in stripped:
            match = re.search(r"=>\s*(-?\d+)", stripped)
            if match:
                status = int(match.group(1))
                record["authorization_status"] = status
                record["notifications_enabled"] = status >= 2
        if "allowsNotifications" in stripped:
            match = re.search(r"=>\s*(true|false|1|0)", stripped, re.IGNORECASE)
            if match:
                token = match.group(1).lower()
                enabled = token in {"true", "1"}
                record["allows_notifications"] = enabled
                record.setdefault("notifications_enabled", enabled)
    return {bundle: fields for bundle, fields in out.items() if len(fields) > 1}


def _parse_simple_section_dict(data: dict, watched: list[str]):
    watched_set = set(watched)
    out = {}
    for bundle_id, section in data.items():
        bundle = str(bundle_id)
        if bundle not in watched_set:
            continue
        section_dict = section if isinstance(section, dict) else {}
        out[bundle] = {
            "source": "section_plist",
            "allows_notifications": section_dict.get("allowsNotifications"),
            "authorization_status": section_dict.get("authorizationStatus"),
            "notifications_enabled": _section_notifications_enabled(section_dict),
            "display_name": section_dict.get("displayName")
            or section_dict.get("sectionDisplayName"),
        }
    return out


def _parse_bulletin_plist(path: Path, watched: list[str]):
    parsed, section_count, source = parse_bulletin_notifications_from_path(path, watched)
    if parsed:
        return parsed, section_count, source

    rc, stdout, stderr = _run(["plutil", "-p", str(path)])
    if rc == 0 and stdout:
        parsed = _parse_plutil_section_text(stdout, watched)
        if parsed:
            return parsed, len(parsed), "plutil_p"
    return {}, 0, None


def _read_spawn_bulletin(udid: str, watched: list[str]):
    paths = (
        "/var/mobile/Library/BulletinBoard/VersionedSectionInfo.plist",
        "/var/mobile/Library/BulletinBoard/SectionInfo.plist",
    )
    for rel in paths:
        rc, stdout, stderr = _run(
            ["xcrun", "simctl", "spawn", udid, "plutil", "-p", rel]
        )
        if rc != 0 or not stdout:
            continue
        parsed = _parse_plutil_section_text(stdout, watched)
        if parsed:
            return parsed, rel, "spawn_plutil"
    return {}, None, None


def _bulletin_inventory(data_root: Path):
    inventory = {}
    for label, base in (
        ("host_library", data_root / "Library/BulletinBoard"),
        ("host_mobile", data_root / "private/var/mobile/Library/BulletinBoard"),
    ):
        if not base.is_dir():
            inventory[label] = {"exists": False}
            continue
        names = sorted(p.name for p in base.iterdir() if p.is_file())
        inventory[label] = {"exists": True, "files": names[:20], "file_count": len(names)}
    return inventory


def _read_tcc_notifications(data_root: Path, watched: list[str]):
    tcc_path = data_root / "Library/TCC/TCC.db"
    if not tcc_path.is_file():
        tcc_path = data_root / "private/var/mobile/Library/TCC/TCC.db"
    if not tcc_path.is_file():
        return {}

    client_list = ",".join(f"'{client}'" for client in watched)
    queries = [
        (
            "client_filter",
            (
                "SELECT client, service, auth_value FROM access "
                f"WHERE client IN ({client_list});"
            ),
        ),
        (
            "notification_services",
            (
                "SELECT client, service, auth_value FROM access "
                "WHERE lower(service) LIKE '%notif%';"
            ),
        ),
    ]
    out: dict[str, object] = {}
    for label, query in queries:
        rc, stdout, stderr = _run(["sqlite3", str(tcc_path), query])
        if rc != 0 or not stdout.strip():
            continue
        watched_set = set(watched)
        for line in stdout.splitlines():
            parts = line.split("|")
            if len(parts) != 3:
                continue
            client, service, auth_value = parts
            if label == "client_filter" and client not in watched_set:
                continue
            if label == "notification_services" and client not in watched_set:
                continue
            try:
                auth_int = int(auth_value)
            except ValueError:
                auth_int = None
            record = out.setdefault(
                client,
                {"source": "tcc", "services": {}},
            )
            services = record.setdefault("services", {})
            services[service] = auth_int
            if "notif" in service.lower():
                record["tcc_service"] = service
                record["auth_value"] = auth_int
                record["notifications_enabled"] = (
                    auth_int == 2 if auth_int is not None else None
                )
    return out


def _has_notification_ground_truth(record: dict) -> bool:
    if record.get("notifications_enabled") is not None:
        return True
    if record.get("authorization_status") is not None:
        return True
    if record.get("allows_notifications") is not None:
        return True
    return False


def _read_section_info(udid: str, watched: list[str]):
    data_root = _simulator_data_root(udid)
    out: dict[str, object] = {
        "available": False,
        "section_count": 0,
        "watched_apps": {},
        "data_root": str(data_root) if data_root else None,
        "sources": [],
    }
    if data_root is None:
        out["error"] = "simulator data root not found"
        return out

    out["bulletin_inventory"] = _bulletin_inventory(data_root)
    watched_apps: dict[str, object] = {}
    sources: list[str] = []
    bulletin_parsed: dict[str, object] = {}
    paths = _find_bulletin_plist_paths(data_root)
    out["paths"] = [str(path) for path in paths]

    for path in paths:
        parsed, section_count, source = _parse_bulletin_plist(path, watched)
        if parsed:
            bulletin_parsed.update(parsed)
            if source:
                sources.append(source)
            out["section_count"] = max(int(out.get("section_count") or 0), section_count)
            out["path"] = str(path)
            break

    if not bulletin_parsed:
        spawn_parsed, spawn_path, spawn_source = _read_spawn_bulletin(udid, watched)
        if spawn_parsed:
            bulletin_parsed.update(spawn_parsed)
            if spawn_source:
                sources.append(spawn_source)
            out["spawn_path"] = spawn_path
            out["section_count"] = len(spawn_parsed)

    tcc: dict[str, object] = {}
    if bulletin_parsed:
        watched_apps.update(bulletin_parsed)
        missing = [
            bundle
            for bundle in watched
            if bundle not in bulletin_parsed
            or not _has_notification_ground_truth(bulletin_parsed.get(bundle, {}))
        ]
        if missing:
            tcc = _read_tcc_notifications(data_root, missing)
    else:
        tcc = _read_tcc_notifications(data_root, watched)

    if tcc:
        for bundle, fields in tcc.items():
            existing = watched_apps.get(bundle)
            if existing is None:
                watched_apps[bundle] = fields
            elif not _has_notification_ground_truth(existing):
                if isinstance(existing, dict) and isinstance(fields, dict):
                    existing.update(fields)
                else:
                    watched_apps[bundle] = fields
        if not bulletin_parsed:
            sources.append("tcc")
        out["tcc_fallback"] = tcc

    if watched_apps:
        out["available"] = True
        out["watched_apps"] = watched_apps
        out["sources"] = sources
    elif paths:
        out["path"] = str(paths[0])
    return out


def main():
    device_type_hint = os.environ.get("MATRAIX_IOS_DEVICE_TYPE", "")
    runtime_hint = os.environ.get("MATRAIX_IOS_RUNTIME", "")
    watched = json.loads(os.environ.get("MATRAIX_WATCHED_BUNDLES", "[]"))

    device, meta = _find_booted_device(device_type_hint, runtime_hint)
    payload: dict[str, object] = {
        "simulator": device or {},
        "simulator_meta": meta,
    }
    if device and device.get("udid"):
        udid = str(device["udid"])
        payload["notifications"] = _read_section_info(udid, watched)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
"""


async def run_ios_notification_probe(
    environment: Any,
    *,
    watched_bundle_ids: tuple[str, ...] = _WATCHED_BUNDLE_IDS,
    device_type: str = "",
    runtime: str = "",
) -> dict[str, Any]:
    """Execute the probe on the simulator Mac host and return parsed JSON."""
    bundles_json = json.dumps(list(watched_bundle_ids))
    env_parts = [f"MATRAIX_WATCHED_BUNDLES={shlex.quote(bundles_json)}"]
    if device_type:
        env_parts.append(f"MATRAIX_IOS_DEVICE_TYPE={shlex.quote(device_type)}")
    if runtime:
        env_parts.append(f"MATRAIX_IOS_RUNTIME={shlex.quote(runtime)}")
    command = (
        " ".join(env_parts)
        + " python3 <<'PY'\n"
        + _load_nskeyedarchiver_script()
        + "\n"
        + _IOS_PROBE_SCRIPT
        + "\nPY"
    )
    result = await environment.exec(command, timeout_sec=90)
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

"""Parse iOS Simulator BulletinBoard notification plists on the Mac host.

``VersionedSectionInfo.plist`` (sectionInfoVersionNumber >= 2) stores one
NSKeyedArchiver blob per bundle under ``sectionInfo[bundle_id]``. Each blob
deserializes to ``BBSectionInfo`` with ``sectionInfoSettings`` containing
``authorizationStatus`` and related notification toggles.

Legacy ``SectionInfo.plist`` is a flat bundle-id -> settings dictionary.
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from plistlib import UID
from typing import Any


def _uid_index(value: Any) -> int | None:
    if isinstance(value, UID):
        return value.data
    return None


def _resolve_uid(value: Any, objects: list[Any]) -> Any:
    idx = _uid_index(value)
    if idx is None:
        return value
    if idx < 0 or idx >= len(objects):
        return None
    return objects[idx]


def notifications_enabled_from_settings(settings: dict[str, Any]) -> bool | None:
    allows = settings.get("allowsNotifications")
    if isinstance(allows, bool):
        return allows
    status = settings.get("authorizationStatus")
    if isinstance(status, bool):
        return status
    if isinstance(status, int):
        # UNAuthorizationStatusAuthorized == 2
        return status >= 2
    shows_nc = settings.get("showsInNotificationCenter")
    shows_ls = settings.get("showsInLockScreen")
    if isinstance(shows_nc, bool) or isinstance(shows_ls, bool):
        return bool(shows_nc) or bool(shows_ls)
    return None


def extract_bb_section_from_nska(nska: dict[str, Any]) -> dict[str, Any]:
    """Read BBSectionInfo + BBSectionInfoSettings from an NSKeyedArchiver dict."""
    if nska.get("$archiver") != "NSKeyedArchiver":
        return {}
    objects = nska.get("$objects")
    if not isinstance(objects, list):
        return {}

    settings: dict[str, Any] | None = None
    section_id: str | None = None
    display_name: str | None = None

    for obj in objects:
        if isinstance(obj, str):
            continue
        if not isinstance(obj, dict):
            continue

        class_info = obj.get("$class")
        class_name = (
            class_info.get("$classname")
            if isinstance(class_info, dict)
            else None
        )
        if class_name == "BBSectionInfoSettings":
            settings = obj
            continue

        if "sectionInfoSettings" in obj:
            settings_ref = _resolve_uid(obj.get("sectionInfoSettings"), objects)
            if isinstance(settings_ref, dict):
                settings = settings_ref
        if "sectionID" in obj:
            section_ref = _resolve_uid(obj.get("sectionID"), objects)
            if isinstance(section_ref, str):
                section_id = section_ref
        for name_key in ("displayName", "appName"):
            if name_key in obj:
                name_ref = _resolve_uid(obj.get(name_key), objects)
                if isinstance(name_ref, str) and name_ref != "$null":
                    display_name = name_ref

    if settings is None:
        return {}

    record: dict[str, Any] = {
        "source": "versioned_section_info",
        "section_id": section_id,
        "display_name": display_name,
        "authorization_status": settings.get("authorizationStatus"),
        "allows_notifications": settings.get("allowsNotifications"),
        "notifications_enabled": notifications_enabled_from_settings(settings),
        "alert_type": settings.get("alertType"),
        "lock_screen_setting": settings.get("lockScreenSetting"),
        "notification_center_setting": settings.get("notificationCenterSetting"),
        "shows_in_notification_center": settings.get("showsInNotificationCenter"),
        "shows_in_lock_screen": settings.get("showsInLockScreen"),
    }
    return {key: value for key, value in record.items() if value is not None}


def parse_section_info_dict(data: dict[str, Any], watched: tuple[str, ...] | list[str]) -> dict[str, dict[str, Any]]:
    """Parse legacy flat ``SectionInfo.plist`` {bundle: settings}."""
    watched_set = set(watched)
    out: dict[str, dict[str, Any]] = {}
    for bundle_id, section in data.items():
        if str(bundle_id).startswith("$"):
            continue
        bundle = str(bundle_id)
        if bundle not in watched_set:
            continue
        section_dict = section if isinstance(section, dict) else {}
        out[bundle] = {
            "source": "section_plist",
            "allows_notifications": section_dict.get("allowsNotifications"),
            "authorization_status": section_dict.get("authorizationStatus"),
            "notifications_enabled": notifications_enabled_from_settings(section_dict),
            "display_name": section_dict.get("displayName")
            or section_dict.get("sectionDisplayName"),
        }
    return out


def parse_versioned_section_info(
    data: dict[str, Any],
    watched: tuple[str, ...] | list[str],
) -> dict[str, dict[str, Any]]:
    """Parse ``VersionedSectionInfo.plist`` {sectionInfo: {bundle: nska-bytes}}."""
    section_info = data.get("sectionInfo")
    if not isinstance(section_info, dict):
        return {}

    watched_set = set(watched)
    out: dict[str, dict[str, Any]] = {}
    for bundle_id, payload in section_info.items():
        bundle = str(bundle_id)
        if bundle not in watched_set:
            continue
        nska: dict[str, Any] | None = None
        if isinstance(payload, (bytes, bytearray)):
            try:
                loaded = plistlib.loads(payload)
            except Exception:
                continue
            nska = loaded if isinstance(loaded, dict) else None
        elif isinstance(payload, dict):
            nska = payload
        if not nska:
            continue
        record = extract_bb_section_from_nska(nska)
        if not record:
            continue
        record.setdefault("section_id", bundle)
        out[bundle] = record
    return out


def parse_bulletin_notifications_from_bytes(
    raw: bytes,
    watched: tuple[str, ...] | list[str],
) -> tuple[dict[str, dict[str, Any]], int, str | None]:
    """Parse a BulletinBoard plist payload and return (watched_apps, section_count, source)."""
    try:
        data = plistlib.loads(raw)
    except Exception:
        return {}, 0, None
    if not isinstance(data, dict):
        return {}, 0, None
    return parse_bulletin_notifications_from_dict(data, watched)


def parse_bulletin_notifications_from_dict(
    data: dict[str, Any],
    watched: tuple[str, ...] | list[str],
) -> tuple[dict[str, dict[str, Any]], int, str | None]:
    if "sectionInfo" in data:
        parsed = parse_versioned_section_info(data, watched)
        section_count = len(data.get("sectionInfo") or {})
        return parsed, section_count, "versioned_section_info"

    if data.get("$archiver") == "NSKeyedArchiver":
        # Some hosts may store a single archived root instead of sectionInfo map.
        top = data.get("$top") or {}
        root_ref = top.get("root")
        if _uid_index(root_ref) is not None:
            root_obj = _resolve_uid(root_ref, data.get("$objects") or [])
            if isinstance(root_obj, dict) and isinstance(root_obj.get("sectionInfo"), dict):
                wrapped = {"sectionInfo": {}}
                for bundle, value in root_obj["sectionInfo"].items():
                    if isinstance(value, (bytes, bytearray)):
                        wrapped["sectionInfo"][bundle] = value
                    elif isinstance(value, dict) and value.get("$archiver"):
                        wrapped["sectionInfo"][bundle] = plistlib.dumps(value)
                parsed = parse_versioned_section_info(wrapped, watched)
                return parsed, len(wrapped["sectionInfo"]), "versioned_section_info"

    if not any(str(key).startswith("$") for key in data.keys()):
        parsed = parse_section_info_dict(data, watched)
        if parsed:
            return parsed, len(data), "section_plist"

    return {}, 0, None


def parse_bulletin_notifications_from_path(
    path: Path | str,
    watched: tuple[str, ...] | list[str],
) -> tuple[dict[str, dict[str, Any]], int, str | None]:
    plist_path = Path(path)
    try:
        with plist_path.open("rb") as handle:
            data = plistlib.load(handle)
    except Exception:
        return {}, 0, None
    if not isinstance(data, dict):
        return {}, 0, None
    return parse_bulletin_notifications_from_dict(data, watched)

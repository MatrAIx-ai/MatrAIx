from __future__ import annotations

from pathlib import Path

import pytest

from harbor.telemetry.nskeyedarchiver import (
    extract_bb_section_from_nska,
    notifications_enabled_from_settings,
    parse_bulletin_notifications_from_path,
    parse_versioned_section_info,
)

_LOCAL_VERSIONED = Path(
    "/Users/aravindmohan/Library/Developer/CoreSimulator/Devices/"
    "34448552-9FD0-4544-86FE-9EA2B2C86A2F/data/Library/BulletinBoard/VersionedSectionInfo.plist"
)

_WATCHED = (
    "com.apple.MobileSMS",
    "com.apple.mobilemail",
    "com.apple.mobilesafari",
)


def test_notifications_enabled_from_settings_prefers_authorization_status() -> None:
    assert notifications_enabled_from_settings({"authorizationStatus": 2}) is True
    assert notifications_enabled_from_settings({"authorizationStatus": 1}) is False
    assert notifications_enabled_from_settings({"allowsNotifications": True}) is True


def test_parse_synthetic_versioned_section_info() -> None:
    from plistlib import UID

    objects = [
        "$null",
        {
            "sectionID": UID(2),
            "sectionInfoSettings": UID(3),
            "displayName": UID(4),
            "$class": {"$classname": "BBSectionInfo"},
        },
        "com.apple.MobileSMS",
        {
            "authorizationStatus": 2,
            "showsInNotificationCenter": True,
            "alertType": 1,
            "$class": {"$classname": "BBSectionInfoSettings"},
        },
        "Messages",
    ]
    nska = {
        "$archiver": "NSKeyedArchiver",
        "$version": 100000,
        "$objects": objects,
        "$top": {"root": UID(1)},
    }
    root = {
        "sectionInfo": {"com.apple.MobileSMS": nska},
        "sectionInfoVersionNumber": 2,
    }
    parsed = parse_versioned_section_info(root, ["com.apple.MobileSMS"])
    assert parsed["com.apple.MobileSMS"]["authorization_status"] == 2
    assert parsed["com.apple.MobileSMS"]["notifications_enabled"] is True
    assert parsed["com.apple.MobileSMS"]["display_name"] == "Messages"


@pytest.mark.skipif(not _LOCAL_VERSIONED.is_file(), reason="local simulator plist missing")
def test_parse_local_versioned_section_info_messages() -> None:
    parsed, section_count, source = parse_bulletin_notifications_from_path(
        _LOCAL_VERSIONED,
        _WATCHED,
    )
    assert source == "versioned_section_info"
    assert section_count >= 1
    messages = parsed["com.apple.MobileSMS"]
    assert messages["authorization_status"] == 2
    assert messages["notifications_enabled"] is True
    assert messages.get("display_name") == "Messages"


@pytest.mark.skipif(not _LOCAL_VERSIONED.is_file(), reason="local simulator plist missing")
def test_extract_bb_section_from_nested_blob() -> None:
    import plistlib

    root = plistlib.load(_LOCAL_VERSIONED.open("rb"))
    blob = root["sectionInfo"]["com.apple.MobileSMS"]
    nska = plistlib.loads(blob)
    record = extract_bb_section_from_nska(nska)
    assert record["authorization_status"] == 2
    assert record["notifications_enabled"] is True


def test_parse_versioned_section_info_handles_in_memory_payload() -> None:
    import plistlib

    if not _LOCAL_VERSIONED.is_file():
        pytest.skip("local simulator plist missing")
    root = plistlib.load(_LOCAL_VERSIONED.open("rb"))
    parsed = parse_versioned_section_info(root, ["com.apple.MobileSMS"])
    assert parsed["com.apple.MobileSMS"]["notifications_enabled"] is True

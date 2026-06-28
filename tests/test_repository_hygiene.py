from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_LOCAL_PATHS = (
    "/data2" + "/zonglin",
    "/home" + "/zdi",
    "/tmp" + "/personabench_full_matraix_migration",
)


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / name.decode("utf-8")
        for name in result.stdout.split(b"\0")
        if name
    ]


def test_tracked_files_do_not_reference_developer_local_paths() -> None:
    violations: list[str] = []
    for path in _tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for local_path in FORBIDDEN_LOCAL_PATHS:
            if local_path in text:
                violations.append(f"{path.relative_to(ROOT)} contains {local_path}")

    assert violations == []

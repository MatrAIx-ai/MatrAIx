import asyncio
import sys
from pathlib import Path

import yaml

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "environment" / "runtime"))

from harbor.utils.crew_personas import (
    container_path_for_persona,
    find_crew_manifest,
    persona_paths_from_manifest,
    upload_crew_personas_for_task,
)


def test_find_crew_manifest(tmp_path: Path) -> None:
    task_dir = tmp_path / "game-starclash"
    (task_dir / "input").mkdir(parents=True)
    manifest = task_dir / "input" / "crew_manifest.yaml"
    manifest.write_text("persona_paths: []\n", encoding="utf-8")
    assert find_crew_manifest(task_dir) == manifest
    assert find_crew_manifest(tmp_path / "other") is None


def test_persona_paths_from_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "crew_manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "persona_paths": [
                    "persona/datasets/bench-dev-sample/persona_0042.yaml",
                    "persona/datasets/bench-dev-sample/persona_0229.yaml",
                ],
                "hand_size": 4,
            }
        ),
        encoding="utf-8",
    )
    assert persona_paths_from_manifest(manifest) == [
        "persona/datasets/bench-dev-sample/persona_0042.yaml",
        "persona/datasets/bench-dev-sample/persona_0229.yaml",
    ]


def test_container_path_for_persona() -> None:
    assert (
        container_path_for_persona("persona/datasets/bench-dev-sample/persona_0042.yaml")
        == "/app/persona/datasets/bench-dev-sample/persona_0042.yaml"
    )


def test_upload_crew_personas_for_task(tmp_path: Path) -> None:
    asyncio.run(_test_upload_crew_personas_for_task(tmp_path))


async def _test_upload_crew_personas_for_task(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    persona_dir = repo_root / "persona" / "datasets" / "bench-dev-sample"
    persona_dir.mkdir(parents=True)
    persona_file = persona_dir / "persona_0042.yaml"
    persona_file.write_text("persona_id: '0042'\n", encoding="utf-8")

    (repo_root / "environment" / "task-environments").mkdir(parents=True)
    task_dir = repo_root / "application" / "tasks" / "game-starclash"
    (task_dir / "input").mkdir(parents=True)
    (task_dir / "input" / "crew_manifest.yaml").write_text(
        yaml.safe_dump(
            {"persona_paths": ["persona/datasets/bench-dev-sample/persona_0042.yaml"]}
        ),
        encoding="utf-8",
    )

    uploads: list[tuple[Path, str]] = []

    class _Env:
        async def upload_file(self, source_path: Path | str, target_path: str) -> None:
            uploads.append((Path(source_path), target_path))

    count = await upload_crew_personas_for_task(_Env(), task_dir)
    assert count == 1
    assert uploads == [
        (
            persona_file.resolve(),
            "/app/persona/datasets/bench-dev-sample/persona_0042.yaml",
        )
    ]
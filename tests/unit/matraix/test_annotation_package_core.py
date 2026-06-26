from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from persona.tools.annotation_package.core import (
    build_annotation_package,
    filter_dimensions,
    load_dimensions,
    parse_range,
)


def _write_minimal_collab_kit(path: Path) -> None:
    path.mkdir()
    for name in (
        "assignment_runner.py",
        "backends.py",
        "claude_json_backend.py",
        "codex_json_backend.py",
        "conformance.py",
        "harness.py",
        "solver.py",
    ):
        (path / name).write_text(f"# {name}\n", encoding="utf-8")
    schemas = path / "schemas"
    schemas.mkdir()
    (schemas / "result.output.schema.json").write_text("{}", encoding="utf-8")


def test_parse_range_requires_half_open_start_end() -> None:
    assert parse_range("10:20") == (10, 20)
    with pytest.raises(ValueError, match="START:END"):
        parse_range("10")
    with pytest.raises(ValueError, match="0 <= start < end"):
        parse_range("20:10")


def test_filter_dimensions_accepts_names_and_slugs() -> None:
    dims = load_dimensions(Path("persona/dimensions.json"))

    by_name = filter_dimensions(dims, ["Demographic: Core"])
    by_slug = filter_dimensions(dims, ["demographic_core"])

    assert by_name
    assert [dim["id"] for dim in by_name] == [dim["id"] for dim in by_slug]
    assert all(dim["category"] == "Demographic: Core" for dim in by_name)


def test_build_annotation_package_writes_manifest_and_foldered_archive(
    tmp_path: Path,
) -> None:
    collab_kit = tmp_path / "collab_kit_src"
    launcher = tmp_path / "run_assignment.sh"
    _write_minimal_collab_kit(collab_kit)
    launcher.write_text(
        "#!/usr/bin/env bash\npython3 collab_kit/assignment_runner.py \"$@\"\n"
    )

    out_dir = tmp_path / "A_0_2_worker"
    tasks = [
        {
            "global_idx": 0,
            "task_id": "wiki_profile:0000000000",
            "qid": "Q1",
            "title": "Ada Example",
            "source_url": "https://example.test/Q1",
            "profile_text": "Ada Example is a mathematician.",
            "input_sha256": "a" * 64,
        },
        {
            "global_idx": 1,
            "task_id": "wiki_profile:0000000001",
            "qid": "Q2",
            "title": "Grace Example",
            "source_url": "https://example.test/Q2",
            "profile_text": "Grace Example is a computer scientist.",
            "input_sha256": "b" * 64,
        },
    ]
    dimensions = [
        {
            "id": "domain",
            "label": "Domain",
            "category": "Expertise: Domains",
            "description": "Primary field.",
            "values": ["Software & AI", "Mathematics"],
        }
    ]

    summary = build_annotation_package(
        task_rows=tasks,
        dimensions=dimensions,
        out_dir=out_dir,
        assignment_id="A_0_2",
        worker_id="worker",
        dataset_id="test-dataset",
        dataset_sha256="c" * 64,
        range_start=0,
        range_end=2,
        source="wiki",
        collab_kit_src=collab_kit,
        root_launcher_src=launcher,
        create_archive=True,
    )

    assert summary["task_count"] == 2
    assert summary["dimension_count"] == 1
    assert Path(summary["archive_path"]).is_file()

    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["source"] == "wiki"
    assert assignment["range_start"] == 0
    assert assignment["range_end"] == 2
    assert len(assignment["tasks_sha256"]) == 64

    manifest = json.loads(
        (out_dir / "package_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["assignment"]["assignment_id"] == "A_0_2"
    assert manifest["files"]["tasks.jsonl"]["mode"] == "immutable"
    assert manifest["files"]["collab_kit/solver.py"]["mode"] == "editable"

    with tarfile.open(summary["archive_path"], "r:gz") as tar:
        names = [member.name for member in tar.getmembers()]
    assert "A_0_2_worker/assignment.json" in names
    assert "A_0_2_worker/tasks.jsonl" in names
    assert len(names) == len(set(names))

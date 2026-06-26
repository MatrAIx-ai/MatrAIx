from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIMENSIONS = REPO_ROOT / "persona" / "dimensions.json"
DEFAULT_COLLAB_KIT_SRC = Path(__file__).resolve().parent / "collab_kit"
DEFAULT_ROOT_LAUNCHER_SRC = Path(__file__).resolve().parent / "run_assignment.sh"
SLUG_RE = re.compile(r"[^a-z0-9]+")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_range(raw: str) -> tuple[int, int]:
    try:
        start_s, end_s = raw.split(":", 1)
        start = int(start_s)
        end = int(end_s)
    except Exception as exc:
        raise ValueError(f"range must be START:END, got {raw!r}") from exc
    if start < 0 or end <= start:
        raise ValueError(f"range must satisfy 0 <= start < end, got {raw!r}")
    return start, end


def slugify(value: str) -> str:
    slug = SLUG_RE.sub("_", value.strip().lower()).strip("_")
    return slug or "uncategorized"


def load_dimensions(dimensions_path: Path = DEFAULT_DIMENSIONS) -> list[dict[str, Any]]:
    payload = json.loads(dimensions_path.read_text(encoding="utf-8"))
    dimensions = payload.get("dimensions") if isinstance(payload, dict) else payload
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError(f"{dimensions_path}: expected a non-empty dimensions list")
    return [dict(item) for item in dimensions]


def filter_dimensions(
    dimensions: list[dict[str, Any]], categories: list[str] | None
) -> list[dict[str, Any]]:
    if not categories:
        return dimensions
    wanted = {item.strip() for item in categories if item.strip()}
    filtered = [
        dim
        for dim in dimensions
        if str(dim.get("category", "")) in wanted
        or slugify(str(dim.get("category", ""))) in wanted
    ]
    if not filtered:
        raise ValueError(f"no dimensions matched categories: {sorted(wanted)}")
    return filtered


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def prepare_out_dir(out_dir: Path, *, force: bool) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        if not force:
            raise FileExistsError(
                f"{out_dir} already exists and is not empty; use --force"
            )
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


def _ignore_collab_kit(_dir_path: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name == "__pycache__" or name.endswith(".pyc"):
            ignored.add(name)
        elif name == "worker_out" or name.endswith(".tar.gz"):
            ignored.add(name)
        elif name == "results.jsonl" or name.endswith(".progress.jsonl"):
            ignored.add(name)
    return ignored


def copy_collab_kit(out_dir: Path, collab_kit_src: Path) -> None:
    shutil.copytree(
        collab_kit_src,
        out_dir / "collab_kit",
        ignore=_ignore_collab_kit,
    )


def copy_root_launcher(out_dir: Path, root_launcher_src: Path) -> None:
    dst = out_dir / "run_assignment.sh"
    shutil.copy2(root_launcher_src, dst)
    dst.chmod(dst.stat().st_mode | 0o111)


def _manifest_file_entry(path: Path, *, root: Path, mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "path": str(path.relative_to(root)),
    }


def write_package_manifest(out_dir: Path, assignment: dict[str, Any]) -> None:
    immutable = [
        out_dir / "assignment.json",
        out_dir / "tasks.jsonl",
        out_dir / "dimensions.json",
        out_dir / "run_assignment.sh",
        out_dir / "collab_kit" / "harness.py",
        out_dir / "collab_kit" / "conformance.py",
        out_dir / "collab_kit" / "backends.py",
        out_dir / "collab_kit" / "assignment_runner.py",
        out_dir / "collab_kit" / "claude_json_backend.py",
        out_dir / "collab_kit" / "codex_json_backend.py",
    ]
    immutable.extend(sorted((out_dir / "collab_kit" / "schemas").glob("*.json")))

    files: dict[str, Any] = {}
    for path in immutable:
        if path.exists():
            rel = str(path.relative_to(out_dir))
            files[rel] = _manifest_file_entry(path, root=out_dir, mode="immutable")

    solver = out_dir / "collab_kit" / "solver.py"
    if solver.exists():
        rel = str(solver.relative_to(out_dir))
        files[rel] = _manifest_file_entry(solver, root=out_dir, mode="editable")

    manifest = {
        "manifest_version": 1,
        "assignment": {
            "assignment_id": assignment["assignment_id"],
            "worker_id": assignment["worker_id"],
            "dataset_id": assignment["dataset_id"],
            "dataset_sha256": assignment["dataset_sha256"],
            "range_start": assignment["range_start"],
            "range_end": assignment["range_end"],
            "task_count": assignment["task_count"],
            "dimension_count": assignment["dimension_count"],
            "categories": assignment["categories"],
            "source": assignment["source"],
        },
        "files": dict(sorted(files.items())),
    }
    write_json(out_dir / "package_manifest.json", manifest)


def write_worker_readme(out_dir: Path, *, source: str) -> None:
    readme = f"""# MatrAIx Persona Annotation Assignment

You received a self-contained annotation package for source `{source}`. Work
inside this directory and return only `results.jsonl` unless the owner asks for
logs.

```bash
./run_assignment.sh --status
./run_assignment.sh
./run_assignment.sh --validate
```

The runner verifies package integrity before running. `collab_kit/solver.py`
is editable starter code; package inputs and schemas are immutable.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")


def build_archive(out_dir: Path) -> Path:
    archive_path = out_dir.with_suffix(".tar.gz")
    if archive_path.exists():
        archive_path.unlink()
    top = out_dir.name
    with tarfile.open(archive_path, "w:gz") as tar:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                arcname = str(Path(top) / path.relative_to(out_dir))
                tar.add(path, arcname=arcname, recursive=False)
    return archive_path


def build_annotation_package(
    *,
    task_rows: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    out_dir: Path,
    assignment_id: str,
    worker_id: str,
    dataset_id: str,
    dataset_sha256: str,
    range_start: int,
    range_end: int,
    source: str,
    categories: list[str] | None = None,
    source_metadata: dict[str, Any] | None = None,
    collab_kit_src: Path = DEFAULT_COLLAB_KIT_SRC,
    root_launcher_src: Path = DEFAULT_ROOT_LAUNCHER_SRC,
    create_archive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    prepare_out_dir(out_dir, force=force)
    dimensions = filter_dimensions(dimensions, categories)

    tasks_path = out_dir / "tasks.jsonl"
    dimensions_out_path = out_dir / "dimensions.json"
    write_jsonl(tasks_path, task_rows)
    dimensions_out_path.write_text(
        json.dumps(dimensions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copy_collab_kit(out_dir, collab_kit_src)
    copy_root_launcher(out_dir, root_launcher_src)
    write_worker_readme(out_dir, source=source)

    assignment = {
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "range_start": range_start,
        "range_end": range_end,
        "task_count": len(task_rows),
        "dimension_count": len(dimensions),
        "categories": categories or "all",
        "source": source,
        "tasks_file": "tasks.jsonl",
        "tasks_sha256": sha256_file(tasks_path),
        "dimensions_file": "dimensions.json",
        "dimensions_sha256": sha256_file(dimensions_out_path),
        "kit": "collab_kit",
        "return_file": "results.jsonl",
    }
    if source_metadata:
        assignment.update(source_metadata)
    write_json(out_dir / "assignment.json", assignment)
    write_package_manifest(out_dir, assignment)
    archive_path = build_archive(out_dir) if create_archive else None
    return {
        "package_dir": str(out_dir),
        "archive_path": str(archive_path) if archive_path else None,
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "task_count": len(task_rows),
        "dimension_count": len(dimensions),
        "source": source,
    }

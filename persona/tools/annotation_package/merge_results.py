from __future__ import annotations

import gzip
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


KIT_DIR = Path(__file__).resolve().parent / "collab_kit"
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

import conformance  # noqa: E402


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    rows: list[dict[str, Any]] = []
    with opener(path, "rt", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object row")
            rows.append(row)
    return rows


def _fetch_db_identity(db_path: Path, indices: list[int]) -> dict[int, dict[str, Any]]:
    if not indices:
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    columns = {row["name"] for row in conn.execute("pragma table_info(profiles)")}
    wanted = ["global_idx", "task_id", "qid"]
    if "input_sha256" in columns:
        wanted.append("input_sha256")
    found: dict[int, dict[str, Any]] = {}
    for start in range(0, len(indices), 900):
        chunk = indices[start : start + 900]
        placeholders = ",".join("?" for _ in chunk)
        query = (
            f"select {', '.join(wanted)} from profiles "
            f"where global_idx in ({placeholders})"
        )
        for row in conn.execute(
            query,
            chunk,
        ):
            found[int(row["global_idx"])] = dict(row)
    conn.close()
    return found


def _is_attributed(field: dict[str, Any]) -> bool:
    return (
        field.get("value") is not None
        and field.get("assignment_type") != "unsupported"
    )


def merge_results(
    results_files: list[Path],
    *,
    dimensions: list[dict[str, Any]] | None,
    db_path: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    conflicts: list[str] = []
    loaded: list[tuple[Path, list[dict[str, Any]]]] = []
    per_source: dict[str, dict[str, int]] = {}

    for path in results_files:
        rows = _load_jsonl(path)
        loaded.append((path, rows))
        result_errors, result_warnings = conformance.check_results(rows, dimensions)
        errors.extend(f"{path}: {error}" for error in result_errors)
        warnings.extend(f"{path}: {warning}" for warning in result_warnings)

    db_meta: dict[int, dict[str, Any]] = {}
    if db_path is not None:
        indices = sorted(
            {
                row["global_idx"]
                for _path, rows in loaded
                for row in rows
                if isinstance(row.get("global_idx"), int)
            }
        )
        db_meta = _fetch_db_identity(db_path, indices)

    merged: dict[int, dict[str, Any]] = {}
    for path, rows in loaded:
        source = str(path)
        counts = per_source.setdefault(source, {"records": 0, "attributed": 0})
        for row in rows:
            global_idx = row.get("global_idx")
            if not isinstance(global_idx, int):
                continue
            counts["records"] += 1

            if db_path is not None:
                expected = db_meta.get(global_idx)
                if expected is None:
                    errors.append(
                        f"{source}: global_idx {global_idx} not found in --db dataset"
                    )
                    continue
                for key in ("task_id", "qid"):
                    if row.get(key) is not None and row.get(key) != expected.get(key):
                        errors.append(
                            f"{source}: global_idx {global_idx} {key} mismatch "
                            f"(result {row.get(key)!r} "
                            f"!= dataset {expected.get(key)!r})"
                        )
                expected_input_sha = expected.get("input_sha256")
                if expected_input_sha and row.get("input_sha256") != expected_input_sha:
                    errors.append(
                        f"{source}: global_idx {global_idx} input_sha256 mismatch "
                        f"(result {row.get('input_sha256')!r} "
                        f"!= dataset {expected_input_sha!r})"
                    )

            entry = merged.setdefault(
                global_idx,
                {
                    "global_idx": global_idx,
                    "task_id": row.get("task_id"),
                    "qid": row.get("qid"),
                    "fields": {},
                    "sources": [],
                    "runs": [],
                },
            )
            if source not in entry["sources"]:
                entry["sources"].append(source)
            run = row.get("run")
            if isinstance(run, dict) and run not in entry["runs"]:
                entry["runs"].append(run)

            for field in row.get("fields", []):
                if not isinstance(field, dict):
                    continue
                if _is_attributed(field):
                    counts["attributed"] += 1
                field_id = field.get("field_id")
                if not isinstance(field_id, str):
                    continue
                previous = entry["fields"].get(field_id)
                if previous is None:
                    entry["fields"][field_id] = field
                elif previous.get("value") != field.get("value"):
                    conflicts.append(
                        f"global_idx {global_idx} field {field_id!r}: "
                        f"{previous.get('value')!r} vs {field.get('value')!r}"
                    )
                    if (field.get("confidence") or 0) > (
                        previous.get("confidence") or 0
                    ):
                        entry["fields"][field_id] = field

    records: list[dict[str, Any]] = []
    for global_idx in sorted(merged):
        entry = merged[global_idx]
        fields = sorted(
            entry["fields"].values(),
            key=lambda field: str(field.get("field_id")),
        )
        records.append(
            {
                "global_idx": global_idx,
                "task_id": entry.get("task_id"),
                "qid": entry.get("qid"),
                "fields": fields,
                "n_attributed": sum(1 for field in fields if _is_attributed(field)),
                "sources": sorted(entry["sources"]),
                "runs": entry["runs"],
            }
        )

    report = {
        "accepted": not errors,
        "errors": errors,
        "warnings": warnings,
        "conflicts": conflicts,
        "per_source": per_source,
        "record_count": len(records),
    }
    return records, report

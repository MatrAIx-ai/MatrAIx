from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from persona.tools.annotation_package.core import canonical_json, sha256_text


TASK_COLUMNS = ("global_idx", "task_id", "qid", "title", "source_url", "profile_text")


def wiki_input_payload(task: dict[str, Any]) -> dict[str, Any]:
    return {key: task[key] for key in TASK_COLUMNS}


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in conn.execute("pragma table_info(profiles)")}


def load_wiki_tasks(
    db_path: Path,
    *,
    range_start: int,
    range_end: int,
) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    columns = _columns(conn)
    selected = list(TASK_COLUMNS)
    has_input_sha = "input_sha256" in columns
    if has_input_sha:
        selected.append("input_sha256")
    rows = [
        dict(row)
        for row in conn.execute(
            f"""
            select {", ".join(selected)}
            from profiles
            where global_idx >= ? and global_idx < ?
            order by global_idx
            """,
            (range_start, range_end),
        )
    ]
    conn.close()

    expected_count = range_end - range_start
    if len(rows) != expected_count:
        raise ValueError(
            f"range [{range_start}, {range_end}) expected {expected_count} rows, "
            f"got {len(rows)}"
        )

    tasks: list[dict[str, Any]] = []
    for row in rows:
        task = dict(row)
        if not task.get("input_sha256"):
            payload = wiki_input_payload(task)
            task["input_sha256"] = sha256_text(canonical_json(payload))
        tasks.append(task)
    return tasks

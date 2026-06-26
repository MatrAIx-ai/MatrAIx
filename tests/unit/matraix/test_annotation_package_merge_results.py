from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from persona.tools.annotation_package.merge_results import merge_results


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _result_row(global_idx: int, *, input_sha256: str = "a" * 64) -> dict:
    return {
        "global_idx": global_idx,
        "task_id": f"wiki_profile:{global_idx:010d}",
        "qid": f"Q{global_idx}",
        "input_sha256": input_sha256,
        "model": "mock-model",
        "run": {
            "backend": "mock",
            "model": "mock-model",
            "effort": "high",
            "runner_version": "1.0.0",
        },
        "fields": [
            {
                "field_id": "domain",
                "value": "Software & AI",
                "confidence": 0.8,
                "evidence": "worked on software systems",
                "assignment_type": "summary_inference",
            }
        ],
    }


def test_merge_results_unions_valid_fields(tmp_path: Path) -> None:
    results = tmp_path / "results.jsonl"
    _write_jsonl(results, [_result_row(0), _result_row(1)])
    dimensions = [
        {
            "id": "domain",
            "label": "Domain",
            "category": "Expertise: Domains",
            "description": "Primary field.",
            "values": ["Software & AI", "Mathematics"],
        }
    ]

    merged, report = merge_results([results], dimensions=dimensions, db_path=None)

    assert report["errors"] == []
    assert len(merged) == 2
    assert merged[0]["global_idx"] == 0
    assert merged[0]["n_attributed"] == 1
    assert merged[0]["fields"][0]["field_id"] == "domain"
    assert str(results) in merged[0]["sources"]


def test_merge_results_reports_db_identity_mismatch(tmp_path: Path) -> None:
    results = tmp_path / "results.jsonl"
    db = tmp_path / "profiles.sqlite"
    _write_jsonl(results, [_result_row(0, input_sha256="bad")])
    conn = sqlite3.connect(db)
    conn.execute(
        """
        create table profiles (
          global_idx integer primary key,
          task_id text not null,
          qid text not null,
          input_sha256 text not null
        )
        """
    )
    conn.execute(
        "insert into profiles values (?, ?, ?, ?)",
        (0, "wiki_profile:0000000000", "Q0", "a" * 64),
    )
    conn.commit()
    conn.close()

    _merged, report = merge_results([results], dimensions=None, db_path=db)

    assert any("input_sha256 mismatch" in error for error in report["errors"])

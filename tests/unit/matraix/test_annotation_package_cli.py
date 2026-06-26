from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


def _write_wiki_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        create table profiles (
          global_idx integer primary key,
          task_id text not null,
          qid text not null,
          title text not null,
          source_url text not null,
          profile_text text not null
        )
        """
    )
    for idx, title in enumerate(["Ada Lovelace", "Grace Hopper"]):
        conn.execute(
            """
            insert into profiles
              (global_idx, task_id, qid, title, source_url, profile_text)
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                f"wiki_profile:{idx:010d}",
                f"Q{idx + 1}",
                title,
                f"https://www.wikidata.org/wiki/Q{idx + 1}",
                f"{title} is a biographical profile.",
            ),
        )
    conn.commit()
    conn.close()


def _write_histories(path: Path) -> None:
    row = {
        "user_id": "USER_A",
        "reviews": [
            {
                "timestamp": 1,
                "date": "2020-01-01",
                "category": "Books",
                "rating": 5,
                "title": "Practical Python",
                "text": "Useful for weekly data projects.",
            },
            {
                "timestamp": 2,
                "date": "2021-01-01",
                "category": "Electronics",
                "rating": 4,
                "title": "Keyboard",
                "text": "Durable for programming work.",
            },
        ],
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_cli_builds_wiki_package(tmp_path: Path) -> None:
    db = tmp_path / "profiles.sqlite"
    out_dir = tmp_path / "A_0_2_worker"
    _write_wiki_db(db)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "persona.tools.annotation_package.cli",
            "make",
            "--source",
            "wiki",
            "--db",
            str(db),
            "--range",
            "0:2",
            "--out-dir",
            str(out_dir),
            "--assignment-id",
            "A_0_2",
            "--worker-id",
            "worker",
            "--dataset-id",
            "wiki-test",
            "--dataset-sha256",
            "d" * 64,
            "--categories",
            "demographic_core",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["source"] == "wiki"
    assert Path(summary["archive_path"]).is_file()
    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["task_count"] == 2
    assert assignment["source"] == "wiki"
    assert assignment["categories"] == ["demographic_core"]

    status = subprocess.run(
        ["./run_assignment.sh", "--status"],
        cwd=out_dir,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Integrity: PASS" in status.stdout


def test_cli_builds_amazon_review_package(tmp_path: Path) -> None:
    histories = tmp_path / "user_histories.jsonl"
    out_dir = tmp_path / "amazon_0_1_worker"
    _write_histories(histories)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "persona.tools.annotation_package.cli",
            "make",
            "--source",
            "amazon-reviews",
            "--user-histories",
            str(histories),
            "--range",
            "0:1",
            "--out-dir",
            str(out_dir),
            "--assignment-id",
            "AMZ_0_1",
            "--worker-id",
            "worker",
            "--dataset-id",
            "amazon-test",
            "--dataset-sha256",
            "e" * 64,
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["source"] == "amazon_reviews_2023"
    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["source"] == "amazon_reviews_2023"
    assert assignment["cv_folds"] == 3
    tasks = [
        json.loads(line)
        for line in (out_dir / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert tasks[0]["source"] == "amazon_reviews_2023"
    assert "=== Fold 1/2 ===" in tasks[0]["profile_text"]

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from persona.tools.annotation_package.sources.amazon_reviews import load_amazon_tasks
from persona.tools.annotation_package.sources.wiki import load_wiki_tasks


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
    for idx, title in enumerate(["Ada Lovelace", "Grace Hopper", "Katherine Johnson"]):
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


def _write_user_histories(path: Path) -> None:
    rows = [
        {
            "user_id": "USER_A",
            "reviews": [
                {
                    "timestamp": 1_577_836_800_000,
                    "date": "2020-01-01",
                    "category": "Books",
                    "rating": 5,
                    "title": "Practical Python",
                    "text": "Useful for weekly data projects.",
                    "verified_purchase": True,
                    "helpful_vote": 3,
                },
                {
                    "timestamp": 1_609_459_200_000,
                    "date": "2021-01-01",
                    "category": "Electronics",
                    "rating": 4,
                    "title": "Reliable keyboard",
                    "text": "Durable enough for programming work.",
                    "verified_purchase": True,
                    "helpful_vote": 2,
                },
                {
                    "timestamp": 1_640_995_200_000,
                    "date": "2022-01-01",
                    "category": "Books",
                    "rating": 5,
                    "title": "Machine learning cookbook",
                    "text": "Good recipes for experiments.",
                    "verified_purchase": False,
                    "helpful_vote": 1,
                },
            ],
        },
        {
            "user_id": "USER_B",
            "reviews": [
                {
                    "timestamp": 1_577_836_800_000,
                    "date": "2020-01-01",
                    "category": "Home",
                    "rating": 5,
                    "title": "Storage bins",
                    "text": "Keeps tools organized.",
                    "verified_purchase": True,
                    "helpful_vote": 0,
                },
                {
                    "timestamp": 1_609_459_200_000,
                    "date": "2021-01-01",
                    "category": "Home",
                    "rating": 4,
                    "title": "Label maker",
                    "text": "Useful for tidy shelves.",
                    "verified_purchase": True,
                    "helpful_vote": 0,
                },
            ],
        },
    ]
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_load_wiki_tasks_reads_range_and_computes_input_sha(tmp_path: Path) -> None:
    db = tmp_path / "profiles.sqlite"
    _write_wiki_db(db)

    tasks = load_wiki_tasks(db, range_start=1, range_end=3)

    assert [task["global_idx"] for task in tasks] == [1, 2]
    assert tasks[0]["task_id"] == "wiki_profile:0000000001"
    assert tasks[0]["qid"] == "Q2"
    assert tasks[0]["title"] == "Grace Hopper"
    assert len(tasks[0]["input_sha256"]) == 64


def test_load_wiki_tasks_requires_complete_range(tmp_path: Path) -> None:
    db = tmp_path / "profiles.sqlite"
    _write_wiki_db(db)

    with pytest.raises(ValueError, match="expected 5 rows, got 3"):
        load_wiki_tasks(db, range_start=0, range_end=5)


def test_load_amazon_tasks_renders_folded_review_profiles(tmp_path: Path) -> None:
    histories = tmp_path / "user_histories.jsonl"
    _write_user_histories(histories)

    tasks = load_amazon_tasks(
        histories,
        range_start=0,
        range_end=2,
        cv_folds=3,
        min_support_folds=2,
        max_reviews_per_user=5,
        max_review_text_chars=120,
        max_profile_text_chars=10_000,
    )

    assert [task["global_idx"] for task in tasks] == [0, 1]
    assert tasks[0]["source"] == "amazon_reviews_2023"
    assert tasks[0]["task_id"] == "amazon_reviews_2023:USER_A"
    assert tasks[0]["qid"] == "amazon_user:USER_A"
    assert tasks[0]["effective_cv_folds"] == 3
    assert tasks[1]["effective_cv_folds"] == 2
    assert len(tasks[0]["cv_fold_texts"]) == 3
    assert "=== Fold 1/3 ===" in tasks[0]["profile_text"]
    assert "[r0001]" in tasks[0]["profile_text"]
    assert "Practical Python" in tasks[0]["profile_text"]
    assert len(tasks[0]["input_sha256"]) == 64

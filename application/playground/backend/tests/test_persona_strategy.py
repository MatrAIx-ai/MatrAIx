"""Tests for optional per-task persona_strategy.json loading."""

from __future__ import annotations

import json

from backend.service.persona_strategy import load_persona_strategy, normalize_persona_strategy
from backend.service.task_detail_service import get_task_detail


def test_normalize_persona_strategy_keeps_optional_sample_size() -> None:
    payload = normalize_persona_strategy(
        {
            "schemaVersion": "1.0",
            "defaultMode": "stratified",
            "sources": ["Nemotron"],
            "dimensionFilters": {"age_bracket": ["25-34", "35-44"], "region": "North America"},
            "stratifyFields": ["age_bracket"],
            "sampleSize": 8,
        }
    )
    assert payload["defaultMode"] == "stratified"
    assert payload["sources"] == ["Nemotron"]
    assert payload["dimensionFilters"] == {
        "age_bracket": ["25-34", "35-44"],
        "region": ["North America"],
    }
    assert payload["sampleSize"] == 8
    assert "seed" not in payload


def test_load_persona_strategy_missing_file_returns_none(tmp_path) -> None:
    assert load_persona_strategy(tmp_path) is None


def test_get_task_detail_includes_persona_strategy(tmp_path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "example-survey-demo"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        '[metadata]\ntype = "survey"\n[task]\nname = "demo/survey"\n',
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text("# Demo\n\nAnswer in character.\n", encoding="utf-8")
    (task_dir / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "defaultMode": "random",
                "dimensionFilters": {"age_bracket": ["18-24", "25-34"]},
                "sampleSize": 6,
            }
        ),
        encoding="utf-8",
    )

    detail = get_task_detail("application/tasks/example-survey-demo", repo_root=tmp_path)
    assert detail["personaStrategy"] is not None
    assert detail["personaStrategy"]["defaultMode"] == "random"
    assert detail["personaStrategy"]["sampleSize"] == 6
    assert detail["personaStrategy"]["dimensionFilters"]["age_bracket"] == ["18-24", "25-34"]

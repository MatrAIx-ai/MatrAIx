from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[2]
PERSONA_SURVEY = ROOT / "application/tasks/persona-survey"


def test_persona_survey_task_metadata_is_clean() -> None:
    task_text = (PERSONA_SURVEY / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == "personabench/application-persona-survey"
    assert task["metadata"]["type"] == "survey"
    assert "matraix/" not in task_text.lower()

    readme = (PERSONA_SURVEY / "README.md").read_text(encoding="utf-8")
    assert "bench-dev-2000" not in readme
    assert "persona/datasets/bench-dev-sample/persona_0042.yaml" in readme


def test_persona_survey_verifier_accepts_minimal_valid_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "survey_result.json").write_text(
        json.dumps(
            {
                "instrument": {"id": "smoke", "title": "Smoke survey"},
                "answers": [
                    {
                        "questionId": "q1",
                        "value": 4,
                        "rationale": "Fits the assigned persona.",
                        "confidence": 0.8,
                    }
                ],
                "trajectory": [
                    {
                        "timestamp": "2026-06-24T00:00:00Z",
                        "actor": "user",
                        "action": "answer_question",
                        "context": {"questionId": "q1"},
                        "outcome": {"questionId": "q1", "value": 4},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    verifier_path = PERSONA_SURVEY / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location("persona_survey_test_state", verifier_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT_DIR = output_dir
    module.RESULT_PATH = output_dir / "survey_result.json"
    assert module.main() == 0

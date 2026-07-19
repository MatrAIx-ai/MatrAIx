"""Integration unit tests for DirectEngineEvaluator and verifier compatibility."""
import json
import tempfile
from pathlib import Path

from direct_eval.evaluator import DirectEngineEvaluator


def test_direct_evaluator_runs_and_produces_valid_result():
    dims = {
        "risk_tolerance": "Low",
        "decision_style": "Analytical",
        "economic_motivation": "Cost-sensitive",
    }
    evaluator = DirectEngineEvaluator(persona_dimensions=dims, seed=42)
    result = evaluator.run()

    assert result["game_id"] == "texas-holdem-heads-up-v1"
    assert result["seed"] == 42
    assert len(result["hole_cards"]) == 2
    assert len(result["community_cards"]) <= 5
    assert result["winner"] in ("player", "opponent", "tie")
    assert isinstance(result["chip_delta"], int)
    assert result["risk_posture"] == "risk_averse"
    assert result["exploration_style"] == "deep_research"
    assert result["task_strategy_basis"] == "pot_control"
    assert len(result["reason"]) >= 20
    assert result["_mode"] == "direct"


def test_direct_evaluator_verifier_compliance(monkeypatch, tmp_path):
    dims = {
        "risk_tolerance": "High",
        "decision_style": "Impulsive",
        "economic_motivation": "Premium-seeking",
    }
    evaluator = DirectEngineEvaluator(persona_dimensions=dims, seed=1)
    result = evaluator.run()

    # Save to temporary holdem_result.json
    output_file = tmp_path / "holdem_result.json"
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Set environment variable MATRIX_OUTPUT_DIR
    monkeypatch.setenv("MATRIX_OUTPUT_DIR", str(tmp_path))

    # Also mock persona.yaml input
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    persona_yaml = input_dir / "persona.yaml"
    persona_yaml.write_text(
        "dimensions:\n  risk_tolerance: High\n  decision_style: Impulsive\n  economic_motivation: Premium-seeking\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PERSONA_INPUT_DIR", str(input_dir))

    # Import and run test_state functions
    from tests.test_state import _compute_persona_consistency, test_output_schema_and_game_semantics

    test_output_schema_and_game_semantics()
    consistency = _compute_persona_consistency(result)
    assert consistency["score"] == 1.0

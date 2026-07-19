"""Unit tests for direct engine persona action policies."""
import random
from dataclasses import dataclass

from direct_eval.policies import (
    DecisionStylePolicy,
    EconomicMotivationPolicy,
    RiskPolicy,
)
from direct_eval.policy_registry import build_policy


@dataclass
class MockState:
    player_bet: int = 10
    bot_bet: int = 20
    pot: int = 30


def test_risk_policy_mapping():
    policy = RiskPolicy()
    assert policy.derive_output_fields({"risk_tolerance": "Low"})["risk_posture"] == "risk_averse"
    assert policy.derive_output_fields({"risk_tolerance": "High"})["risk_posture"] == "risk_seeking"
    assert policy.derive_output_fields({"risk_tolerance": "Moderate"})["risk_posture"] == "balanced"


def test_decision_style_policy_mapping():
    policy = DecisionStylePolicy()
    assert policy.derive_output_fields({"decision_style": "Analytical"})["exploration_style"] == "deep_research"
    assert policy.derive_output_fields({"decision_style": "Impulsive"})["exploration_style"] == "quick_pick"
    assert policy.derive_output_fields({"decision_style": "Cautious"})["exploration_style"] == "hesitant"


def test_economic_motivation_policy_mapping():
    policy = EconomicMotivationPolicy()
    assert policy.derive_output_fields({"economic_motivation": "Cost-sensitive"})["task_strategy_basis"] == "pot_control"
    assert policy.derive_output_fields({"economic_motivation": "Value-driven"})["task_strategy_basis"] == "hand_strength"


def test_composed_policy():
    dims = {
        "risk_tolerance": "Low",
        "decision_style": "Analytical",
        "economic_motivation": "Cost-sensitive",
    }
    policy = build_policy(dims)
    state = MockState(player_bet=10, bot_bet=20, pot=30)
    rng = random.Random(42)

    action = policy.decide(state, dims, rng)
    assert action in ("fold", "call", "check", "raise")

    derived = policy.derive_output_fields(dims)
    assert derived["risk_posture"] == "risk_averse"
    assert derived["exploration_style"] == "deep_research"
    assert derived["task_strategy_basis"] == "pot_control"

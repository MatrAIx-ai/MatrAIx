"""Deterministic Persona Action Policies for poker direct engine evaluation."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .hand_strength import classify_preflop


class PersonaActionPolicy(ABC):
    """Abstract base class mapping persona dimensions to poker actions and verifier fields."""

    @abstractmethod
    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        """Return 'fold' | 'check' | 'call' | 'raise' | None (to defer to next policy)."""

    @abstractmethod
    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        """Return dict of derived fields (e.g. risk_posture, exploration_style, strategy_basis)."""


class ComposedPolicy(PersonaActionPolicy):
    """Aggregates sub-policies with priority ordering."""

    def __init__(self, sub_policies: List[PersonaActionPolicy]):
        self.sub_policies = sub_policies

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> str:
        for policy in self.sub_policies:
            action = policy.decide(state, dims, rng)
            if action is not None:
                return action
        return "check"  # Fallback safety

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for policy in self.sub_policies:
            fields = policy.derive_output_fields(dims)
            if fields:
                for k, v in fields.items():
                    if k not in result or v is not None:
                        result.setdefault(k, v)
        return result


class RiskPolicy(PersonaActionPolicy):
    """Maps risk_tolerance dimension to poker aggressiveness & risk_posture.

    Preflop decisions use Sklansky hand-tier thresholding to produce
    biologically plausible folding behavior. Post-flop decisions continue
    to use the bet-position heuristic.
    """

    _RISK_POSTURE_MAP = {
        "Low": "risk_averse",
        "Moderate": "balanced",
        "High": "risk_seeking",
    }

    # NOTE FOR REVIEW: Fold thresholds calibrated conservatively.
    # Each (risk_tolerance, tier) pair specifies the probability of folding
    # when facing a bet preflop. These are tunable — Kate's poker expertise
    # should validate the realism of these thresholds for evaluation purposes.
    _FOLD_PREFLOP: dict[str, dict[int, float]] = {
        "Low":      {1: 0.00, 2: 0.00, 3: 0.05, 4: 0.15, 5: 0.30, 6: 0.50, 7: 0.70, 8: 0.85},
        "Moderate": {1: 0.00, 2: 0.00, 3: 0.02, 4: 0.08, 5: 0.15, 6: 0.30, 7: 0.50, 8: 0.65},
        "High":     {1: 0.00, 2: 0.00, 3: 0.00, 4: 0.02, 5: 0.05, 6: 0.10, 7: 0.20, 8: 0.35},
    }

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        rt = dims.get("risk_tolerance", "Moderate")
        player_behind = state.player_bet < state.bot_bet

        # === PREFLOP: hand-strength-aware decision ===
        # NOTE FOR REVIEW: Post-flop decisions continue to use the bet-position
        # heuristic (see below). Full board-aware equity evaluation (using treys)
        # is scoped as a follow-up and NOT implemented in this PR.
        if getattr(state, "street", "") == "preflop":
            if player_behind:
                tier = classify_preflop(state.hole_cards)
                fold_pct = self._FOLD_PREFLOP.get(rt, {}).get(tier, 0.65)
                if rng.random() < fold_pct:
                    return "fold"
                if rt == "High":
                    return "raise" if rng.random() < 0.5 else "call"
                if rt == "Low":
                    return "call"
                return "call" if rng.random() < 0.7 else "raise"
            else:
                if rt == "High":
                    return "raise" if rng.random() < 0.4 else "check"
                return "check"

        # === POSTFLOP: existing bet-position heuristic (UNCHANGED) ===
        # NOTE: Post-flop hand evaluation using board-aware equity
        # is a known limitation. See PR description for details.
        if rt == "Low":
            if player_behind:
                return "fold" if rng.random() < 0.6 else "call"
            return "check"
        elif rt == "High":
            if player_behind:
                return "raise" if rng.random() < 0.5 else "call"
            return "raise" if rng.random() < 0.4 else "check"
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        rt = dims.get("risk_tolerance", "Moderate")
        return {"risk_posture": self._RISK_POSTURE_MAP.get(rt, "balanced")}


class DecisionStylePolicy(PersonaActionPolicy):
    """Maps decision_style to decision strategy & exploration_style."""

    _STYLE_MAP = {
        "Analytical": "deep_research",
        "Impulsive": "quick_pick",
        "Cautious": "hesitant",
        "Intuitive": "compared_multiple",
    }

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        ds = dims.get("decision_style", "Analytical")
        if ds == "Analytical":
            return self._pot_odds_decision(state)
        elif ds == "Impulsive":
            return rng.choice(["fold", "check", "call", "raise"])
        elif ds == "Cautious":
            if state.player_bet < state.bot_bet:
                return "call" if rng.random() < 0.7 else "fold"
            return "check"
        return None

    def _pot_odds_decision(self, state: Any) -> str:
        to_call = state.bot_bet - state.player_bet
        if to_call <= 0:
            return "check"
        pot_odds = to_call / (state.pot + to_call) if (state.pot + to_call) > 0 else 1.0
        return "call" if pot_odds <= 0.4 else "fold"

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        ds = dims.get("decision_style", "Analytical")
        return {"exploration_style": self._STYLE_MAP.get(ds, "deep_research")}


class EconomicMotivationPolicy(PersonaActionPolicy):
    """Maps economic_motivation to chip strategy & task_strategy_basis."""

    _STRATEGY_MAP = {
        "Cost-sensitive": "pot_control",
        "Value-driven": "hand_strength",
        "Premium-seeking": "bluff",
        "Indifferent": "pot_odds",
    }

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        eco = dims.get("economic_motivation", "Value-driven")
        if eco == "Cost-sensitive":
            if state.player_bet < state.bot_bet:
                return "fold"
            return "check"
        elif eco == "Premium-seeking":
            if state.player_bet >= state.bot_bet:
                return "raise" if rng.random() < 0.3 else "check"
            return "call"
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        eco = dims.get("economic_motivation", "Value-driven")
        return {"task_strategy_basis": self._STRATEGY_MAP.get(eco, "hand_strength")}


class _BasePolicy(PersonaActionPolicy):
    """Fallback base policy for default poker action decisions."""

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> str:
        to_call = state.bot_bet - state.player_bet
        if to_call <= 0:
            return "check"
        return "call"

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        return {
            "risk_posture": "balanced",
            "exploration_style": "deep_research",
            "task_strategy_basis": "hand_strength",
        }

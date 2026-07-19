"""Deterministic Persona Action Policies for poker direct engine evaluation."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


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
    """Maps risk_tolerance dimension to poker aggressiveness & risk_posture."""

    _RISK_POSTURE_MAP = {
        "Low": "risk_averse",
        "Moderate": "balanced",
        "High": "risk_seeking",
    }

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        rt = dims.get("risk_tolerance", "Moderate")
        player_behind = state.player_bet < state.bot_bet

        if rt == "Low":
            # Risk-averse: fold to raises easily, prefer check/call
            if player_behind:
                return "fold" if rng.random() < 0.6 else "call"
            return "check"
        elif rt == "High":
            # Risk-seeking: raise aggressively, call down
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

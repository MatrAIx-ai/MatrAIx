"""Policy registry for constructing composed persona policies."""
from __future__ import annotations

from typing import Dict

from .policies import (
    ComposedPolicy,
    DecisionStylePolicy,
    EconomicMotivationPolicy,
    PersonaActionPolicy,
    RiskPolicy,
    _BasePolicy,
)


def build_policy(dims: Dict[str, str]) -> PersonaActionPolicy:
    """Build a composed policy from persona dimensions."""
    sub_policies = []

    if "risk_tolerance" in dims:
        sub_policies.append(RiskPolicy())
    if "decision_style" in dims:
        sub_policies.append(DecisionStylePolicy())
    if "economic_motivation" in dims:
        sub_policies.append(EconomicMotivationPolicy())

    sub_policies.append(_BasePolicy())

    return ComposedPolicy(sub_policies)

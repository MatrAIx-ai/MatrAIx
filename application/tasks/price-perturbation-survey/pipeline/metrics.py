"""Rule-based retention-rate metric.

Computes the share of personas who would still buy after a price
increase — a plain aggregation over ``Decision.would_buy`` with no
judge model involved.
"""

from __future__ import annotations

from typing import Sequence

from .collector import Decision


def compute_retention_rate(decisions: Sequence[Decision]) -> float:
    """Return the fraction of decisions where ``would_buy == "yes"``.

    Parameters
    ----------
    decisions:
        Purchase decisions collected from the survey.

    Returns
    -------
    float
        A value between 0.0 and 1.0 (inclusive).  Returns 0.0 if
        *decisions* is empty.
    """
    if not decisions:
        return 0.0
    yes_count = sum(1 for d in decisions if d.would_buy == "yes")
    return yes_count / len(decisions)

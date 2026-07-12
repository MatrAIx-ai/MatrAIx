"""Product perturbation primitives.

The survey generator (``scripts/generate_surveys.py``) constructs
``Perturbation`` records directly — price changes via ``perturb_price``,
attribute changes from an authored swap table — so this module only
needs the shared value type and the price helper. Attribute *values*
are authored per-product rather than derived from a fixed swap table,
which is why no generic color/material swap logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Product


@dataclass(frozen=True)
class Perturbation:
    """Records what was changed about a product."""

    attribute: str
    original_value: str
    new_value: str


def perturb_price(product: Product, factor: float = 1.25) -> float:
    """Return the product's price after applying a multiplicative factor."""
    return round(product.original_price * factor, 2)

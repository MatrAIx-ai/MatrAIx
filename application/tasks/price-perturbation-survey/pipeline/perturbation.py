"""Price perturbation utilities."""

from __future__ import annotations

from .models import Product


def perturb_price(product: Product, factor: float = 1.25) -> float:
    """Return the product's price after applying a multiplicative factor.

    Parameters
    ----------
    product:
        The product whose price to perturb.
    factor:
        Multiplicative factor (default 1.25 = +25%).

    Returns
    -------
    float
        The new price, rounded to two decimal places.
    """
    return round(product.original_price * factor, 2)

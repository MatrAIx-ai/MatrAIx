"""Data models for the price-perturbation survey pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    """A one-time-purchase retail product.

    Fields align with the fixture schema in ``fixtures/products.json``
    and the ``{{placeholder}}`` names in ``instruction.md``.
    """

    product_name: str
    description: str
    original_price: float
    image_url: str | None = None

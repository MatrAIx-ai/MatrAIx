"""Data models for the purchase-intent survey pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    """A one-time-purchase retail product.

    Fields align with the fixture schema in ``fixtures/products.json``
    and the ``{{placeholder}}`` names in ``templates/price_change.md``.

    The core three fields (``product_name``, ``description``,
    ``original_price``) are required; everything else is optional
    metadata used to make the purchase-intent survey more realistic
    (brand/category framing, real Amazon link, and social-proof signals
    like rating/review_count).
    """

    product_name: str
    description: str
    original_price: float
    image_url: str | None = None
    attributes: dict[str, str] | None = None
    brand: str | None = None
    category: str | None = None
    amazon_url: str | None = None
    asin: str | None = None
    rating: float | None = None
    review_count: int | None = None
    features: list[str] | None = None
    notes: str | None = None

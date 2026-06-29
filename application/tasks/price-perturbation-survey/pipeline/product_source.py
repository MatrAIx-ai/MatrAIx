"""Pluggable product-source abstraction.

Provides a ``ProductSource`` ABC and a default ``FixtureProductSource``
that reads from the checked-in ``fixtures/products.json`` — no network
calls required.  An optional ``AmazonProductSource`` stub is included
behind the same interface for future live-scraping work.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from .models import Product

# Default path to the checked-in fixture data, relative to this file.
_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_DEFAULT_FIXTURE_PATH = _FIXTURES_DIR / "products.json"


class ProductSource(ABC):
    """Abstract base for product-data providers."""

    @abstractmethod
    def get_products(self) -> list[Product]:
        """Return a list of products to evaluate."""


class FixtureProductSource(ProductSource):
    """Reads products from a local JSON fixture file.

    This is the default source.  It requires no network access and
    produces deterministic results, making it ideal for testing and
    offline development.

    Parameters
    ----------
    path:
        Path to a JSON file containing an array of product objects.
        Defaults to ``fixtures/products.json`` shipped with this task.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else _DEFAULT_FIXTURE_PATH

    def get_products(self) -> list[Product]:
        with open(self._path) as f:
            raw = json.load(f)
        return [
            Product(
                product_name=item["product_name"],
                description=item["description"],
                original_price=float(item["original_price"]),
                image_url=item.get("image_url"),
            )
            for item in raw
        ]


class AmazonProductSource(ProductSource):
    """Stub for a live Amazon product scraper.

    This exists to demonstrate the pluggable interface.  A real
    implementation would need to handle anti-bot measures, rate
    limiting, and Amazon's Terms of Service — none of which are
    addressed here.  Using ``FixtureProductSource`` is strongly
    recommended for all automated/test runs.
    """

    def get_products(self) -> list[Product]:
        raise NotImplementedError(
            "Live Amazon scraping is not implemented. "
            "Use FixtureProductSource for offline/deterministic runs."
        )

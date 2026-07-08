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
                attributes=item.get("attributes"),
                brand=item.get("brand"),
                category=item.get("category"),
                amazon_url=item.get("amazon_url"),
                asin=item.get("asin"),
                rating=item.get("rating"),
                review_count=item.get("review_count"),
                features=item.get("features"),
                notes=item.get("notes"),
            )
            for item in raw
        ]


class AmazonProductSource(ProductSource):
    """Stub for a live Amazon product scraper.

    This exists to demonstrate the pluggable interface. A plain HTTP GET
    with a realistic browser User-Agent (letting the client negotiate
    gzip) does return the full server-rendered product page — see
    ``scripts/scrape_amazon.py``, which extracts title/price/rating/
    review count via regex. Rating and review count parse reliably for
    most product pages; price is unreliable on pages with size/color
    variant grids (the buybox price isn't always the first candidate
    match), and rating/review markup occasionally uses a different
    template Amazon serves for some listings. Treat scraped output as a
    starting point to spot-check, not ground truth to trust blindly.

    Scraping should still be paced between requests (~15-20s+) rather
    than fired in a tight loop, and stays subject to Amazon's Terms of
    Service. This class itself remains unimplemented; real product data
    is curated via ``scripts/scrape_amazon.py`` + ``scripts/add_product.py``
    and stored in the fixture files. Using ``FixtureProductSource`` is
    strongly recommended for all automated/test runs.
    """

    def get_products(self) -> list[Product]:
        raise NotImplementedError(
            "Live Amazon scraping is not implemented as a ProductSource. "
            "Use scripts/scrape_amazon.py to fetch data, then "
            "scripts/add_product.py to add it to the fixture. Use "
            "FixtureProductSource for offline/deterministic runs."
        )

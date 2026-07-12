#!/usr/bin/env python3
"""Validate and append real, Amazon-linked products to fixtures/products.json.

This is the validate/append half of a two-step workflow for growing the
product list with real data:

  1. Research + scrape: find a product's real ``amazon.com/.../dp/<ASIN>``
     listing (a plain web search for the product name reliably surfaces
     one — Amazon's search index isn't gated the way one might assume),
     then fetch price/rating/review-count/title with
     ``scripts/scrape_amazon.py`` (a plain HTTP GET with browser headers
     returns the full server-rendered page — no headless browser needed).
     Always double check the scraped ``product_name`` actually matches
     the product you searched for: ASINs occasionally get reassigned to
     an entirely different listing over time. Price extraction is
     unreliable on pages with size/color variant grids or bundled add-on
     offers — cross-check those manually rather than trusting the scrape.
  2. Validation (this script): build a dict matching ``PRODUCT_SCHEMA``
     below for each product and pass it to ``add_products`` (or run this
     file as a CLI against a JSON file of new entries). It checks required
     fields, the amazon.com/dp/ASIN URL shape, rating bounds, and rejects
     duplicate ASINs already in the fixture — then appends and rewrites
     fixtures/products.json.

PRODUCT_SCHEMA (required keys marked *):

    product_name*   str
    description*    str
    original_price* float > 0
    amazon_url*     str, must match https://www.amazon.com/.../dp/<ASIN>
    asin*           str, 10-character alphanumeric Amazon ASIN
    brand           str | None
    category        str | None
    rating          float | None, 0.0-5.0
    review_count    int | None, >= 0
    attributes      dict[str, str] | None
    features        list[str] | None
    image_url       str | None
    notes           str | None -- use this to record data-provenance
                    caveats (e.g. "rating aggregated from retailer X,
                    Amazon's live page blocks scraping").
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_DEFAULT_PRODUCTS_PATH = _FIXTURES_DIR / "products.json"

_ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
_AMAZON_URL_RE = re.compile(r"^https://www\.amazon\.com/.+/dp/([A-Z0-9]{10})")

_REQUIRED_FIELDS = (
    "product_name",
    "description",
    "original_price",
    "amazon_url",
    "asin",
)
_OPTIONAL_FIELDS = (
    "brand",
    "category",
    "rating",
    "review_count",
    "attributes",
    "features",
    "image_url",
    "notes",
)


def validate_product(entry: dict, *, existing_asins: set[str] | None = None) -> list[str]:
    """Return a list of validation error strings (empty means valid)."""
    errors: list[str] = []

    for field in _REQUIRED_FIELDS:
        if not entry.get(field):
            errors.append(f"missing required field: {field!r}")

    price = entry.get("original_price")
    if price is not None and not (isinstance(price, (int, float)) and price > 0):
        errors.append(f"original_price must be a positive number, got {price!r}")

    asin = entry.get("asin")
    if asin is not None and not _ASIN_RE.match(asin):
        errors.append(f"asin must be a 10-character alphanumeric code, got {asin!r}")

    amazon_url = entry.get("amazon_url")
    if amazon_url is not None:
        match = _AMAZON_URL_RE.match(amazon_url)
        if not match:
            errors.append(
                f"amazon_url must look like https://www.amazon.com/.../dp/<ASIN>, "
                f"got {amazon_url!r}"
            )
        elif asin and match.group(1) != asin:
            errors.append(
                f"asin {asin!r} does not match ASIN in amazon_url {match.group(1)!r}"
            )

    rating = entry.get("rating")
    if rating is not None and not (isinstance(rating, (int, float)) and 0.0 <= rating <= 5.0):
        errors.append(f"rating must be between 0.0 and 5.0, got {rating!r}")

    review_count = entry.get("review_count")
    if review_count is not None and not (isinstance(review_count, int) and review_count >= 0):
        errors.append(f"review_count must be a non-negative integer, got {review_count!r}")

    if existing_asins and asin in existing_asins:
        errors.append(f"duplicate asin: {asin!r} already exists in fixture")

    unknown = set(entry) - set(_REQUIRED_FIELDS) - set(_OPTIONAL_FIELDS)
    if unknown:
        errors.append(f"unknown fields not in schema: {sorted(unknown)}")

    return errors


def add_products(
    new_entries: list[dict],
    *,
    path: Path | str = _DEFAULT_PRODUCTS_PATH,
    dry_run: bool = False,
) -> list[dict]:
    """Validate and append ``new_entries`` to the products fixture file.

    Raises ``ValueError`` (listing all problems found) if any entry fails
    validation or duplicates an ASIN already in the file. Returns the full
    updated product list on success.
    """
    path = Path(path)
    existing: list[dict] = json.loads(path.read_text()) if path.exists() else []
    existing_asins = {p["asin"] for p in existing if p.get("asin")}

    all_errors: dict[str, list[str]] = {}
    for entry in new_entries:
        errors = validate_product(entry, existing_asins=existing_asins)
        if errors:
            all_errors[entry.get("product_name", "<unnamed>")] = errors
        elif entry.get("asin"):
            existing_asins.add(entry["asin"])

    if all_errors:
        lines = ["Validation failed:"]
        for name, errors in all_errors.items():
            lines.append(f"  {name}:")
            lines.extend(f"    - {e}" for e in errors)
        raise ValueError("\n".join(lines))

    updated = existing + new_entries
    if not dry_run:
        path.write_text(json.dumps(updated, indent=2) + "\n")
    return updated


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python add_product.py <new_products.json>\n"
            "  <new_products.json> must contain a JSON array of product "
            "objects matching PRODUCT_SCHEMA (see module docstring)."
        )
        sys.exit(1)

    new_entries = json.loads(Path(sys.argv[1]).read_text())
    if isinstance(new_entries, dict):
        new_entries = [new_entries]

    updated = add_products(new_entries)
    print(f"Added {len(new_entries)} product(s). Fixture now has {len(updated)} total.")


if __name__ == "__main__":
    main()

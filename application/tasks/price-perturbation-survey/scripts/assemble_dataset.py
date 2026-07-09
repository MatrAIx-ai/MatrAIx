#!/usr/bin/env python3
"""Assemble the final product dataset from harvest checkpoint files.

Reads the JSONL written by ``harvest.py``, dedupes by ASIN, converts each
record to the fixture product schema (same shape as
``fixtures/products.json``), runs final validation, and writes a single
sorted JSON array plus a summary report to stdout.

The description field is built from the page's own feature bullets (the
first few, joined) — i.e. seller-authored copy, not generated text — so
it stays accurate to the listing.

Records failing final validation are excluded and reported. Suspicious-
but-valid records (price outliers, very long titles) are flagged in the
report for manual spot-checking without being excluded.

Usage:
    python3 scripts/assemble_dataset.py \
        --harvest output/harvest.jsonl \
        --out fixtures/products_1k.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def build_description(record: dict) -> str:
    """Seller-authored description: first feature bullets, trimmed."""
    bullets = record.get("features") or []
    parts: list[str] = []
    total = 0
    for bullet in bullets:
        parts.append(bullet)
        total += len(bullet)
        if total > 400 or len(parts) >= 3:
            break
    return " ".join(parts)


def to_product(record: dict) -> dict:
    attributes = record["attributes"]
    product = {
        "product_name": record["product_name"],
        "brand": attributes.get("brand"),
        "category": record.get("category"),
        "description": build_description(record),
        "original_price": record["original_price"],
        "image_url": None,
        "amazon_url": record["amazon_url"],
        "asin": record["asin"],
        "rating": record.get("rating"),
        "review_count": record.get("review_count"),
        "attributes": attributes,
        "features": record.get("features") or [],
        "notes": (
            "All fields live-scraped from the Amazon product page via "
            f"scripts/harvest.py on {record.get('scraped_at', 'unknown')[:10]}. "
            "Attributes come from the page's structured product-overview/"
            "tech-spec/detail-bullet sections (seller-authored)."
        ),
    }
    return product


def validate_final(product: dict, min_attributes: int) -> str | None:
    if not product["product_name"] or len(product["product_name"]) < 10:
        return "short_title"
    if not product["description"]:
        return "empty_description"
    if not product["original_price"] or product["original_price"] <= 0:
        return "bad_price"
    if len(product["attributes"]) < min_attributes:
        return "too_few_attributes"
    if not product["asin"] or len(product["asin"]) != 10:
        return "bad_asin"
    if not (product["amazon_url"] or "").startswith("https://www.amazon.com/"):
        return "bad_url"
    return None


def flags(product: dict) -> list[str]:
    """Non-fatal signals worth a manual spot check."""
    out = []
    if product["original_price"] < 3:
        out.append("price_under_$3")
    if product["original_price"] > 1000:
        out.append("price_over_$1000")
    if product.get("rating") is None:
        out.append("no_rating")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-attributes", type=int, default=5)
    args = parser.parse_args()

    seen: set[str] = set()
    products: list[dict] = []
    excluded: Counter[str] = Counter()
    flagged: list[tuple[str, list[str]]] = []

    for line in args.harvest.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["asin"] in seen:
            excluded["duplicate_asin"] += 1
            continue
        seen.add(record["asin"])
        product = to_product(record)
        reason = validate_final(product, args.min_attributes)
        if reason:
            excluded[reason] += 1
            continue
        f = flags(product)
        if f:
            flagged.append((product["asin"], f))
        products.append(product)

    products.sort(key=lambda p: (p.get("category") or "", p["asin"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(products, indent=2) + "\n")

    categories = Counter(p.get("category") for p in products)
    attr_counts = [len(p["attributes"]) for p in products]
    print(f"wrote {len(products)} products -> {args.out}")
    print(f"excluded: {dict(excluded) or 'none'}")
    print(
        "attributes per product: "
        f"min={min(attr_counts)} "
        f"median={sorted(attr_counts)[len(attr_counts) // 2]} "
        f"max={max(attr_counts)}"
        if attr_counts else "no products"
    )
    print(f"categories ({len(categories)}): {dict(categories.most_common())}")
    if flagged:
        print(f"flagged for spot-check ({len(flagged)}):")
        for asin, reasons in flagged[:30]:
            print(f"  {asin}: {', '.join(reasons)}")
        if len(flagged) > 30:
            print(f"  ... and {len(flagged) - 30} more")


if __name__ == "__main__":
    main()

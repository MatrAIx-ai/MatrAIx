#!/usr/bin/env python3
"""Generate one perturbed purchase-intent survey per product.

For each product in the bulk dataset, exactly one attribute is changed —
either a physical attribute (color, material, size, ...) or the price —
and the appropriate instruction template is rendered into a complete,
self-contained survey prompt.

Two-step workflow, because the *new* attribute values are authored by a
human/LLM reviewer rather than generated blindly:

1. ``--emit-worklist``: seeded-random choice of which attribute to
   perturb per product; writes a compact worklist JSON of
   ``{survey_id, asin, product_name, attribute, original_value}``
   entries needing a replacement value. Price perturbations are
   deterministic (+25%) and need no entry.

2. ``--assemble --swaps <file>``: merges the authored swap values
   (``{survey_id: new_value}``), renders every survey through the
   task's instruction templates, validates, and writes the final
   ``surveys`` JSONL — one line per survey, each carrying the full
   prompt text plus perturbation metadata and the response schema.

The random choice is seeded (--seed, default 42), so the same products
file always yields the same worklist.

Usage:
    python3 scripts/generate_surveys.py --products fixtures/products_bulk.json \
        --emit-worklist output/survey_worklist.json
    python3 scripts/generate_surveys.py --products fixtures/products_bulk.json \
        --assemble --swaps output/survey_swaps.json \
        --out fixtures/surveys_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.models import Product  # noqa: E402
from pipeline.perturbation import Perturbation, perturb_price  # noqa: E402
from pipeline.renderer import render_prompt_with_perturbation  # noqa: E402

# Attributes that are meaningful for a consumer to react to and safe to
# vary without changing the product's identity. Deliberately excludes
# identity/provenance fields (brand, manufacturer, model_number, upc)
# and free-form spec dumps (dimensions, compatibility lists).
ELIGIBLE_ATTRIBUTES = (
    "color",
    "material",
    "fabric_type",
    "size",
    "capacity",
    "flavor",
    "scent",
    "pattern",
    "style",
    "wattage",
    "number_of_items",
    "unit_count",
    "shape",
    "item_shape",
)

_MAX_VALUE_LEN = 60

RESPONSE_SCHEMA = {
    "purchase_intent": [
        "definitely_would_buy",
        "probably_would_buy",
        "might_or_might_not",
        "probably_would_not",
        "definitely_would_not",
    ],
    "price_fairness": [
        "much_too_high",
        "somewhat_high",
        "about_right",
        "good_value",
        "great_value",
    ],
    "alternative_seeking": ["yes", "no"],
    "purchase_timing": ["buy_now", "wait_for_sale", "not_planning_to_buy"],
    "necessity_level": [
        "essential",
        "important_but_not_urgent",
        "nice_to_have",
    ],
    "reasoning": "free text, 1-3 sentences",
}


def _eligible_for(record: dict) -> list[str]:
    attrs = record.get("attributes") or {}
    out = []
    for key in ELIGIBLE_ATTRIBUTES:
        value = attrs.get(key)
        if value and 1 <= len(value) <= _MAX_VALUE_LEN:
            out.append(key)
    return out


def _choices(records: list[dict], seed: int) -> list[dict]:
    """One perturbation choice per product: eligible attrs + price."""
    rng = random.Random(seed)
    choices = []
    for i, record in enumerate(records, start=1):
        candidates = _eligible_for(record) + ["price"]
        attribute = rng.choice(candidates)
        choices.append(
            {
                "survey_id": f"S{i:04d}",
                "asin": record["asin"],
                "product_name": record["product_name"][:70],
                "attribute": attribute,
                "original_value": (
                    f"{record['original_price']:.2f}"
                    if attribute == "price"
                    else record["attributes"][attribute]
                ),
            }
        )
    return choices


def emit_worklist(records: list[dict], out_path: Path, seed: int) -> None:
    choices = _choices(records, seed)
    needing_values = [c for c in choices if c["attribute"] != "price"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(needing_values, indent=2) + "\n")
    dist = Counter(c["attribute"] for c in choices)
    print(f"{len(choices)} surveys planned; {len(needing_values)} need "
          f"authored swap values -> {out_path}")
    print(f"attribute distribution: {dict(dist.most_common())}")


def _to_product(record: dict) -> Product:
    return Product(
        product_name=record["product_name"],
        description=record["description"],
        original_price=record["original_price"],
        brand=record.get("brand"),
        category=record.get("category"),
        amazon_url=record.get("amazon_url"),
        asin=record.get("asin"),
        rating=record.get("rating"),
        review_count=record.get("review_count"),
        attributes=record.get("attributes"),
    )


def assemble(
    records: list[dict], swaps_path: Path, out_path: Path, seed: int
) -> None:
    swaps: dict[str, str] = json.loads(swaps_path.read_text())
    choices = _choices(records, seed)
    by_asin = {r["asin"]: r for r in records}

    missing = [
        c["survey_id"] for c in choices
        if c["attribute"] != "price" and c["survey_id"] not in swaps
    ]
    if missing:
        raise SystemExit(
            f"{len(missing)} surveys lack swap values: {missing[:10]}..."
        )

    surveys = []
    for choice in choices:
        record = by_asin[choice["asin"]]
        product = _to_product(record)
        # Authored swaps may mark a pick as "__price__": the randomly
        # chosen attribute value turned out to be junk or a singleton
        # (e.g. color "No", unit_count "1.0 Count"), where an attribute
        # change is nonsensical — perturb the price instead.
        swap_value = swaps.get(choice["survey_id"], "").strip()
        if choice["attribute"] == "price" or swap_value == "__price__":
            new_price = perturb_price(product)
            perturbation = Perturbation(
                attribute="price",
                original_value=f"${product.original_price:.2f}",
                new_value=f"${new_price:.2f}",
            )
        else:
            original = choice["original_value"]
            new_value = swap_value
            if not new_value or new_value.casefold() == original.casefold():
                raise SystemExit(
                    f"{choice['survey_id']}: swap value missing or "
                    f"identical to original ({original!r})"
                )
            perturbation = Perturbation(
                attribute=choice["attribute"],
                original_value=original,
                new_value=new_value,
            )

        rendered = render_prompt_with_perturbation(product, perturbation)
        prompt = rendered.user_prompt
        if "{{" in prompt:
            raise SystemExit(
                f"{choice['survey_id']}: unfilled placeholder in prompt"
            )
        surveys.append(
            {
                "survey_id": choice["survey_id"],
                "asin": record["asin"],
                "product_name": record["product_name"],
                "category": record.get("category"),
                "amazon_url": record["amazon_url"],
                "perturbation": {
                    "type": (
                        "price" if perturbation.attribute == "price"
                        else "attribute"
                    ),
                    "attribute": perturbation.attribute,
                    "original_value": perturbation.original_value,
                    "new_value": perturbation.new_value,
                },
                "prompt": prompt,
                "response_schema": RESPONSE_SCHEMA,
            }
        )

    ids = [s["survey_id"] for s in surveys]
    assert len(set(ids)) == len(ids) == len(records)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for survey in surveys:
            f.write(json.dumps(survey) + "\n")

    dist = Counter(s["perturbation"]["attribute"] for s in surveys)
    print(f"wrote {len(surveys)} surveys -> {out_path}")
    print(f"perturbed attribute distribution: {dict(dist.most_common())}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--emit-worklist", type=Path)
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--swaps", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    records = json.loads(args.products.read_text())

    if args.emit_worklist:
        emit_worklist(records, args.emit_worklist, args.seed)
    elif args.assemble:
        if not args.swaps or not args.out:
            parser.error("--assemble requires --swaps and --out")
        assemble(records, args.swaps, args.out, args.seed)
    else:
        parser.error("pass --emit-worklist or --assemble")


if __name__ == "__main__":
    main()

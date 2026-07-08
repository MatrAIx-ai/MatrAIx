"""Product perturbation utilities.

Supports price perturbation (original behavior) and attribute perturbation
(color, shape, material) for studying how different product changes affect
persona purchase intent.

NOTE: The attribute swap tables below only match simple, single-word values
("black", "plastic", "stainless steel"). Real enriched product fixtures tend
to have compound/marketing-style attribute strings ("Koy/Truffle/Whisper",
"100% recycled, bluesign-approved polyester"), which never match, so
choose_perturbation() currently always falls back to price for those
products. Attribute perturbation is intentionally kept for future use but
needs improved matching (e.g. fuzzy/substring matching, or an explicit
per-product `perturbable_attribute` field) before it will actually fire.
Price-only perturbation is the active path for now.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import Product

_COLOR_SWAPS = {
    "black": "white",
    "white": "navy blue",
    "red": "forest green",
    "blue": "burnt orange",
    "green": "burgundy",
    "silver": "rose gold",
    "gold": "matte black",
    "pink": "charcoal gray",
    "gray": "teal",
    "grey": "teal",
    "brown": "slate blue",
    "navy": "crimson",
    "beige": "olive green",
    "purple": "mustard yellow",
    "orange": "midnight blue",
    "yellow": "deep purple",
    "white/silver": "black/gold",
    "stainless steel": "copper",
}

_SHAPE_SWAPS = {
    "round": "square",
    "square": "round",
    "rectangular": "oval",
    "oval": "rectangular",
    "slim": "bulky",
    "compact": "full-size",
    "full-size": "compact",
    "cylindrical": "flat",
    "flat": "cylindrical",
    "tapered": "straight",
    "straight": "tapered",
    "ergonomic": "standard",
    "standard": "ergonomic",
}

_MATERIAL_SWAPS = {
    "plastic": "aluminum",
    "aluminum": "bamboo",
    "stainless steel": "ceramic",
    "ceramic": "stainless steel",
    "leather": "canvas",
    "canvas": "nylon",
    "nylon": "leather",
    "wood": "metal",
    "metal": "wood",
    "glass": "polycarbonate",
    "silicone": "hard plastic",
    "rubber": "silicone",
    "cotton": "polyester",
    "polyester": "merino wool",
    "mesh": "solid fabric",
    "bamboo": "recycled plastic",
    "titanium": "carbon fiber",
    "carbon fiber": "titanium",
}

PERTURBABLE_ATTRIBUTES = ("color", "shape", "material")


@dataclass(frozen=True)
class Perturbation:
    """Records what was changed about a product."""

    attribute: str
    original_value: str
    new_value: str


def perturb_price(product: Product, factor: float = 1.25) -> float:
    """Return the product's price after applying a multiplicative factor."""
    return round(product.original_price * factor, 2)


def _swap(value: str, swap_table: dict[str, str]) -> str | None:
    key = value.strip().lower()
    return swap_table.get(key)


def perturb_attribute(product: Product, attribute: str) -> Perturbation:
    """Perturb a non-price attribute of a product.

    Raises ValueError if the product lacks the attribute or no swap is defined.
    """
    if not product.attributes or attribute not in product.attributes:
        raise ValueError(
            f"Product '{product.product_name}' has no '{attribute}' attribute"
        )

    original = product.attributes[attribute]
    swap_table = {
        "color": _COLOR_SWAPS,
        "shape": _SHAPE_SWAPS,
        "material": _MATERIAL_SWAPS,
    }.get(attribute, {})

    new_value = _swap(original, swap_table)
    if new_value is None:
        raise ValueError(
            f"No swap defined for {attribute}={original!r} "
            f"on product '{product.product_name}'"
        )

    return Perturbation(
        attribute=attribute,
        original_value=original,
        new_value=new_value,
    )


def make_price_perturbation(
    product: Product, factor: float = 1.25
) -> Perturbation:
    """Wrap price perturbation in the Perturbation dataclass."""
    new_price = perturb_price(product, factor)
    return Perturbation(
        attribute="price",
        original_value=f"${product.original_price:.2f}",
        new_value=f"${new_price:.2f}",
    )


def choose_perturbation(
    product: Product, factor: float = 1.25
) -> Perturbation:
    """Pick the best attribute to perturb for a product.

    Tries non-price attributes first (deterministic per product name),
    falls back to price if none are available or swappable.
    """
    if product.attributes:
        available = [
            a for a in PERTURBABLE_ATTRIBUTES if a in product.attributes
        ]
        if available:
            # Deterministic selection based on product name.
            digest = hashlib.md5(
                product.product_name.encode()
            ).hexdigest()
            idx = int(digest, 16) % len(available)
            attr = available[idx]
            try:
                return perturb_attribute(product, attr)
            except ValueError:
                pass

    return make_price_perturbation(product, factor)

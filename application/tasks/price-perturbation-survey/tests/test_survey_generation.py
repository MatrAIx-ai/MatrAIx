"""Tests for survey generation and the collection runner's parsing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_TASK_DIR = Path(__file__).resolve().parent.parent
for _p in (_TASK_DIR, _TASK_DIR / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import generate_surveys as gen  # noqa: E402


def _product(asin: str, **attrs: str) -> dict:
    return {
        "asin": asin,
        "product_name": f"Test Product {asin}",
        "description": "A useful test product with enough words.",
        "original_price": 40.00,
        "brand": "TestBrand",
        "category": "kitchen",
        "amazon_url": f"https://www.amazon.com/dp/{asin}",
        "rating": 4.5,
        "review_count": 100,
        "attributes": {"brand": "TestBrand", **attrs},
    }


def test_choices_are_seed_stable() -> None:
    records = [_product(f"B{i:09d}", color="Black") for i in range(20)]
    a = gen._choices(records, seed=42)
    b = gen._choices(records, seed=42)
    assert a == b
    assert [c["survey_id"] for c in a] == [f"S{i:04d}" for i in range(1, 21)]


def test_ineligible_products_fall_back_to_price() -> None:
    # No eligible attributes -> only "price" is a candidate.
    records = [_product("B000000001", model_number="XYZ")]
    (choice,) = gen._choices(records, seed=1)
    assert choice["attribute"] == "price"


def test_assemble_renders_and_validates(tmp_path: Path) -> None:
    records = [
        _product("B000000001", color="Black"),
        _product("B000000002", material="Plastic"),
    ]
    products = tmp_path / "products.json"
    products.write_text(json.dumps(records))

    # Force known attribute picks by seeding until both are attributes,
    # then supply swaps.
    choices = gen._choices(records, seed=42)
    swaps = {
        c["survey_id"]: "__price__" if c["attribute"] == "price" else "Green"
        for c in choices
    }
    # ensure "Green" differs from any original
    swaps_path = tmp_path / "swaps.json"
    swaps_path.write_text(json.dumps(swaps))
    out = tmp_path / "surveys.jsonl"

    gen.assemble(records, swaps_path, out, seed=42)
    surveys = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(surveys) == 2
    for s in surveys:
        assert "{{" not in s["prompt"]
        assert s["perturbation"]["original_value"]
        assert s["perturbation"]["new_value"]
        assert s["response_schema"]["purchase_intent"]


def test_assemble_rejects_identical_swap(tmp_path: Path) -> None:
    records = [_product("B000000001", color="Black")]
    choices = gen._choices(records, seed=7)
    # Find a seed where the pick is the attribute, not price.
    seed = 7
    while choices[0]["attribute"] == "price":
        seed += 1
        choices = gen._choices(records, seed=seed)

    products = tmp_path / "p.json"
    products.write_text(json.dumps(records))
    swaps_path = tmp_path / "s.json"
    swaps_path.write_text(json.dumps({choices[0]["survey_id"]: "Black"}))
    out = tmp_path / "o.jsonl"

    with pytest.raises(SystemExit, match="identical"):
        gen.assemble(records, swaps_path, out, seed=seed)


def test_assemble_errors_on_missing_swap(tmp_path: Path) -> None:
    records = [_product("B000000001", color="Black")]
    choices = gen._choices(records, seed=3)
    seed = 3
    while choices[0]["attribute"] == "price":
        seed += 1
        choices = gen._choices(records, seed=seed)

    products = tmp_path / "p.json"
    products.write_text(json.dumps(records))
    swaps_path = tmp_path / "s.json"
    swaps_path.write_text(json.dumps({}))  # no swap for the survey
    out = tmp_path / "o.jsonl"

    with pytest.raises(SystemExit, match="lack swap values"):
        gen.assemble(records, swaps_path, out, seed=seed)


def test_shipped_dataset_is_wellformed() -> None:
    """Guard the actual committed surveys_v1.jsonl."""
    path = _TASK_DIR / "fixtures" / "surveys_v1.jsonl"
    if not path.exists():
        pytest.skip("surveys_v1.jsonl not generated yet")
    surveys = [json.loads(x) for x in path.read_text().splitlines()]
    ids = [s["survey_id"] for s in surveys]
    assert len(set(ids)) == len(ids)
    for s in surveys:
        assert "{{" not in s["prompt"]
        p = s["perturbation"]
        assert p["type"] in ("price", "attribute")
        assert p["original_value"] != p["new_value"]
        assert s["prompt"].count(p["new_value"]) >= 1
        assert len(s["response_schema"]) == 6

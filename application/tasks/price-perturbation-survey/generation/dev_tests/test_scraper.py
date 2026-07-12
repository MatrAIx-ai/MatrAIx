"""Tests for the Amazon scraper's parsing and block detection.

Fixtures are small HTML snippets copied verbatim from real Amazon page
markup (captured 2026-07-08), so the regexes are exercised against the
real structures they will meet in production — no network calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TASK_DIR = Path(__file__).resolve().parent.parent
if str(_TASK_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(_TASK_DIR / "scripts"))

from scrape_amazon import (  # noqa: E402
    ScrapedProduct,
    is_blocked,
    parse_product_page,
)

# --- fixtures: real markup fragments ---------------------------------------

_TITLE = (
    '<span id="productTitle" class="a-size-large product-title-word-break">'
    "  Ninja Professional Blender 1000W &amp; 72oz  </span>"
)

# Product-overview table rows (real structure from a live page).
_PO_TABLE = """
<table class="a-normal a-spacing-micro" role="list">
<tr class="a-spacing-small po-brand" role="listitem">
  <td class="a-span3"><span class="a-size-base a-text-bold">Brand</span></td>
  <td class="a-span9"><span class="a-size-base po-break-word">Ninja</span></td>
</tr>
<tr class="a-spacing-small po-color" role="listitem">
  <td class="a-span3"><span class="a-size-base a-text-bold">Color</span></td>
  <td class="a-span9"><span class="a-size-base po-break-word">Black/Gray</span></td>
</tr>
<tr class="a-spacing-small po-capacity" role="listitem">
  <td class="a-span3"><span class="a-size-base a-text-bold">Capacity</span></td>
  <td class="a-span9"><span class="a-size-base po-break-word">1.8 liters</span></td>
</tr>
<tr class="a-spacing-small po-material" role="listitem">
  <td class="a-span3"><span class="a-size-base a-text-bold">Material</span></td>
  <td class="a-span9"><span class="a-size-base po-break-word">Plastic</span></td>
</tr>
<tr class="a-spacing-small po-wattage" role="listitem">
  <td class="a-span3"><span class="a-size-base a-text-bold">Wattage</span></td>
  <td class="a-span9"><span class="a-size-base po-break-word">1000 watts</span></td>
</tr>
<tr class="a-spacing-small po-4k_bought" role="listitem">
  <td class="a-span3"><span class="a-size-base a-text-bold">4K+ bought</span></td>
  <td class="a-span9"><span class="a-size-base po-break-word">in past month</span></td>
</tr>
</table>
"""

_TECHSPEC = """
<table id="productDetails_techSpec_section_1">
<tr>
  <th class="a-color-secondary a-size-base prodDetSectionEntry"> Item Weight </th>
  <td class="a-size-base prodDetAttrValue"> 7.6 pounds </td>
</tr>
<tr>
  <th class="a-color-secondary a-size-base prodDetSectionEntry"> ASIN </th>
  <td class="a-size-base prodDetAttrValue"> B00NGV4506 </td>
</tr>
</table>
"""

_DETAIL_BULLETS = """
<div id="detailBullets_feature_div">
<span class="a-text-bold">Package Dimensions &lrm;: &rlm;</span>
<span>17.7 x 11 x 9.5 inches</span>
</div>
"""

_FEATURE_BULLETS = """
<div id="feature-bullets" class="a-section a-spacing-medium">
<h1 class="a-size-base-plus a-text-bold"> About this item </h1>
<ul class="a-unordered-list a-vertical a-spacing-mini">
<li class="a-spacing-mini"><span class="a-list-item"> PROFESSIONAL POWER: 1000 watts of professional power. </span></li>
<li class="a-spacing-mini"><span class="a-list-item"> XL CAPACITY: The 72 oz pitcher serves the entire family. </span></li>
</ul>
</div>
"""

_PRICE = (
    '<span class="aok-offscreen"> $99.00 </span>'
    '<span id="apex-price-to-pay-value" class="apex-price-to-pay-value">'
    '<span class="a-price" data-a-color="base">'
    '<span class="a-offscreen">$99.00</span></span></span>'
)

_REVIEWS = (
    '<span class="a-icon-alt">4.6 out of 5 stars</span>'
    '<span id="acrCustomerReviewText" aria-label="59,243 Reviews" '
    'class="a-size-base">59,243 ratings</span>'
)

_URL = "https://www.amazon.com/Ninja-Professional/dp/B00NGV4506"


def _page(*sections: str) -> str:
    return "<html><body>" + "".join(sections) + "</body></html>"


_FULL_PAGE = _page(
    _TITLE, _REVIEWS, _PRICE, _PO_TABLE, _TECHSPEC, _DETAIL_BULLETS,
    _FEATURE_BULLETS,
)

_BLOCK_PAGE = """
<html><head><title dir="ltr">Amazon.com</title>
<script>ue_sn = "opfcaptcha.amazon.com";</script></head>
<body><!-- To discuss automated access to Amazon data please contact
api-services-support@amazon.com. -->
<h4>Type the characters you see in this image</h4></body></html>
"""


class TestBlockDetection:
    def test_block_page_detected(self) -> None:
        assert is_blocked(_BLOCK_PAGE)

    def test_product_page_not_blocked(self) -> None:
        assert not is_blocked(_FULL_PAGE)


class TestParseProductPage:
    def test_core_fields(self) -> None:
        p = parse_product_page(_FULL_PAGE, _URL)
        assert isinstance(p, ScrapedProduct)
        assert p.asin == "B00NGV4506"
        assert p.product_name == "Ninja Professional Blender 1000W & 72oz"
        assert p.original_price == 99.00
        assert p.rating == 4.6
        assert p.review_count == 59243

    def test_attributes_merged_from_all_sections(self) -> None:
        p = parse_product_page(_FULL_PAGE, _URL)
        assert p.attributes["brand"] == "Ninja"
        assert p.attributes["color"] == "Black/Gray"
        assert p.attributes["capacity"] == "1.8 liters"
        assert p.attributes["material"] == "Plastic"
        assert p.attributes["wattage"] == "1000 watts"
        assert p.attributes["item_weight"] == "7.6 pounds"
        assert p.attributes["package_dimensions"] == "17.7 x 11 x 9.5 inches"
        assert len(p.attributes) >= 5

    def test_junk_attribute_rows_filtered(self) -> None:
        p = parse_product_page(_FULL_PAGE, _URL)
        assert not any("bought" in k for k in p.attributes)
        assert "asin" not in p.attributes  # blocklisted key

    def test_feature_bullets(self) -> None:
        p = parse_product_page(_FULL_PAGE, _URL)
        assert len(p.features) == 2
        assert p.features[0].startswith("PROFESSIONAL POWER")

    def test_degraded_page_missing_price(self) -> None:
        """Post-block renders can omit the buybox entirely."""
        p = parse_product_page(_page(_TITLE, _REVIEWS, _PO_TABLE), _URL)
        assert p.original_price is None
        assert p.product_name  # rest of the page still parses

    def test_price_ignores_faraway_offscreen(self) -> None:
        """A price anchor with no nearby price must not wildcard to an
        unrelated a-offscreen price later in the document."""
        page = _page(
            _TITLE,
            '<span class="apex-price-to-pay-value"></span>',
            "x" * 500,
            '<span class="a-price"><span class="a-offscreen">$9.09</span></span>',
        )
        p = parse_product_page(page, _URL)
        # Falls back to the document-wide search (only one price exists),
        # but the anchored search must not have matched through 500 chars.
        assert p.original_price == 9.09


class TestHarvestValidation:
    def test_validate_accepts_good_record(self) -> None:
        from harvest import validate
        p = parse_product_page(_FULL_PAGE, _URL)
        assert validate(p, min_attributes=5) is None

    def test_validate_rejects_few_attributes(self) -> None:
        from harvest import validate
        p = parse_product_page(_page(_TITLE, _REVIEWS, _PRICE), _URL)
        reason = validate(p, min_attributes=5)
        assert reason is not None and "too_few_attributes" in reason

    def test_validate_rejects_missing_price(self) -> None:
        from harvest import validate
        p = parse_product_page(_page(_TITLE, _REVIEWS, _PO_TABLE), _URL)
        assert validate(p, min_attributes=5) == "missing_price"


class TestDiscovery:
    def test_extract_asins(self) -> None:
        from discover_products import extract_asins
        listing = (
            '<a href="/Ninja-Professional/dp/B00NGV4506/ref=zg_bs_1">x</a>'
            '<a href="/dp/B0CFPJYX7P?th=1">y</a>'
            '<a href="/Ninja-Professional/dp/B00NGV4506/ref=dup">dup</a>'
        )
        assert extract_asins(listing) == ["B00NGV4506", "B0CFPJYX7P"]

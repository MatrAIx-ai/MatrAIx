#!/usr/bin/env python3
"""Amazon product page scraper.

Fetches real product data (title, price, rating, review count, attributes,
feature bullets) directly from Amazon product pages with a plain HTTP GET —
a realistic browser User-Agent plus letting ``requests`` negotiate gzip is
enough to get the full server-rendered page back, no headless browser
required.

Anti-bot handling: Amazon soft-blocks aggressive clients with a CAPTCHA
interstitial (served from ``opfcaptcha.amazon.com``) rather than a hard
error — the response is still HTTP 200, so callers MUST distinguish a real
product page from a block page. ``fetch_page`` raises ``BlockedError`` when
it detects one; ``is_blocked`` exposes the check directly. Blocks clear on
their own after roughly 100+ seconds of not sending requests (empirically;
see scripts/harvest.py for the backoff policy built on this).

Paces requests between calls (default 20s, override with --delay) since
repeated rapid requests are the thing that trips the block, not a single
fetch.

Attribute extraction pulls from three structured sections of the page, in
priority order (all are key→value pairs authored by Amazon/the seller, so
values are accurate to the listing):

1. the product-overview table under the price (``po-*`` rows),
2. the "Product information" tech-spec tables (``prodDetSectionEntry``),
3. the detail bullets list (``detailBullets_feature_div``).

Usage:
    python3 scripts/scrape_amazon.py <amazon_url> [<amazon_url> ...]
    python3 scripts/scrape_amazon.py --delay 30 <url1> <url2>
"""

from __future__ import annotations

import argparse
import html as html_lib
import re
import time
from dataclasses import dataclass, field

import requests

# A coherent Chrome-on-macOS header set. The client-hint (sec-ch-ua) and
# Sec-Fetch-* headers matter: real Chrome always sends them, so a Chrome
# User-Agent WITHOUT them is a fingerprint mismatch that weighs toward
# the anti-bot block when the IP is already under suspicion.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "sec-ch-ua": (
        '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'
    ),
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}

_ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})")
_TITLE_RE = re.compile(r'id="productTitle"[^>]*>\s*([^<]+?)\s*</span>')
# The buybox "price to pay" marker — anchoring on this (rather than the
# first `a-offscreen` on the page) matters for apparel/variant pages,
# where earlier `a-offscreen` spans belong to per-swatch size/color
# prices in the variant picker, not the selected buybox price. Amazon
# uses two different class-name spellings across page templates.
_PRICE_ANCHOR_RE = re.compile(r"apex-price-?to-?pay-value")
_OFFSCREEN_PRICE_RE = re.compile(r'a-offscreen">\$([\d,]+\.\d{2})')
_REVIEW_COUNT_RE = re.compile(
    r'id="acrCustomerReviewText" aria-label="([\d,]+) Reviews"'
)
_RATING_RE = re.compile(r'a-icon-alt">([\d.]+) out of 5 stars')

# --- attribute sources -----------------------------------------------------
# Product-overview table rows:
#   <tr class="... po-brand"> <td>...<span class="a-size-base a-text-bold">
#   Brand </span>...</td> <td>...<span class="a-size-base po-break-word">
#   Ninja </span>...</td> </tr>
_PO_ROW_RE = re.compile(
    r'class="[^"]*\bpo-[a-z0-9_.\-]+[^"]*"[^>]*>'  # row carrying po-<attr>
    r".{0,400}?a-text-bold[^>]*>\s*(?P<key>[^<]+?)\s*</span>"
    r".{0,400}?po-break-word[^>]*>\s*(?P<val>[^<]+?)\s*</span>",
    re.S,
)
# Tech-spec ("Product information") table rows:
#   <th class="... prodDetSectionEntry"> Brand </th>
#   <td class="... prodDetAttrValue"> Ninja </td>
_TECHSPEC_ROW_RE = re.compile(
    r"prodDetSectionEntry[^>]*>\s*(?P<key>[^<]+?)\s*</th>"
    r".{0,200}?prodDetAttrValue[^>]*>\s*(?P<val>[^<]+?)\s*</td>",
    re.S,
)
# Detail bullets:
#   <span class="a-text-bold">Brand &lrm;: &rlm;</span> <span>Ninja</span>
_DETAIL_BULLET_RE = re.compile(
    r'<span class="a-text-bold">\s*(?P<key>[^<]+?)\s*</span>'
    r"\s*<span>\s*(?P<val>[^<]+?)\s*</span>",
    re.S,
)
# Feature bullets ("About this item"):
_FEATURE_BULLETS_SECTION_RE = re.compile(
    r'id="feature-bullets".*?</ul>', re.S
)
_LIST_ITEM_RE = re.compile(
    r'<span class="a-list-item">\s*(.*?)\s*</span>', re.S
)

# Detail-bullet / tech-spec keys that are not product attributes.
_ATTRIBUTE_KEY_BLOCKLIST = {
    "asin",
    "customer_reviews",
    "best_sellers_rank",
    "date_first_available",
    "is_discontinued_by_manufacturer",
    "country_of_origin",
    "warranty_description",
    "batteries_required",
    "batteries_included",
}
# Junk rows that appear inside the product-overview table but are not
# attributes (e.g. the "4K+ bought in past month" social-proof badge).
_ATTRIBUTE_KEY_JUNK_RE = re.compile(r"bought|_deal|coupon|save_\d|percent_off")

_BLOCK_MARKERS = (
    "opfcaptcha.amazon.com",
    "api-services-support@amazon.com",
    "Type the characters you see in this image",
    "Robot Check",
)


class BlockedError(Exception):
    """Amazon served an anti-bot CAPTCHA page instead of content."""


@dataclass(frozen=True)
class ScrapedProduct:
    asin: str
    amazon_url: str
    product_name: str
    original_price: float | None
    rating: float | None
    review_count: int | None
    attributes: dict[str, str] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)


def is_blocked(html: str) -> bool:
    """True if this response body is Amazon's anti-bot interstitial."""
    return any(marker in html for marker in _BLOCK_MARKERS)


def _clean_text(raw: str) -> str:
    """Unescape entities, strip bidi marks, collapse whitespace."""
    text = html_lib.unescape(raw)
    text = text.replace("‎", "").replace("‏", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(":").strip()


def _clean_title(raw: str) -> str:
    return _clean_text(raw)


def _normalize_key(raw: str) -> str:
    """'Package Dimensions' -> 'package_dimensions'."""
    key = _clean_text(raw).lower()
    key = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    return key


def fetch_page(
    url: str,
    *,
    timeout: int = 20,
    session: requests.Session | None = None,
) -> str:
    """Fetch a product page.

    Raises for non-2xx responses; raises BlockedError if Amazon served
    its anti-bot CAPTCHA interstitial (which comes back as HTTP 200) or
    a 503 (its other block signal).
    """
    getter = session or requests
    resp = getter.get(url, headers=_HEADERS, timeout=timeout)
    if resp.status_code == 503 or is_blocked(resp.text):
        raise BlockedError(f"Amazon anti-bot block on {url}")
    resp.raise_for_status()
    return resp.text


def _extract_attributes(html: str) -> dict[str, str]:
    """Merge the page's structured key→value sections, best source first."""
    attributes: dict[str, str] = {}
    for pattern in (_PO_ROW_RE, _TECHSPEC_ROW_RE, _DETAIL_BULLET_RE):
        for m in pattern.finditer(html):
            key = _normalize_key(m.group("key"))
            val = _clean_text(m.group("val"))
            if not key or not val or len(key) > 60 or len(val) > 200:
                continue
            if key in _ATTRIBUTE_KEY_BLOCKLIST:
                continue
            if _ATTRIBUTE_KEY_JUNK_RE.search(key):
                continue
            attributes.setdefault(key, val)
    return attributes


def _extract_features(html: str) -> list[str]:
    """Feature bullets from the 'About this item' section."""
    section_match = _FEATURE_BULLETS_SECTION_RE.search(html)
    if not section_match:
        return []
    features = []
    for m in _LIST_ITEM_RE.finditer(section_match.group(0)):
        text = _clean_text(re.sub(r"<[^>]+>", " ", m.group(1)))
        if text and len(text) <= 500:
            features.append(text)
    return features


def parse_product_page(html: str, url: str) -> ScrapedProduct:
    """Extract structured product data from a fetched product page.

    Rating is taken as the "X out of 5 stars" text immediately preceding
    the review-count widget (``id="acrCustomerReviewText"``), since the
    page also renders star ratings for unrelated carousel items
    (frequently-bought-together, similar products, etc.) that a naive
    first-match search would pick up instead.
    """
    asin_match = _ASIN_RE.search(url)
    asin = asin_match.group(1) if asin_match else ""

    title_match = _TITLE_RE.search(html)
    product_name = _clean_title(title_match.group(1)) if title_match else ""

    # Pages can have several "price to pay" anchors (buybox, renewed
    # offers, bundles, "compare with similar items" tables). Only accept
    # a price found within a short window of an anchor — searching
    # unbounded to the end of the document risks picking up an unrelated
    # price far away. Even so, treat scraped price as best-effort: see
    # module docstring and the caller-side spot-check requirement.
    original_price = None
    for anchor_match in _PRICE_ANCHOR_RE.finditer(html):
        window = html[anchor_match.end(): anchor_match.end() + 300]
        price_match = _OFFSCREEN_PRICE_RE.search(window)
        if price_match:
            original_price = float(price_match.group(1).replace(",", ""))
            break
    if original_price is None:
        # Fallback for page layouts without the price-to-pay marker.
        price_match = _OFFSCREEN_PRICE_RE.search(html)
        if price_match:
            original_price = float(price_match.group(1).replace(",", ""))

    review_match = _REVIEW_COUNT_RE.search(html)
    review_count = (
        int(review_match.group(1).replace(",", "")) if review_match else None
    )

    rating = None
    if review_match:
        preceding = html[: review_match.start()]
        rating_matches = _RATING_RE.findall(preceding)
        if rating_matches:
            rating = float(rating_matches[-1])

    return ScrapedProduct(
        asin=asin,
        amazon_url=url,
        product_name=product_name,
        original_price=original_price,
        rating=rating,
        review_count=review_count,
        attributes=_extract_attributes(html),
        features=_extract_features(html),
    )


def scrape_products(
    urls: list[str], *, delay_sec: float = 20.0
) -> list[ScrapedProduct]:
    """Scrape multiple product pages, pacing requests between each."""
    session = requests.Session()
    results: list[ScrapedProduct] = []
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(delay_sec)
        html = fetch_page(url, session=session)
        results.append(parse_product_page(html, url))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+", help="Amazon product URLs to scrape")
    parser.add_argument(
        "--delay", type=float, default=20.0,
        help="Seconds to wait between requests (default: 20)",
    )
    args = parser.parse_args()

    products = scrape_products(args.urls, delay_sec=args.delay)
    for p in products:
        print(f"{p.asin}  {p.product_name!r}")
        print(
            f"  price=${p.original_price}  rating={p.rating}  "
            f"review_count={p.review_count}"
        )
        print(f"  attributes ({len(p.attributes)}): {p.attributes}")
        print(f"  features: {len(p.features)} bullets")


if __name__ == "__main__":
    main()

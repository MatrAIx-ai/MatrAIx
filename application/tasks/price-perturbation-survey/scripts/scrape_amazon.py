#!/usr/bin/env python3
"""Amazon product page scraper.

Fetches real product data (title, price, rating, review count) directly
from Amazon product pages with a plain HTTP GET — a realistic browser
User-Agent plus letting ``requests`` negotiate gzip is enough to get the
full server-rendered page back, no headless browser required.

Paces requests between calls (default 20s, override with --delay) since
repeated rapid requests are the thing that trips Amazon's anti-bot
detection, not a single fetch.

Usage:
    python3 scripts/scrape_amazon.py <amazon_url> [<amazon_url> ...]
    python3 scripts/scrape_amazon.py --delay 30 <url1> <url2>
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass

import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
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

_HTML_ENTITIES = {
    "&amp;": "&",
    "&#39;": "'",
    "&quot;": '"',
    "&apos;": "'",
}


@dataclass(frozen=True)
class ScrapedProduct:
    asin: str
    amazon_url: str
    product_name: str
    original_price: float | None
    rating: float | None
    review_count: int | None


def _clean_title(raw: str) -> str:
    text = raw.strip()
    for entity, replacement in _HTML_ENTITIES.items():
        text = text.replace(entity, replacement)
    return text


def fetch_page(url: str, *, timeout: int = 20) -> str:
    """Fetch a product page. Raises for non-2xx responses."""
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_product_page(html: str, url: str) -> ScrapedProduct:
    """Extract title/price/rating/review_count from a fetched product page.

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

    original_price = None
    anchor_match = _PRICE_ANCHOR_RE.search(html)
    if anchor_match:
        price_match = _OFFSCREEN_PRICE_RE.search(html, anchor_match.end())
        if price_match:
            original_price = float(price_match.group(1).replace(",", ""))
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
    )


def scrape_products(
    urls: list[str], *, delay_sec: float = 20.0
) -> list[ScrapedProduct]:
    """Scrape multiple product pages, pacing requests between each."""
    results: list[ScrapedProduct] = []
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(delay_sec)
        html = fetch_page(url)
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


if __name__ == "__main__":
    main()

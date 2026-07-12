#!/usr/bin/env python3
"""Discover Amazon product URLs from best-seller category pages.

Fetches Amazon's public best-seller listing pages across a diverse set of
physical-goods categories and extracts canonical product URLs
(``https://www.amazon.com/dp/<ASIN>``). Best-seller pages are used because
they (a) surface popular, currently-purchasable products with rich listing
data, and (b) are server-rendered enough that the top ~30-50 items appear
in the plain HTML.

Media categories (books, music, video) are deliberately excluded: their
product pages lack the structured attribute tables the harvester needs.

Output is a JSON file of candidate records ``{"asin", "url", "category"}``,
deduped by ASIN, appended-to across runs (rerunning tops up rather than
restarting). Progress is checkpointed per category page so an interrupted
run resumes where it left off.

Usage:
    python3 scripts/discover_products.py --out output/candidates.json
    python3 scripts/discover_products.py --out output/candidates.json --delay 25
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import requests

# Allow running as a script from the task dir or repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_amazon import BlockedError, fetch_page  # noqa: E402

# Best-seller category slugs (amazon.com/gp/bestsellers/<slug>). All are
# physical consumer goods with structured attribute tables on their
# product pages. Two pages exist per list (?pg=1, ?pg=2), ~50 items each,
# though only the server-rendered portion (~30) is extractable per page.
CATEGORY_SLUGS = [
    "kitchen",
    "home-garden",
    "electronics",
    "toys-and-games",
    "sporting-goods",
    "beauty",
    "hpc",  # health & personal care
    "pet-supplies",
    "office-products",
    "hi",  # tools & home improvement
    "automotive",
    "baby-products",
    "videogames",
    "musical-instruments",
    "lawn-garden",
    "appliances",
    "fashion",
    "luggage",
    "grocery",
    "industrial",
    "arts-crafts",
    "wireless",  # cell phones & accessories
    "pc",  # computers & accessories
    "photo",  # camera & photo
    "furniture",
    "kitchen-dining",
    "home-improvement",
    "sports-and-fitness",
    "outdoor-recreation",
    "apparel",
    "shoes",
    "jewelry",
    "watches",
    "beauty-and-grooming",
    "camping-hiking",
]

_PRODUCT_LINK_RE = re.compile(r'href="(/[^"]*?/dp/([A-Z0-9]{10})[/?][^"]*)"')
_DP_LINK_RE = re.compile(r'href="/dp/([A-Z0-9]{10})[/?"]')


def category_urls(slug: str) -> list[str]:
    return [
        f"https://www.amazon.com/gp/bestsellers/{slug}/",
        f"https://www.amazon.com/gp/bestsellers/{slug}/?pg=2",
    ]


def extract_asins(html: str) -> list[str]:
    """All product ASINs linked from a listing page, in page order."""
    seen: dict[str, None] = {}
    for m in _PRODUCT_LINK_RE.finditer(html):
        seen.setdefault(m.group(2))
    for m in _DP_LINK_RE.finditer(html):
        seen.setdefault(m.group(1))
    return list(seen)


def load_candidates(path: Path) -> tuple[list[dict], set[str], set[str]]:
    """Load existing output: (records, known ASINs, done page URLs)."""
    if not path.exists():
        return [], set(), set()
    data = json.loads(path.read_text())
    records = data["candidates"]
    return records, {r["asin"] for r in records}, set(data["done_pages"])


def save_candidates(path: Path, records: list[dict], done_pages: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"candidates": records, "done_pages": sorted(done_pages)}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def discover(
    out_path: Path,
    *,
    delay_sec: float = 20.0,
    block_backoff_sec: float = 120.0,
    slugs: list[str] | None = None,
) -> None:
    records, known_asins, done_pages = load_candidates(out_path)
    session = requests.Session()
    slugs = slugs if slugs is not None else CATEGORY_SLUGS

    pages = [
        (slug, url) for slug in slugs for url in category_urls(slug)
        if url not in done_pages
    ]
    print(
        f"{len(records)} candidates already collected; "
        f"{len(pages)} listing pages to fetch",
        flush=True,
    )

    for i, (slug, url) in enumerate(pages):
        if i > 0:
            time.sleep(delay_sec + random.uniform(0, delay_sec * 0.5))
        try:
            html = fetch_page(url, session=session)
        except BlockedError:
            print(
                f"BLOCKED on {url} — backing off {block_backoff_sec:.0f}s",
                flush=True,
            )
            time.sleep(block_backoff_sec)
            block_backoff_sec = min(block_backoff_sec * 2, 1800)
            # Do not mark the page done; a rerun will retry it.
            continue
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            print(f"HTTP {status} on {url}: skipping", flush=True)
            if status in (404, 410):
                # Bad category slug — permanent; don't retry on rerun.
                done_pages.add(url)
                save_candidates(out_path, records, done_pages)
            continue
        except requests.RequestException as e:
            print(f"FETCH ERROR on {url}: {e}", flush=True)
            continue

        asins = extract_asins(html)
        new = 0
        for asin in asins:
            if asin in known_asins:
                continue
            known_asins.add(asin)
            records.append(
                {
                    "asin": asin,
                    "url": f"https://www.amazon.com/dp/{asin}",
                    "category": slug,
                }
            )
            new += 1
        done_pages.add(url)
        save_candidates(out_path, records, done_pages)
        print(
            f"[{i + 1}/{len(pages)}] {slug}: {len(asins)} asins on page, "
            f"{new} new (total {len(records)})",
            flush=True,
        )

    print(f"Done. {len(records)} total candidates in {out_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, required=True,
        help="Output JSON path (appended-to across runs)",
    )
    parser.add_argument("--delay", type=float, default=20.0)
    parser.add_argument(
        "--slugs", nargs="*", default=None,
        help="Override category slugs (default: built-in list)",
    )
    args = parser.parse_args()
    discover(args.out, delay_sec=args.delay, slugs=args.slugs)


if __name__ == "__main__":
    main()

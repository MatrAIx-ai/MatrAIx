#!/usr/bin/env python3
"""Harvest a large Amazon product dataset from a candidate URL list.

Reads candidates produced by ``discover_products.py`` and scrapes each
product page with ``scrape_amazon.parse_product_page``, writing one JSON
line per outcome. Designed to run unattended for hours and survive
everything short of a power cut:

* **Checkpointing** — every accepted product is appended to
  ``<out>.jsonl`` and flushed immediately; every rejected candidate is
  appended to ``<out>.rejects.jsonl`` with a reason. Rerunning the same
  command skips ASINs already present in either file and continues.
* **Block handling** — Amazon soft-blocks with a CAPTCHA page (still
  HTTP 200). On a block the runner sleeps a long, escalating quiet
  period (default 5 → 10 → 20 → 40 min, capped at 60) before retrying
  the same candidate; empirically the block clears only after a
  sustained quiet period, and continuing to poll while blocked appears
  to extend it. After recovery, the base delay between requests is
  raised 1.5x for the rest of the run.
* **Validation at scrape time** — a record is only accepted if it has a
  non-empty title, a positive price, and at least ``--min-attributes``
  attributes (default 5). Anything else goes to the rejects file, so
  the output JSONL only ever contains records meeting the bar.
* **Stop conditions** — stops when ``--target`` accepted products is
  reached, or candidates are exhausted, or ``--max-blocks`` consecutive
  block/backoff cycles fail (so a hard IP block doesn't spin forever).

Usage:
    python3 scripts/harvest.py \
        --candidates output/candidates.json \
        --out output/harvest \
        --target 1000
"""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_amazon import (  # noqa: E402
    BlockedError,
    ScrapedProduct,
    fetch_page,
    parse_product_page,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
        f.flush()


def _load_done_asins(*paths: Path) -> set[str]:
    done: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["asin"])
    return done


def validate(product: ScrapedProduct, min_attributes: int) -> str | None:
    """Return a rejection reason, or None if the record is acceptable.

    Price is checked LAST so that a "missing_price" reason means
    everything else on the page was fine — which is the signature of
    Amazon's degraded (buybox-less) template and makes the record worth
    one retry, unlike genuinely thin pages.
    """
    if not product.product_name or len(product.product_name) < 10:
        return "missing_or_short_title"
    if not product.asin:
        return "missing_asin"
    if len(product.attributes) < min_attributes:
        return f"too_few_attributes ({len(product.attributes)})"
    if not product.original_price or product.original_price <= 0:
        return "missing_price"
    if product.original_price > 5000:
        return "implausible_price"
    return None


def harvest(
    candidates_path: Path,
    out_prefix: Path,
    *,
    target: int = 1000,
    min_attributes: int = 5,
    base_delay: float = 20.0,
    block_backoff_start: float = 300.0,
    max_blocks: int = 8,
) -> None:
    results_path = out_prefix.with_suffix(".jsonl")
    rejects_path = out_prefix.with_suffix(".rejects.jsonl")
    results_path.parent.mkdir(parents=True, exist_ok=True)

    candidates = json.loads(candidates_path.read_text())["candidates"]
    done = _load_done_asins(results_path, rejects_path)
    accepted = (
        sum(1 for _ in results_path.open()) if results_path.exists() else 0
    )
    queue = [c for c in candidates if c["asin"] not in done]
    random.shuffle(queue)  # mix categories so a partial run is still diverse

    print(
        f"{_now()} start: {accepted} accepted so far, "
        f"{len(queue)} candidates queued, target {target}",
        flush=True,
    )

    session = requests.Session()
    delay = base_delay
    backoff = block_backoff_start
    consecutive_blocks = 0
    consecutive_successes = 0
    fetched = 0
    # Candidates that fetched fine but came back on Amazon's degraded
    # page template (no server-rendered buybox price — seen right after
    # a block clears). Worth one more attempt later in the run rather
    # than a permanent reject.
    retry_queue: list[dict] = []

    queue_iter = iter(queue)
    retrying = False
    while True:
        candidate = next(queue_iter, None)
        if candidate is None:
            if retrying or not retry_queue:
                break
            retrying = True
            print(
                f"{_now()} retrying {len(retry_queue)} degraded-template "
                "candidates",
                flush=True,
            )
            queue_iter = iter(list(retry_queue))
            continue
        if accepted >= target:
            break
        url, asin, category = (
            candidate["url"], candidate["asin"], candidate.get("category")
        )

        if fetched > 0:
            time.sleep(delay + random.uniform(0, delay * 0.5))

        try:
            html = fetch_page(url, session=session)
            fetched += 1
        except BlockedError:
            consecutive_blocks += 1
            consecutive_successes = 0
            if consecutive_blocks > max_blocks:
                print(
                    f"{_now()} giving up after {max_blocks} consecutive "
                    "block cycles — rerun later to resume",
                    flush=True,
                )
                break
            print(
                f"{_now()} BLOCKED (cycle {consecutive_blocks}) — "
                f"sleeping {backoff / 60:.0f} min",
                flush=True,
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 3600)
            delay = min(delay * 1.5, 90)
            # Fresh session: drop any cookies associated with the block.
            session = requests.Session()
            # Candidate not marked done — retried on the next loop pass
            # only if requeued; simplest is to retry it inline once now.
            try:
                html = fetch_page(url, session=session)
                fetched += 1
            except (BlockedError, requests.RequestException):
                _append_jsonl(
                    rejects_path,
                    {"asin": asin, "url": url, "reason": "blocked_twice",
                     "at": _now()},
                )
                continue
        except requests.RequestException as e:
            _append_jsonl(
                rejects_path,
                {"asin": asin, "url": url,
                 "reason": f"fetch_error: {type(e).__name__}", "at": _now()},
            )
            continue

        consecutive_blocks = 0
        backoff = block_backoff_start  # a success ends the block episode
        consecutive_successes += 1
        if consecutive_successes % 25 == 0 and delay > base_delay:
            # Blocks raise the pacing 1.5x each episode; without a
            # counterpart, one bad patch would pin the whole run at
            # maximum politeness. Ease back toward base after each
            # sustained clean stretch to find the tolerated rate.
            delay = max(base_delay, delay * 0.8)
            print(f"{_now()} clean stretch — easing delay to {delay:.0f}s",
                  flush=True)
        product = parse_product_page(html, url)
        reason = validate(product, min_attributes)
        if reason == "missing_price" and product.product_name and not retrying:
            # Degraded template: page parsed fine but the buybox was
            # empty. Retry once at the end of the run.
            retry_queue.append(candidate)
            continue
        if reason is not None:
            _append_jsonl(
                rejects_path,
                {"asin": asin, "url": url, "reason": reason,
                 "title": product.product_name[:80], "at": _now()},
            )
            continue

        record = asdict(product)
        record["category"] = category
        record["scraped_at"] = _now()
        _append_jsonl(results_path, record)
        accepted += 1
        if accepted % 10 == 0 or accepted == target:
            print(
                f"{_now()} accepted={accepted}/{target} "
                f"(delay={delay:.0f}s)",
                flush=True,
            )

    print(
        f"{_now()} done: {accepted} accepted, results in {results_path}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument(
        "--out", type=Path, required=True,
        help="Output prefix; writes <out>.jsonl and <out>.rejects.jsonl",
    )
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--min-attributes", type=int, default=5)
    parser.add_argument("--delay", type=float, default=20.0)
    parser.add_argument("--max-blocks", type=int, default=8)
    args = parser.parse_args()
    harvest(
        args.candidates,
        args.out,
        target=args.target,
        min_attributes=args.min_attributes,
        base_delay=args.delay,
        max_blocks=args.max_blocks,
    )


if __name__ == "__main__":
    main()

#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://openlibrary.org/search?q=science+fiction"
output = Path("/app/output/book_choice.json")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "book-choice"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    result = page.locator("li.searchResultItem").first
    link = result.locator("h3 a").first
    title = link.inner_text().strip()
    href = link.get_attribute("href") or ""
    author = result.locator("span.bookauthor a").first.inner_text().strip()
    browser.close()

work_match = re.search(r"/works/(OL\d+W)", href)
subject_id = work_match.group(1) if work_match else slugify(title)

payload = {
    "decision_subject_id": subject_id,
    "decision_subject_label": title,
    "decision_outcome": "selected",
    "basis_primary": "taste",
    "exploration_style": "quick_pick",
    "reason": "This book is the one I would most realistically pick up next because it fits the kind of reading I naturally gravitate toward.",
    "task_author": author,
    "task_url": f"https://openlibrary.org{href}" if href.startswith("/") else href,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY

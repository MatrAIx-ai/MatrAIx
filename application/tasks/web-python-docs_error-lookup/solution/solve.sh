#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://docs.python.org/3/library/pathlib.html"
output = Path("/app/output/python_docs_lookup.json")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    title = page.title()
    browser.close()

payload = {
    "source_url": url,
    "topic": "pathlib.Path.read_text",
    "answer_summary": (
        "Path.read_text reads the file as text and returns a string. A user "
        "should pass encoding explicitly when the file's text encoding matters."
    ),
    "documentation_confidence": 8,
    "ease_of_lookup": 7,
    "would_reuse_docs": True,
    "friction_points": [
        f"The docs page title was {title!r}, but the page is dense for beginners."
    ],
}
output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

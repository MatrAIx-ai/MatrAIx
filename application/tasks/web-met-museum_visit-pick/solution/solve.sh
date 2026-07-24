#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://www.metmuseum.org/art/collection/search/436535"
output = Path("/app/output/visit_pick.json")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    title = page.locator("h1").first.inner_text().strip()
    browser.close()

object_id = url.rstrip("/").rsplit("/", 1)[-1]

payload = {
    "decision_subject_id": object_id,
    "decision_subject_label": title,
    "decision_outcome": "selected",
    "basis_primary": "taste",
    "exploration_style": "quick_pick",
    "reason": "This artwork is the one I would prioritize seeing in person because it is the kind of piece I would genuinely make time for.",
    "task_pick_type": "artwork",
    "task_url": url,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY

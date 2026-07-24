#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://www.allrecipes.com/recipe/23600/worlds-best-lasagna/"
output = Path("/app/output/recipe_choice.json")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "recipe-choice"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    title = page.locator("h1").first.inner_text().strip()
    total_time = "unknown"
    details = page.locator(".mm-recipes-details__item")
    for index in range(details.count()):
        item_text = details.nth(index).inner_text()
        if "Total Time" in item_text:
            total_time = item_text.replace("Total Time:", "").strip()
            break
    browser.close()

payload = {
    "decision_subject_id": slugify(title),
    "decision_subject_label": title,
    "decision_outcome": "selected",
    "basis_primary": "taste",
    "exploration_style": "quick_pick",
    "reason": "This recipe is the one I would most realistically cook this week because it fits my taste and feels within my comfort zone in the kitchen.",
    "task_total_time_label": total_time,
    "task_url": url,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY

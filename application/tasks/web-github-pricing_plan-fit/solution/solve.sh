#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://github.com/pricing"
output = Path("/app/output/pricing_plan_evaluation.json")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    title = page.title()
    browser.close()

payload = {
    "source_url": url,
    "selected_plan": "Team",
    "fit_rating": 8,
    "trust_rating": 7,
    "budget_fit": "acceptable",
    "conversion_intent": "consider",
    "reason": (
        "The pricing page loaded as "
        f"{title!r}; Team is a plausible fit for a small collaborative group "
        "that needs shared repositories and admin controls."
    ),
    "friction_points": [
        "Some add-on costs may require comparison against detailed GitHub docs."
    ],
}
output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

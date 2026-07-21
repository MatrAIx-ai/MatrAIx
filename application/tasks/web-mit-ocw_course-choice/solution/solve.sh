#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/"
output = Path("/app/output/course_choice.json")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    title = page.locator("h1").first.inner_text().strip()
    body_text = page.locator("body").inner_text()
    browser.close()

number_match = re.search(r"\b(\d+\.\w+)\b", f"{title} {body_text[:2000]}")
course_number = number_match.group(1) if number_match else "6.0001"
slug = url.rstrip("/").rsplit("/", 1)[-1]

payload = {
    "decision_subject_id": slug,
    "decision_subject_label": title,
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "exploration_style": "quick_pick",
    "reason": "This course is the one I would most realistically start because it matches my learning goal and starts at a level I can handle.",
    "task_course_number": course_number,
    "task_url": url,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY

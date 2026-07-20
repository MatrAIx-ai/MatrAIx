#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

SOURCE_URL = "https://www.cloudflare.com/plans/"
OUTPUT = Path("/app/output/cloudflare_plan_comparison.json")
PLAN_IDS = {
    "Free": "free",
    "Pro": "pro",
    "Business": "business",
    "Contract": "contract",
}


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(locale="en-US")
    page.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=60_000)

    category_tab = page.get_by_role("tab", name="Network & CDN tab")
    category_tab.wait_for(state="visible", timeout=60_000)
    category_tab.click()
    panel = page.get_by_role("tabpanel", name="Network & CDN tab")
    panel.wait_for(state="visible", timeout=60_000)

    cards = panel.locator(
        '[data-cms-path="pricingPage.plans.appServices.tiers"] > div'
    )
    if cards.count() != 4:
        raise RuntimeError(
            f"Expected four Network & CDN plan cards, found {cards.count()}"
        )

    candidates: list[dict[str, str]] = []
    for index in range(cards.count()):
        card = cards.nth(index)
        label = card.get_by_role("heading", level=3).inner_text().strip()
        if label not in PLAN_IDS:
            raise RuntimeError(f"Unexpected Network & CDN plan label: {label!r}")
        target = card.locator('[data-cms-path$=".description"]').inner_text().strip()
        price = card.locator('[data-cms-path$=".price"]').inner_text().strip()
        billing = card.locator('[data-cms-path$=".billing"]').inner_text().strip()
        candidates.append(
            {
                "decision_subject_id": PLAN_IDS[label],
                "decision_subject_label": label,
                "task_price_text": f"{price} {billing}",
                "task_target_text": target,
                "task_relevance_note": (
                    "This was a plausible comparison option because its published "
                    "audience, price, billing terms, and visible features could be "
                    "weighed against the organization context."
                ),
            }
        )

    panel.get_by_text("Compare all features", exact=True).wait_for(
        state="visible", timeout=60_000
    )
    panel.get_by_role("button", name="Core Features").wait_for(
        state="visible", timeout=60_000
    )
    browser.close()

selected = next(
    candidate
    for candidate in candidates
    if candidate["decision_subject_id"] == "business"
)
payload = {
    "decision_subject_id": selected["decision_subject_id"],
    "decision_subject_label": selected["decision_subject_label"],
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "basis_secondary": "features",
    "exploration_style": "compared_multiple",
    "reason": (
        "I recommend the Business plan because its published focus on small "
        "businesses is the clearest fit for this example organization context, "
        "while its visible feature set provides a stronger operational baseline "
        "than the lower tiers without assuming Contract-level criticality."
    ),
    "task_pricing_category": "Network & CDN",
    "task_source_url": SOURCE_URL,
    "task_price_text": selected["task_price_text"],
    "task_target_text": selected["task_target_text"],
    "task_options_considered": candidates,
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

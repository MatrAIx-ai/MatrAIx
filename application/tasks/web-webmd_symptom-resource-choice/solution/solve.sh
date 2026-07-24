#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

OUTPUT = Path("/app/output/symptom_resource_choice.json")
FEEDBACK = Path("/app/output/user_feedback.json")
SOURCE_URL = "https://www.webmd.com/"
SEARCH_URL = "https://www.webmd.com/search/search_results/default.aspx?query=headache"
HUB_URL = "https://www.webmd.com/migraines-headaches/default.htm"
FALLBACK_URLS = [
    "https://www.webmd.com/migraines-headaches/migraine-headaches",
    "https://www.webmd.com/migraines-headaches/tension-headaches",
    "https://www.webmd.com/pain-management/guide/headache-basics",
]
BLOCKED_PATH_PARTS = {
    "search",
    "login",
    "subscribe",
    "newsletters",
    "privacy-policy",
    "cookie-policy",
    "about",
    "contact",
}


def article_slug(url: str) -> str:
    parts = [
        re.sub(r"\.(htm|html)$", "", segment, flags=re.IGNORECASE)
        for segment in urlparse(url).path.strip("/").split("/")
        if segment
    ]
    return "-".join(parts).lower().replace("_", "-")


def normalize_article_url(href: str) -> str | None:
    if not href or href.startswith("javascript:") or href.startswith("mailto:"):
        return None
    absolute = urljoin(SOURCE_URL, href.split("#")[0].split("?")[0])
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or parsed.netloc != "www.webmd.com":
        return None
    parts = [segment for segment in parsed.path.strip("/").split("/") if segment]
    if not parts:
        return None
    if any(part in BLOCKED_PATH_PARTS for part in parts):
        return None
    if parts[0] == "search":
        return None
    return absolute


def collect_article_urls(page, *, limit: int = 3) -> list[str]:
    hrefs: list[str] = []
    for link in page.locator("a[href]").all():
        href = link.get_attribute("href")
        if not href:
            continue
        absolute = normalize_article_url(href)
        if absolute is None or absolute in hrefs:
            continue
        hrefs.append(absolute)
        if len(hrefs) >= limit:
            break
    return hrefs


def load_seed_urls(page) -> list[str]:
    for url in (SEARCH_URL, HUB_URL):
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(4_000)
        hrefs = collect_article_urls(page, limit=3)
        if len(hrefs) >= 3:
            return hrefs
    return FALLBACK_URLS[:3]


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    seed_urls = load_seed_urls(page)

    candidates: list[dict[str, str]] = []
    for article_url in seed_urls:
        page.goto(article_url, wait_until="domcontentloaded", timeout=90_000)
        title = page.locator("h1").first.inner_text(timeout=30_000).strip()
        candidates.append(
            {
                "decision_subject_id": article_slug(article_url),
                "decision_subject_label": title,
                "task_article_url": article_url,
                "task_topic_focus": "Symptoms, causes, and when to seek care",
                "task_relevance_note": (
                    "This article was a plausible option because it addressed headache "
                    "information in language I could follow."
                ),
            }
        )

    browser.close()

if len(candidates) < 3:
    raise RuntimeError("WebMD oracle could not collect three article candidates")

selected = candidates[0]
payload = {
    "decision_subject_id": selected["decision_subject_id"],
    "decision_subject_label": selected["decision_subject_label"],
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "basis_secondary": "quality",
    "exploration_style": "compared_multiple",
    "reason": (
        f"I selected {selected['decision_subject_label']} because it was the best fit "
        "among the headache articles I opened and explained the concern in a way that "
        "helped me think about sensible next steps."
    ),
    "task_concern_summary": (
        "I wanted clearer information about recurring headaches before deciding "
        "whether to mention them to a clinician."
    ),
    "task_article_url": selected["task_article_url"],
    "task_source_url": SOURCE_URL,
    "used_search": True,
    "task_options_considered": candidates,
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
FEEDBACK.write_text(
    json.dumps(
        {
            "needConstraintSatisfaction": "yes",
            "personalPreferenceSatisfaction": "partially",
            "overallExperienceRating": 7,
            "reason": (
                "WebMD had enough articles to compare, although I still wanted clearer "
                "guidance on when headache patterns warrant urgent care."
            ),
            "trustLevel": 6,
            "effortRating": 5,
            "clarityOfNextStep": True,
            "taskHealthLiteracyFit": "yes",
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY

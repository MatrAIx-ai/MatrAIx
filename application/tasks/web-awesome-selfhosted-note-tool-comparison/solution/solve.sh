#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

SOURCE_URL = "https://awesome-selfhosted.net/tags/note-taking--editors.html"
OUTPUT = Path("/app/output/selfhosted_note_tool_comparison.json")
SHORTLIST = ["flatnotes", "HedgeDoc", "Joplin"]


def project_listing(page, label: str) -> dict[str, object]:
    heading = page.get_by_role("heading", name=label, exact=True)
    heading.wait_for(state="visible", timeout=60_000)
    listing = heading.evaluate(
        """element => {
          const blocks = [];
          let node = element.nextElementSibling;
          while (node && node.tagName !== "HR" && node.tagName !== "H3") {
            blocks.push({
              text: (node.innerText || "").trim(),
              links: Array.from(node.querySelectorAll("a")).map(link => ({
                text: (link.innerText || "").trim(),
                href: link.href,
              })),
            });
            node = node.nextElementSibling;
          }
          return blocks;
        }"""
    )
    if len(listing) < 3:
        raise RuntimeError(f"Could not parse listing for {label}: {listing!r}")

    links = [link for block in listing for link in block["links"]]
    website = next(
        (link["href"] for link in links if link["text"] == "Website"), None
    )
    source = next(
        (link["href"] for link in links if link["text"] == "Source Code"), None
    )
    platforms = [
        link["text"] for link in links if "/platforms/" in link["href"]
    ]
    licenses = [
        link["text"] for link in links if "#list-of-licenses" in link["href"]
    ]
    metadata_text = " ".join(block["text"] for block in listing)
    update_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", metadata_text)
    if not source or not platforms or not licenses:
        raise RuntimeError(f"Incomplete listing metadata for {label}: {listing!r}")

    return {
        "decision_subject_id": source,
        "decision_subject_label": label,
        "task_project_url": website or source,
        "task_source_code_url": source,
        "task_detail_evidence_url": website or source,
        "task_description": listing[0]["text"],
        "task_platforms": list(dict.fromkeys(platforms)),
        "task_licenses": list(dict.fromkeys(licenses)),
        "task_last_update": update_match.group(0) if update_match else "?",
    }


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(locale="en-US")
    page = context.new_page()
    page.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=60_000)
    page.get_by_role("heading", name="Note-taking & Editors", exact=True).wait_for(
        state="visible", timeout=60_000
    )

    headings = page.locator("main h3")
    if headings.count() < 5:
        raise RuntimeError("The category page contains fewer than five projects")
    for index in range(5):
        if not headings.nth(index).inner_text().strip():
            raise RuntimeError("Encountered an empty project heading")

    candidates = [project_listing(page, label) for label in SHORTLIST]
    for candidate in candidates:
        detail = context.new_page()
        detail.goto(
            str(candidate["task_detail_evidence_url"]),
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        if not detail.url.startswith(("http://", "https://")):
            raise RuntimeError("A project detail page did not load")
        detail.close()
    browser.close()

notes = {
    "flatnotes": (
        "Its flat-folder Markdown storage and Docker packaging make it a focused "
        "personal option with a relatively understandable data model.",
        "Its narrower feature set may be limiting if collaboration becomes important.",
    ),
    "HedgeDoc": (
        "Its real-time collaborative Markdown workflow is useful when notes need "
        "to be shared and edited with other people.",
        "A collaborative service is more infrastructure than I need for private notes.",
    ),
    "Joplin": (
        "Its desktop and mobile clients, Markdown editor, and encryption support "
        "make it a mature cross-device option.",
        "Its client-and-sync architecture is broader and more involved than a "
        "minimal browser-based notebook.",
    ),
}
for candidate in candidates:
    fit, tradeoff = notes[str(candidate["decision_subject_label"])]
    candidate["task_fit_note"] = fit
    candidate["task_tradeoff_note"] = tradeoff

selected = next(
    candidate
    for candidate in candidates
    if candidate["decision_subject_label"] == "flatnotes"
)
payload = {
    "decision_subject_id": selected["decision_subject_id"],
    "decision_subject_label": selected["decision_subject_label"],
    "decision_outcome": "selected",
    "basis_primary": "convenience",
    "basis_secondary": "fit",
    "exploration_style": "compared_multiple",
    "reason": (
        "I would try flatnotes first because its Markdown files and Docker setup "
        "look easier for me to understand and maintain than a larger collaborative "
        "service, while still keeping my notes under my control."
    ),
    "task_source_url": SOURCE_URL,
    "task_category_label": "Note-taking & Editors",
    "task_projects_reviewed_count": 5,
    "task_shortlist": candidates,
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

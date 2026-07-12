"""Verifier for the price-perturbation purchase-intent survey.

Runs inside the task container: validates the agent's output at
/app/output/purchase_decision.json against the six-field survey schema.
Standalone (no repo imports) and returns a process exit code, matching
the persona-survey verifier convention.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUTPUT_PATH = Path("/app/output/purchase_decision.json")

ALLOWED = {
    "purchase_intent": {
        "definitely_would_buy",
        "probably_would_buy",
        "might_or_might_not",
        "probably_would_not",
        "definitely_would_not",
    },
    "price_fairness": {
        "much_too_high",
        "somewhat_high",
        "about_right",
        "good_value",
        "great_value",
    },
    "alternative_seeking": {"yes", "no"},
    "purchase_timing": {"buy_now", "wait_for_sale", "not_planning_to_buy"},
    "necessity_level": {
        "essential",
        "important_but_not_urgent",
        "nice_to_have",
    },
}
REQUIRED_FIELDS = (*ALLOWED.keys(), "reasoning")


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main() -> int:
    if not OUTPUT_PATH.is_file():
        return fail(f"missing {OUTPUT_PATH}")
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return fail(f"purchase_decision.json is not valid JSON: {exc}")
    if not isinstance(data, dict):
        return fail("purchase_decision.json must contain a JSON object")

    keys = set(data)
    missing = set(REQUIRED_FIELDS) - keys
    if missing:
        return fail(f"missing fields: {sorted(missing)}")
    extra = keys - set(REQUIRED_FIELDS)
    if extra:
        return fail(f"unexpected fields: {sorted(extra)}")

    for field, allowed in ALLOWED.items():
        value = data[field]
        if value not in allowed:
            return fail(f"{field}={value!r} not in {sorted(allowed)}")

    reasoning = data["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        return fail("reasoning must be a non-empty string")

    print("purchase_decision.json is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

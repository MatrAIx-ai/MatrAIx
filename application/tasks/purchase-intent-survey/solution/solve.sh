#!/bin/bash
set -euo pipefail

mkdir -p /app/output

# Reference solution. Reads the injected persona's economic posture (if
# present) and writes a schema-valid purchase_decision.json whose answers
# are internally consistent for that posture. This exists to prove the
# task is solvable and to exercise the verifier — a real run has the
# assigned persona reason through the survey itself.
python3 <<'PY'
import json
import re
from pathlib import Path

output = Path("/app/output/purchase_decision.json")
persona_path = Path("/app/input/persona.yaml")

posture = "Value-driven"
if persona_path.is_file():
    match = re.search(
        r"economic_motivation:\s*(.+)", persona_path.read_text(encoding="utf-8")
    )
    if match:
        posture = match.group(1).strip().strip("'\"")

# One internally consistent answer set per spending posture, for a ~25%
# price increase on a discretionary $25 drinkware item.
DECISIONS = {
    "Cost-sensitive": {
        "purchase_intent": "probably_would_not",
        "price_fairness": "somewhat_high",
        "alternative_seeking": "yes",
        "purchase_timing": "wait_for_sale",
        "necessity_level": "nice_to_have",
        "reasoning": (
            "At the higher price this is a want, not a need, and I can find a "
            "cheaper tumbler that does the same job, so I'd wait for a sale."
        ),
    },
    "Value-driven": {
        "purchase_intent": "might_or_might_not",
        "price_fairness": "somewhat_high",
        "alternative_seeking": "yes",
        "purchase_timing": "wait_for_sale",
        "necessity_level": "important_but_not_urgent",
        "reasoning": (
            "The Stanley is well made and highly rated, but the increase pushes "
            "it past what I'd happily pay, so I'd compare options and hold out "
            "for a better price."
        ),
    },
    "Premium-seeking": {
        "purchase_intent": "probably_would_buy",
        "price_fairness": "about_right",
        "alternative_seeking": "no",
        "purchase_timing": "buy_now",
        "necessity_level": "important_but_not_urgent",
        "reasoning": (
            "I want this specific tumbler and the quality justifies the price; "
            "a few extra dollars won't change my mind."
        ),
    },
    "Indifferent": {
        "purchase_intent": "might_or_might_not",
        "price_fairness": "about_right",
        "alternative_seeking": "no",
        "purchase_timing": "buy_now",
        "necessity_level": "nice_to_have",
        "reasoning": (
            "The price change is small in absolute terms and I don't track "
            "drinkware prices closely, so it doesn't really sway me either way."
        ),
    },
}

payload = DECISIONS.get(posture, DECISIONS["Value-driven"])
output.write_text(json.dumps(payload, indent=2) + "\n")
PY

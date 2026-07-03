import json
import os
from pathlib import Path


OUTPUT = (
    Path(os.environ.get("PERSONABENCH_OUTPUT_DIR"))
    if os.environ.get("PERSONABENCH_OUTPUT_DIR")
    else Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output"))
) / "pricing_plan_evaluation.json"

PLANS = {"Free", "Pro", "Team", "Enterprise", "Unsure"}
BUDGET_FIT = {"too_expensive", "acceptable", "good_value", "unclear", "not_applicable"}
CONVERSION_INTENT = {"avoid", "compare_more", "consider", "choose"}
RATING_FIELDS = ("fit_rating", "trust_rating")


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "root must be an object"
    return data


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_source_and_plan_are_valid():
    data = _load()
    source_url = data.get("source_url")
    assert isinstance(source_url, str)
    assert source_url.startswith("https://github.com/pricing")
    assert data.get("selected_plan") in PLANS


def test_pricing_metrics_are_present():
    data = _load()
    for field in RATING_FIELDS:
        score = data.get(field)
        assert isinstance(score, int) and not isinstance(score, bool)
        assert 1 <= score <= 10, f"{field} must be 1-10"
    assert data.get("budget_fit") in BUDGET_FIT
    assert data.get("conversion_intent") in CONVERSION_INTENT


def test_persona_report_is_actionable():
    data = _load()
    reason = data.get("reason")
    assert isinstance(reason, str) and len(reason.strip()) >= 30
    friction_points = data.get("friction_points")
    assert isinstance(friction_points, list)
    for point in friction_points:
        assert isinstance(point, str) and point.strip()


def main() -> int:
    test_output_exists()
    test_source_and_plan_are_valid()
    test_pricing_metrics_are_present()
    test_persona_report_is_actionable()
    print("PASS: GitHub pricing task output is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

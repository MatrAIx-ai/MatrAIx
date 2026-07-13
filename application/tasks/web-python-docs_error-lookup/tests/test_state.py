import json
import os
from pathlib import Path


OUTPUT = (
    Path(os.environ.get("PERSONABENCH_OUTPUT_DIR"))
    if os.environ.get("PERSONABENCH_OUTPUT_DIR")
    else Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output"))
) / "python_docs_lookup.json"

RATING_FIELDS = ("documentation_confidence", "ease_of_lookup")


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "root must be an object"
    return data


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_source_and_topic_are_valid():
    data = _load()
    source_url = data.get("source_url")
    assert isinstance(source_url, str)
    assert source_url.startswith("https://docs.python.org/")
    assert data.get("topic") == "pathlib.Path.read_text"


def test_answer_mentions_pathlib_read_text():
    data = _load()
    answer = data.get("answer_summary")
    assert isinstance(answer, str) and len(answer.strip()) >= 40
    normalized = answer.lower()
    assert "read_text" in normalized or "read text" in normalized
    assert "encoding" in normalized


def test_persona_feedback_scores_are_present():
    data = _load()
    for field in RATING_FIELDS:
        score = data.get(field)
        assert isinstance(score, int) and not isinstance(score, bool)
        assert 1 <= score <= 10, f"{field} must be 1-10"
    assert isinstance(data.get("would_reuse_docs"), bool)
    friction_points = data.get("friction_points")
    assert isinstance(friction_points, list)
    for point in friction_points:
        assert isinstance(point, str) and point.strip()


def main() -> int:
    test_output_exists()
    test_source_and_topic_are_valid()
    test_answer_mentions_pathlib_read_text()
    test_persona_feedback_scores_are_present()
    print("PASS: Python docs lookup task output is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

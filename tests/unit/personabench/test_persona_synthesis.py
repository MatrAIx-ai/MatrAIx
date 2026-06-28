"""Tests for schema-grounded synthetic persona vector generation."""

from __future__ import annotations

from pathlib import Path

import yaml

from personabench.persona_synthesis import (
    DEFAULT_CONSTRAINTS_PATH,
    load_catalog_values,
    load_readable_constraints,
    synthesize_persona_dataset,
    validate_schema_values,
    violated_constraints,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_readable_constraints_parse_expected_rules() -> None:
    rules = load_readable_constraints(DEFAULT_CONSTRAINTS_PATH, root=REPO_ROOT)

    assert len(rules) == 115
    assert any(
        rule.dim1 == "age_bracket"
        and rule.val1 == "13–17"
        and rule.dim2 == "life_stage"
        and rule.val2 == "Retirement"
        for rule in rules
    )


def test_readable_constraints_reject_invalid_pair() -> None:
    rules = load_readable_constraints(DEFAULT_CONSTRAINTS_PATH, root=REPO_ROOT)

    violations = violated_constraints(
        {
            "age_bracket": "13–17",
            "life_stage": "Retirement",
        },
        rules,
    )

    assert len(violations) == 1
    assert violations[0].dim1 == "age_bracket"


def test_schema_validation_rejects_non_catalog_value() -> None:
    catalog_values = load_catalog_values(root=REPO_ROOT)

    errors = validate_schema_values(
        {"age_bracket": "toddler"},
        catalog_values,
    )

    assert errors
    assert "non-catalog value" in errors[0]


def test_synthesize_personas_writes_schema_and_constraint_grounded_dataset(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "synthetic-human"

    manifest = synthesize_persona_dataset(
        out_dir=out_dir,
        count=12,
        seed=7,
        root=REPO_ROOT,
    )

    assert manifest["count"] == 12
    assert manifest["schema_grounding"]["validation"]["status"] == "passed"
    assert manifest["constraint_validation"]["validation"]["status"] == "passed"
    assert (
        manifest["constraint_validation"]["validation"][
            "applicable_to_generated_dimensions_count"
        ]
        > 0
    )
    for entry in manifest["personas"]:
        payload = yaml.safe_load(Path(entry["path"]).read_text(encoding="utf-8"))
        assert payload["persona_id"].startswith("synth_")
        assert "dimensions" in payload

#!/usr/bin/env python3
"""Validate the one-user Amazon medium_b smoke before bulk submission."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ASSIGNMENT_TYPES = {
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--bucket", default="68")
    args = parser.parse_args()

    assert args.smoke.is_file() and args.smoke.stat().st_size > 0, args.smoke
    rows = [json.loads(line) for line in args.smoke.read_text().splitlines() if line.strip()]
    assert len(rows) == 1, f"expected exactly one smoke row, got {len(rows)}"
    row = rows[0]
    assert row.get("user_bucket") == args.bucket, row.get("user_bucket")
    assert row.get("prompt_variant") == "medium_b", row.get("prompt_variant")

    selected = pd.read_parquet(args.selection, columns=["user_id", "user_bucket"])
    expected_users = set(selected.loc[selected.user_bucket == args.bucket, "user_id"])
    assert row.get("user_id") in expected_users, "smoke user is outside authoritative selection"

    schema = json.loads(args.schema.read_text())
    dimensions = schema["dimensions"]
    expected_ids = [dimension["id"] for dimension in dimensions]
    dimensions_by_id = {dimension["id"]: dimension for dimension in dimensions}
    fields = row.get("fields")
    assert isinstance(fields, list), "fields is not a list"
    field_ids = [field.get("field_id") for field in fields]
    assert len(fields) == len(expected_ids) == 1290, (len(fields), len(expected_ids))
    assert len(set(field_ids)) == len(field_ids), "duplicate field_id"
    assert set(field_ids) == set(expected_ids), "field IDs do not match schema"

    non_null = 0
    for field in fields:
        field_id = field["field_id"]
        dimension = dimensions_by_id[field_id]
        value = field.get("value")
        assignment = field.get("assignment_type")
        assert assignment in ASSIGNMENT_TYPES, (field_id, assignment)
        if value is None:
            assert assignment == "unsupported", field_id
            assert float(field.get("confidence", 0.0)) == 0.0, field_id
            assert (field.get("evidence") or "") == "", field_id
            assert (field.get("description") or "") == "", field_id
            continue
        non_null += 1
        allowed = dimension.get("values") or []
        assert value in allowed, (field_id, value)
        assert assignment != "unsupported", field_id
        assert (field.get("evidence") or "").strip(), f"missing evidence: {field_id}"
        confidence = float(field.get("confidence", 0.0))
        assert 0.0 <= confidence <= 1.0, (field_id, confidence)

    print(
        f"SMOKE_VALID bucket={args.bucket} user_id={row['user_id']} "
        f"fields={len(fields)} non_null={non_null} prompt_variant=medium_b"
    )


if __name__ == "__main__":
    main()
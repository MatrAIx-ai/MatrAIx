"""Load optional per-task ``persona_strategy.json`` (Playground sampling defaults)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PERSONA_STRATEGY_FILENAME = "persona_strategy.json"
PERSONA_SAMPLING_MODES = frozenset({"single", "random", "stratified"})


def persona_strategy_path(task_dir: Path) -> Path:
    return task_dir / PERSONA_STRATEGY_FILENAME


def load_persona_strategy(task_dir: Path) -> dict[str, Any] | None:
    """Return a normalized strategy dict, or ``None`` when the file is absent/invalid."""
    path = persona_strategy_path(task_dir)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return normalize_persona_strategy(raw)


def normalize_persona_strategy(raw: dict[str, Any]) -> dict[str, Any]:
    schema_version = str(raw.get("schemaVersion") or "1.0").strip() or "1.0"
    pool = str(raw.get("pool") or "").strip() or None
    default_mode = str(raw.get("defaultMode") or "").strip().lower()
    if default_mode not in PERSONA_SAMPLING_MODES:
        default_mode = None

    sources = _as_str_list(raw.get("sources"))
    dimension_filters = _as_dimension_filters(raw.get("dimensionFilters"))
    stratify_fields = _as_str_list(raw.get("stratifyFields"))

    sample_size = raw.get("sampleSize")
    if isinstance(sample_size, bool) or not isinstance(sample_size, (int, float)):
        sample_size = None
    else:
        sample_size = int(sample_size)
        if sample_size < 1:
            sample_size = None

    seed = raw.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, (int, float)):
        seed = None
    else:
        seed = int(seed)

    cohort_id = str(raw.get("cohortId") or "").strip() or None
    sample_size_per_value_group = raw.get("sampleSizePerValueGroup")
    if isinstance(sample_size_per_value_group, bool) or not isinstance(
        sample_size_per_value_group, (int, float)
    ):
        sample_size_per_value_group = None
    else:
        sample_size_per_value_group = int(sample_size_per_value_group)
        if sample_size_per_value_group < 1:
            sample_size_per_value_group = None

    payload: dict[str, Any] = {
        "schemaVersion": schema_version,
        "sources": sources,
        "dimensionFilters": dimension_filters,
    }
    if pool:
        payload["pool"] = pool
    if default_mode:
        payload["defaultMode"] = default_mode
    if stratify_fields:
        payload["stratifyFields"] = stratify_fields
    if sample_size is not None:
        payload["sampleSize"] = sample_size
    if seed is not None:
        payload["seed"] = seed
    if cohort_id:
        payload["cohortId"] = cohort_id
    if sample_size_per_value_group is not None:
        payload["sampleSizePerValueGroup"] = sample_size_per_value_group
    return payload


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_dimension_filters(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, raw in value.items():
        dim = str(key).strip()
        if not dim:
            continue
        if isinstance(raw, list):
            values = [str(item).strip() for item in raw if str(item).strip()]
        elif raw is None:
            values = []
        else:
            text = str(raw).strip()
            values = [text] if text else []
        if values:
            out[dim] = values
    return out

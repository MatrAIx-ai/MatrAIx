from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


_USE_COLS = [
    "id",
    "external_id",
    "title",
    "tags",
    "description",
    "movie_description",
    "display_text",
    "visited_num",
    "release_year",
    "runtime_minutes",
    "languages",
    "countries",
]
_CATEGORICAL_COLS = ["tags"]


@dataclass(frozen=True)
class RecAIResourceSpec:
    domain: str
    resource_dir: Path
    item_info_file: Path
    table_col_desc_file: Path
    settings_file: Path
    item_sim_file: Path
    model_ckpt_file: Path
    use_cols: list[str]
    categorical_cols: list[str]


def load_catalog_items(path: str | Path) -> list[dict[str, Any]]:
    catalog_path = Path(path).expanduser().resolve()
    items: list[dict[str, Any]] = []
    with catalog_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on catalog line {line_number}: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"catalog line {line_number} must be a JSON object")
            items.append(item)
    if not items:
        raise ValueError(f"catalog is empty: {catalog_path}")
    return items


def ensure_recai_resource_dir(
    catalog_path: str | Path,
    output_dir: str | Path,
    domain: str,
) -> RecAIResourceSpec:
    catalog_items = [
        item for item in load_catalog_items(catalog_path) if item.get("domain") == domain
    ]
    if not catalog_items:
        raise ValueError(f"catalog contains no items for domain '{domain}'")

    resource_dir = Path(output_dir).expanduser().resolve()
    resource_dir.mkdir(parents=True, exist_ok=True)

    item_info_file = resource_dir / "item_info.parquet"
    table_col_desc_file = resource_dir / "table_col_desc.json"
    settings_file = resource_dir / "settings.json"
    item_sim_file = resource_dir / "item_sim.npy"
    model_ckpt_file = resource_dir / "model.ckpt"

    rows = [_dummy_row()] + [
        _to_recai_row(index, item) for index, item in enumerate(catalog_items, start=1)
    ]
    pd.DataFrame(rows, columns=_USE_COLS).to_parquet(item_info_file, index=False)

    table_col_desc_file.write_text(
        json.dumps(_column_descriptions(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    settings_file.write_text(
        json.dumps(
            {
                "GAME_INFO_FILE": item_info_file.name,
                "TABLE_COL_DESC_FILE": table_col_desc_file.name,
                "MODEL_CKPT_FILE": model_ckpt_file.name,
                "ITEM_SIM_FILE": item_sim_file.name,
                "USE_COLS": list(_USE_COLS),
                "CATEGORICAL_COLS": list(_CATEGORICAL_COLS),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _ensure_item_similarity(item_sim_file, rows)

    return RecAIResourceSpec(
        domain=domain,
        resource_dir=resource_dir,
        item_info_file=item_info_file,
        table_col_desc_file=table_col_desc_file,
        settings_file=settings_file,
        item_sim_file=item_sim_file,
        model_ckpt_file=model_ckpt_file,
        use_cols=list(_USE_COLS),
        categorical_cols=list(_CATEGORICAL_COLS),
    )


def _to_recai_row(internal_id: int, item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    categories = item.get("categories") if isinstance(item.get("categories"), list) else []
    return {
        "description": str(item.get("description") or ""),
        "id": internal_id,
        "external_id": str(item["item_id"]),
        "title": str(item["title"]),
        "tags": [str(category) for category in categories if category is not None],
        "movie_description": str(item.get("description") or ""),
        "display_text": str(item.get("display_text") or item.get("description") or item["title"]),
        "visited_num": _visited_num(item),
        "release_year": _metadata_number(metadata, "release_year"),
        "runtime_minutes": _metadata_number(metadata, "runtime_minutes"),
        "languages": _join_values(metadata.get("languages", [])),
        "countries": _join_values(metadata.get("countries", [])),
    }


def _dummy_row() -> dict[str, Any]:
    return {
        "id": 0,
        "external_id": "__dummy__",
        "title": "__dummy__",
        "tags": ["__dummy__"],
        "description": "",
        "movie_description": "",
        "display_text": "",
        "visited_num": 0,
        "release_year": 0,
        "runtime_minutes": 0,
        "languages": "",
        "countries": "",
    }


def _join_values(values: Any) -> str:
    if values is None:
        return ""
    if isinstance(values, list):
        return ", ".join(str(value) for value in values if value is not None)
    return str(values)


def _metadata_number(metadata: dict[str, Any], key: str) -> int | float:
    value = metadata.get(key)
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return value
    return 0


def _visited_num(item: dict[str, Any]) -> int:
    signals = item.get("signals") if isinstance(item.get("signals"), dict) else {}
    for key in ("visited_num", "review_count", "rating_number", "rating_count", "popularity"):
        value = signals.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            if key == "popularity" and 0 <= value <= 1:
                return max(1, int(round(value * 1000)))
            return max(1, int(round(value)))
    return 1


def _column_descriptions() -> dict[str, str]:
    return {
        "id": "Internal integer item id used by RecAI tools.",
        "external_id": "Stable item id from the MatrAIx normalized catalog.",
        "title": "Human-readable item title.",
        "tags": "Comma-separated normalized item categories.",
        "description": "Source item description, plot, or product detail.",
        "movie_description": "Alias of description for RecAI movie-domain lookup prompts.",
        "display_text": "Combined title, description, and metadata text for recommendation reasoning.",
        "visited_num": "Popularity-like count derived from source catalog signals.",
        "release_year": "Release year when available, otherwise 0.",
        "runtime_minutes": "Runtime in minutes when available, otherwise 0.",
        "languages": "Comma-separated language metadata.",
        "countries": "Comma-separated country metadata.",
    }


def _ensure_item_similarity(item_sim_file: Path, rows: list[dict[str, Any]]) -> None:
    real_rows = [row for row in rows if int(row["id"]) > 0]
    expected_size = max((int(row["id"]) for row in real_rows), default=0) + 1
    if _has_expected_similarity_shape(item_sim_file, expected_size):
        return
    max_runtime_items = _runtime_similarity_max_items()
    if len(real_rows) > max_runtime_items:
        raise RuntimeError(
            "full RecAI similarity matrix is missing for this catalog. "
            f"Expected {item_sim_file} with shape ({expected_size}, {expected_size}). "
            "RecAI's native SimilarItemTool loads a dense item_sim.npy at startup; "
            "generate it offline or point INTERECAGENT_GENERATED_RESOURCE_DIR to a complete resource directory."
        )
    np.save(item_sim_file, _build_item_similarity(rows), allow_pickle=False)


def _has_expected_similarity_shape(item_sim_file: Path, expected_size: int) -> bool:
    if not item_sim_file.exists():
        return False
    try:
        item_sim = np.load(item_sim_file, allow_pickle=False, mmap_mode="r")
    except Exception:
        return False
    return tuple(item_sim.shape) == (expected_size, expected_size)


def _build_item_similarity(rows: list[dict[str, Any]]) -> np.ndarray:
    real_rows = [row for row in rows if int(row["id"]) > 0]
    vectors = {int(row["id"]): _text_vector(_row_text(row)) for row in real_rows}
    size = max(vectors.keys(), default=0) + 1
    similarity = np.zeros((size, size), dtype=np.float32)
    for row_id in vectors:
        similarity[row_id, row_id] = 1.0
    row_ids = sorted(vectors)
    for left_index, left_id in enumerate(row_ids):
        for right_id in row_ids[left_index + 1 :]:
            score = _cosine(vectors[left_id], vectors[right_id])
            similarity[left_id, right_id] = score
            similarity[right_id, left_id] = score
    return similarity


def _runtime_similarity_max_items() -> int:
    raw_value = os.environ.get("INTERECAGENT_RUNTIME_SIMILARITY_MAX_ITEMS", "2000")
    try:
        return max(0, int(raw_value))
    except ValueError:
        return 2000


def _row_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row[column])
        for column in ("title", "tags", "description", "display_text")
        if row.get(column)
    )


def _text_vector(text: str) -> Counter[str]:
    return Counter(_tokenize(text))


def _tokenize(text: str) -> Iterable[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in overlap)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return float(numerator / (left_norm * right_norm))

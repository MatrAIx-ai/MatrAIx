from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
DEFAULT_RESOURCE_DIR = (
    REPO_ROOT
    / "data"
    / "cache"
    / "recommendation_chatbot_eval"
    / "recai_resources"
    / "movie"
)


def _row_text(row: pd.Series) -> str:
    parts: list[str] = []
    for column in ("title", "tags", "description", "movie_description", "display_text"):
        value = row.get(column)
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item is not None)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts)


def _load_item_info(item_info_path: Path) -> pd.DataFrame:
    if not item_info_path.exists():
        raise FileNotFoundError(f"missing item_info parquet: {item_info_path}")
    item_info = pd.read_parquet(item_info_path)
    if "id" not in item_info.columns:
        raise ValueError(f"{item_info_path} must include an id column")
    item_info = item_info.sort_values("id").reset_index(drop=True)
    expected_ids = list(range(int(item_info["id"].max()) + 1))
    actual_ids = [int(item_id) for item_id in item_info["id"].tolist()]
    if actual_ids != expected_ids:
        raise ValueError("item_info ids must be contiguous and start at 0")
    return item_info


def _dtype_from_name(name: str) -> Any:
    if name == "float16":
        return np.float16
    if name == "float32":
        return np.float32
    raise ValueError("--dtype must be float16 or float32")


def generate_item_similarity(
    item_info_path: Path,
    output_path: Path,
    *,
    block_size: int = 128,
    dtype: Any = np.float16,
    max_features: int | None = 50000,
    min_df: int = 2,
    force: bool = False,
    progress: bool = False,
) -> dict[str, Any]:
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    item_info_path = Path(item_info_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    if output_path.exists() and not force:
        existing = np.load(output_path, allow_pickle=False, mmap_mode="r")
        return {
            "output_path": str(output_path),
            "shape": list(existing.shape),
            "dtype": str(existing.dtype),
            "skipped": True,
        }

    item_info = _load_item_info(item_info_path)
    texts = [_row_text(row) for _index, row in item_info.iterrows()]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        dtype=np.float32,
        max_df=0.8,
        min_df=min_df,
        max_features=max_features,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b\w\w+\b",
    )
    vectors = normalize(vectorizer.fit_transform(texts), norm="l2", copy=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(output_path.name + ".tmp.npy")
    if tmp_path.exists():
        tmp_path.unlink()

    item_count = vectors.shape[0]
    matrix = np.lib.format.open_memmap(
        tmp_path,
        mode="w+",
        dtype=dtype,
        shape=(item_count, item_count),
    )
    matrix[:] = 0
    for start in range(0, item_count, block_size):
        end = min(start + block_size, item_count)
        block = (vectors[start:end] @ vectors.T).toarray()
        block = np.clip(block, 0.0, 1.0)
        matrix[start:end, :] = block.astype(dtype, copy=False)
        if progress:
            print(f"wrote rows {start}-{end - 1} / {item_count - 1}", file=sys.stderr)
    np.fill_diagonal(matrix, dtype(1.0))
    del matrix

    os.replace(tmp_path, output_path)
    generated = np.load(output_path, allow_pickle=False, mmap_mode="r")
    return {
        "output_path": str(output_path),
        "shape": list(generated.shape),
        "dtype": str(generated.dtype),
        "skipped": False,
        "vocab_size": len(vectorizer.vocabulary_),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate RecAI dense item_sim.npy for a catalog resource directory.")
    parser.add_argument("--resource-dir", type=Path, default=DEFAULT_RESOURCE_DIR)
    parser.add_argument("--item-info", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--block-size", type=int, default=128)
    parser.add_argument("--dtype", choices=["float16", "float32"], default="float16")
    parser.add_argument("--max-features", type=int, default=50000)
    parser.add_argument("--min-df", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    item_info_path = args.item_info or args.resource_dir / "item_info.parquet"
    output_path = args.output or args.resource_dir / "item_sim.npy"
    stats = generate_item_similarity(
        item_info_path,
        output_path,
        block_size=args.block_size,
        dtype=_dtype_from_name(args.dtype),
        max_features=args.max_features,
        min_df=args.min_df,
        force=args.force,
        progress=not args.quiet,
    )
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

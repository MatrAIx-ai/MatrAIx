#!/usr/bin/env python3
"""Report complete / partial / untouched buckets for the Amazon 100K extraction.

Compares each output shard's unique user_ids against the selected-user count per bucket
in selected_users_100k.parquet, across all 256 hex buckets (00..ff). Prints the partial
list (with have/selected) and the untouched list, plus the remaining-user total.

Defaults assume the upstream repo layout; override with env vars:
  SELECTION_PATH   path to selected_users_100k.parquet
  OUT_DIRS         ':'-separated list of dirs holding shard_<bkt>.jsonl outputs

Needs pyarrow (for parquet). Example:
  OUT_DIRS=/scratch/me/casper_out:/scratch/me/a100_out \
      python persona/human_extraction/scripts/report_remaining_buckets.py
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
# .../persona/human_extraction/scripts/report_remaining_buckets.py -> human_extraction dir
HE_DIR = HERE.parents[1]

SELECTION = Path(
    os.environ.get(
        "SELECTION_PATH", HE_DIR / "data/amazon/selected_users_100k.parquet"
    )
)
_default_out = HE_DIR / "data/amazon/extraction_v1"
OUT_DIRS = [
    Path(p) for p in os.environ.get("OUT_DIRS", str(_default_out)).split(":") if p
]


def unique_users(path: str) -> int:
    seen: set = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                seen.add(json.loads(line).get("user_id"))
            except json.JSONDecodeError:
                pass
    return len(seen)


def main() -> None:
    if not SELECTION.is_file():
        raise SystemExit(
            f"selection index not found: {SELECTION}\n"
            "Set SELECTION_PATH, or regenerate it (see explore_amazon_data.ipynb)."
        )
    sel = pd.read_parquet(SELECTION, columns=["user_bucket"])
    selected = {b: int(n) for b, n in sel["user_bucket"].value_counts().items()}
    all_buckets = [f"{i:02x}" for i in range(256)]

    done: dict[str, int] = {}
    for d in OUT_DIRS:
        for f in glob.glob(str(d / "shard_*.jsonl")):
            b = Path(f).name.split("shard_")[1].split(".")[0]
            done[b] = done.get(b, 0) + unique_users(f)

    complete = [b for b in all_buckets if done.get(b, 0) >= selected.get(b, 10**9)]
    partial = [b for b in all_buckets if 0 < done.get(b, 0) < selected.get(b, 10**9)]
    untouched = [b for b in all_buckets if done.get(b, 0) == 0]
    remaining = sum(selected.get(b, 0) - done.get(b, 0) for b in partial) + sum(
        selected.get(b, 0) for b in untouched
    )

    print(f"scanned dirs : {[str(d) for d in OUT_DIRS]}")
    print(f"complete : {len(complete)}")
    print(f"partial  : {len(partial)}")
    for b in partial:
        print(f"    {b}  {done[b]}/{selected[b]}")
    print(f"untouched: {len(untouched)}  -> {','.join(untouched)}")
    print(f"remaining users: {remaining} of {sum(selected.values())}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Select top Amazon reviewers for staged persona inference.

The input is the user-level eligible-reviewer artifact already built from the
Amazon Reviews 2023 dataset. The script ranks eligible users by signals that
should make persona extraction richer: review text volume, text-review count,
category breadth, history length, review count, and verified-purchase share.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download


DEFAULT_REPO_ID = "MatrAIx/MatrAIx"
DEFAULT_ARTIFACT = (
    "amazon/modal_artifacts/"
    "amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000"
)
DEFAULT_OUTPUT_DIR = (
    "personas/existing_data_curation/samples/"
    "amazon_reviews_2023/top_reviewers"
)


RANKING_WEIGHTS = {
    "text_chars": 0.35,
    "text_reviews": 0.20,
    "category_count": 0.20,
    "history_days": 0.15,
    "review_count": 0.05,
    "verified_share": 0.05,
}


def json_safe(value: object) -> object:
    """Convert pandas/numpy scalar and array values to JSON-safe Python values."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return str(value)
    return value


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--artifact", default=DEFAULT_ARTIFACT)
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--top-k", type=int, default=10_000)
    parser.add_argument("--repo-type", default="dataset")
    return parser.parse_args(argv)


def load_eligible_users(repo_id: str, repo_type: str, artifact: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for bucket_id in range(256):
        bucket = f"{bucket_id:02x}"
        filename = f"{artifact}/bucket={bucket}/eligible_users.parquet"
        local_path = hf_hub_download(
            repo_id=repo_id,
            repo_type=repo_type,
            filename=filename,
        )
        frame = pq.read_table(local_path).to_pandas()
        if "user_bucket" not in frame.columns:
            frame["user_bucket"] = bucket
        frames.append(frame)
        if (bucket_id + 1) % 32 == 0:
            print(
                f"Loaded {bucket_id + 1}/256 buckets; "
                f"{sum(len(f) for f in frames):,} rows",
                flush=True,
            )
    return pd.concat(frames, ignore_index=True)


def rank_users(users: pd.DataFrame, top_k: int) -> pd.DataFrame:
    users = users.copy()
    for column in [
        "review_count",
        "category_count",
        "history_days",
        "history_years",
        "text_chars",
        "text_reviews",
        "verified_share",
        "verified_count",
        "rating_count",
        "average_rating",
    ]:
        if column not in users.columns:
            users[column] = 0
        users[column] = pd.to_numeric(users[column], errors="coerce").fillna(0)

    if {"first_date", "last_date"}.issubset(users.columns):
        first_dates = pd.to_datetime(users["first_date"], errors="coerce")
        last_dates = pd.to_datetime(users["last_date"], errors="coerce")
        computed_history_days = (last_dates - first_dates).dt.days.fillna(0).clip(lower=0)
        users["history_days"] = computed_history_days.where(
            computed_history_days > users["history_days"], users["history_days"]
        )
        users["history_years"] = (users["history_days"] / 365.25).round(3)

    users["text_reviews"] = users["text_reviews"].where(
        users["text_reviews"] > 0, users["review_count"]
    )
    users["chars_per_text_review"] = (
        users["text_chars"] / users["text_reviews"].clip(lower=1)
    ).round(3)

    users["rich_persona_score"] = 0.0
    for source_column, weight in RANKING_WEIGHTS.items():
        rank_column = f"{source_column}_rank"
        users[rank_column] = users[source_column].rank(method="average", pct=True)
        users["rich_persona_score"] += users[rank_column] * weight

    ranked = users.sort_values(
        by=[
            "rich_persona_score",
            "text_chars",
            "category_count",
            "history_days",
            "review_count",
            "verified_share",
            "user_id",
        ],
        ascending=[False, False, False, False, False, False, True],
    ).reset_index(drop=True)

    top = ranked.head(top_k).copy()
    top.insert(0, "rank", range(1, len(top) + 1))
    return top


def quantiles(series: pd.Series) -> dict[str, float]:
    return {
        str(q): float(series.quantile(q))
        for q in [0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0]
    }


def write_outputs(
    top: pd.DataFrame,
    source_count: int,
    output_dir: Path,
    repo_id: str,
    artifact: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "amazon_top_10000_rich_persona_reviewers_2018_2023"
    jsonl_path = output_dir / f"{stem}.jsonl"
    csv_path = output_dir / f"{stem}.csv"
    ids_path = output_dir / "amazon_top_10000_rich_persona_reviewer_ids_2018_2023.txt"
    markdown_path = output_dir / f"{stem}.md"
    summary_json_path = output_dir / f"{stem}_summary.json"

    fields = [
        "rank",
        "user_id",
        "user_bucket",
        "rich_persona_score",
        "review_count",
        "text_reviews",
        "text_chars",
        "chars_per_text_review",
        "category_count",
        "history_days",
        "history_years",
        "verified_share",
        "verified_count",
        "rating_count",
        "average_rating",
        "first_date",
        "last_date",
        "categories",
    ]
    for field in fields:
        if field not in top.columns:
            top[field] = None

    records = []
    for row in top[fields].to_dict(orient="records"):
        records.append({key: json_safe(value) for key, value in row.items()})

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_records = []
    for row in records:
        csv_row = row.copy()
        if isinstance(csv_row.get("categories"), list):
            csv_row["categories"] = "|".join(str(item) for item in csv_row["categories"])
        csv_records.append(csv_row)
    pd.DataFrame(csv_records, columns=fields).to_csv(csv_path, index=False)
    ids_path.write_text(
        "\n".join(top["user_id"].astype(str).tolist()) + "\n",
        encoding="utf-8",
    )

    summary = {
        "source_dataset": repo_id,
        "source_artifact": artifact,
        "source_rows": int(source_count),
        "selected_rows": int(len(top)),
        "eligibility_filter_in_source_artifact": {
            "time_window": "2018-2023",
            "review_count": ">= 30",
            "verified_share": ">= 0.70",
            "text_chars": ">= 2000",
        },
        "ranking_weights": RANKING_WEIGHTS,
        "selected_quantiles": {
            metric: quantiles(top[metric])
            for metric in [
                "review_count",
                "text_reviews",
                "text_chars",
                "category_count",
                "history_days",
                "verified_share",
                "rich_persona_score",
            ]
        },
    }
    summary_json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Amazon Top 10K Rich Persona Reviewers",
        "",
        (
            "This file documents a reusable top-10K Amazon reviewer pool for "
            "persona inference. It is intended for staged inference runs when "
            "running all eligible users at once is too expensive."
        ),
        "",
        "## Source",
        "",
        f"- Hugging Face dataset: `{repo_id}`",
        f"- Source artifact: `{artifact}`",
        "- Source artifact time window: `2018-2023`",
        (
            "- Source eligibility filter: `review_count >= 30`, "
            "`verified_share >= 0.70`, `text_chars >= 2000`"
        ),
        f"- Eligible rows loaded: `{source_count:,}`",
        f"- Selected rows: `{len(top):,}`",
        "",
        "## Output Files",
        "",
        (
            "- `amazon_top_10000_rich_persona_reviewer_ids_2018_2023.txt`: "
            "one user ID per line for retrieval/inference jobs."
        ),
        (
            "- `amazon_top_10000_rich_persona_reviewers_2018_2023.jsonl`: "
            "ranked users with scoring metrics and category metadata."
        ),
        (
            "- `amazon_top_10000_rich_persona_reviewers_2018_2023.csv`: "
            "same ranked table in CSV form for quick inspection."
        ),
        "",
        "## Ranking Score",
        "",
        (
            "The ranking score is a weighted sum of percentile ranks across "
            "richness signals. Percentile ranks are used because Amazon review "
            "activity is heavy-tailed."
        ),
        "",
        "| Signal | Weight | Why it matters |",
        "|---|---:|---|",
        "| `text_chars` | 0.35 | More written evidence for values, preferences, routines, and decision style. |",
        "| `text_reviews` | 0.20 | More distinct text-bearing observations. |",
        "| `category_count` | 0.20 | Broader life/product coverage, supporting richer cross-domain personas. |",
        "| `history_days` | 0.15 | Longer temporal history, reducing one-off or short-burst behavior. |",
        "| `review_count` | 0.05 | More total rating/review events, including rating-only behavior. |",
        "| `verified_share` | 0.05 | Higher purchase-verification reliability. |",
        "",
        "## Selected Pool Summary",
        "",
        "| Metric | Min | P25 | Median | P75 | P90 | P99 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for metric in [
        "review_count",
        "text_reviews",
        "text_chars",
        "category_count",
        "history_days",
        "verified_share",
        "rich_persona_score",
    ]:
        values = summary["selected_quantiles"][metric]
        lines.append(
            f"| `{metric}` | {values['0']:.3f} | {values['0.25']:.3f} | "
            f"{values['0.5']:.3f} | {values['0.75']:.3f} | "
            f"{values['0.9']:.3f} | {values['0.99']:.3f} | "
            f"{values['1.0']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Top 20 Preview",
            "",
            "| Rank | User ID | Score | Reviews | Text reviews | Text chars | Categories | History days | Verified share |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for _, row in top.head(20).iterrows():
        lines.append(
            f"| {int(row['rank'])} | `{row['user_id']}` | "
            f"{row['rich_persona_score']:.4f} | {int(row['review_count'])} | "
            f"{int(row['text_reviews'])} | {int(row['text_chars'])} | "
            f"{int(row['category_count'])} | {float(row['history_days']):.1f} | "
            f"{float(row['verified_share']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reproducibility Note",
            "",
            (
                "The selected users are ranked from the existing eligible-user "
                "summary artifact, not by reading raw review text or calling an "
                "LLM. This makes the list cheap to regenerate and suitable as a "
                "shared inference queue."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    users = load_eligible_users(args.repo_id, args.repo_type, args.artifact)
    top = rank_users(users, args.top_k)
    write_outputs(top, len(users), args.output_dir, args.repo_id, args.artifact)
    print(
        json.dumps(
            {
                "source_rows": int(len(users)),
                "selected_rows": int(len(top)),
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from persona.tools.annotation_package.core import (
    DEFAULT_DIMENSIONS,
    build_annotation_package,
    load_dimensions,
    parse_range,
)
from persona.tools.annotation_package.sources.amazon_reviews import (
    SOURCE as AMAZON_SOURCE,
    load_amazon_tasks,
)
from persona.tools.annotation_package.sources.wiki import load_wiki_tasks


def _parse_categories(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _add_make_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("make", help="Build a worker annotation package")
    parser.add_argument("--source", choices=("wiki", "amazon-reviews"), required=True)
    parser.add_argument("--range", required=True, dest="range_spec")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--assignment-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--dimensions", type=Path, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--categories")
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--force", action="store_true")

    wiki = parser.add_argument_group("wiki source")
    wiki.add_argument("--db", type=Path)

    amazon = parser.add_argument_group("amazon review source")
    amazon.add_argument("--user-histories", type=Path)
    amazon.add_argument("--cv-folds", type=int, default=3)
    amazon.add_argument("--min-support-folds", type=int, default=2)
    amazon.add_argument("--max-reviews-per-user", type=int, default=90)
    amazon.add_argument("--max-review-text-chars", type=int, default=900)
    amazon.add_argument("--max-profile-text-chars", type=int, default=70_000)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and validate persona annotation worker packages."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_make_parser(subparsers)
    return parser.parse_args(argv)


def _make(args: argparse.Namespace) -> dict[str, Any]:
    range_start, range_end = parse_range(args.range_spec)
    dimensions = load_dimensions(args.dimensions)
    categories = _parse_categories(args.categories)

    if args.source == "wiki":
        if args.db is None:
            raise SystemExit("--db is required when --source wiki")
        task_rows = load_wiki_tasks(
            args.db,
            range_start=range_start,
            range_end=range_end,
        )
        source = "wiki"
        source_metadata: dict[str, Any] = {}
    else:
        if args.user_histories is None:
            raise SystemExit(
                "--user-histories is required when --source amazon-reviews"
            )
        task_rows = load_amazon_tasks(
            args.user_histories,
            range_start=range_start,
            range_end=range_end,
            cv_folds=args.cv_folds,
            min_support_folds=args.min_support_folds,
            max_reviews_per_user=args.max_reviews_per_user,
            max_review_text_chars=args.max_review_text_chars,
            max_profile_text_chars=args.max_profile_text_chars,
        )
        source = AMAZON_SOURCE
        source_metadata = {
            "cv_folds": args.cv_folds,
            "min_support_folds": args.min_support_folds,
        }

    return build_annotation_package(
        task_rows=task_rows,
        dimensions=dimensions,
        out_dir=args.out_dir,
        assignment_id=args.assignment_id,
        worker_id=args.worker_id,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        range_start=range_start,
        range_end=range_end,
        source=source,
        categories=categories,
        source_metadata=source_metadata,
        create_archive=not args.no_archive,
        force=args.force,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "make":
        summary = _make(args)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

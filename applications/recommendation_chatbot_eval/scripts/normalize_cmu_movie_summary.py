from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]

DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "cmu_movie_summary" / "MovieSummaries"
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT
    / "data"
    / "normalized"
    / "recommendation_catalogs"
    / "cmu_movie_summary"
    / "items.jsonl"
)


def _parse_name_map(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = ast.literal_eval(raw_value)
    except (SyntaxError, ValueError):
        return []
    if not isinstance(parsed, dict):
        return []
    return [_sanitize_text(str(value)) for value in parsed.values() if value]


def _sanitize_text(value: str) -> str:
    return value.encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def _parse_int(raw_value: str) -> int | None:
    if not raw_value:
        return None
    try:
        return int(float(raw_value))
    except ValueError:
        return None


def _release_year(release_date: str) -> int | None:
    if not release_date or len(release_date) < 4:
        return None
    return _parse_int(release_date[:4])


def _metadata_by_movie_id(metadata_path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with metadata_path.open("r", encoding="utf-8") as file:
        for line in file:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9:
                continue
            (
                wikipedia_movie_id,
                freebase_movie_id,
                movie_name,
                release_date,
                box_office_revenue,
                runtime,
                languages,
                countries,
                genres,
            ) = fields
            if not wikipedia_movie_id or not movie_name:
                continue
            rows[wikipedia_movie_id] = {
                "freebase_movie_id": freebase_movie_id,
                "title": _sanitize_text(movie_name),
                "release_date": release_date,
                "release_year": _release_year(release_date),
                "box_office_revenue": _parse_int(box_office_revenue),
                "runtime_minutes": _parse_int(runtime),
                "languages": _parse_name_map(languages),
                "countries": _parse_name_map(countries),
                "genres": _parse_name_map(genres),
            }
    return rows


def _iter_plot_summaries(plot_path: Path):
    with plot_path.open("r", encoding="utf-8") as file:
        for line in file:
            wikipedia_movie_id, separator, summary = line.rstrip("\n").partition("\t")
            if separator and wikipedia_movie_id and summary:
                yield wikipedia_movie_id, _sanitize_text(summary)


def _drop_none_values(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _catalog_item(wikipedia_movie_id: str, summary: str, metadata: dict[str, Any]) -> dict[str, Any]:
    title = metadata["title"]
    categories = metadata["genres"]
    metadata_fields = _drop_none_values(
        {
            "release_date": metadata["release_date"] or None,
            "release_year": metadata["release_year"],
            "runtime_minutes": metadata["runtime_minutes"],
            "languages": metadata["languages"],
            "countries": metadata["countries"],
        }
    )
    signals = _drop_none_values({"box_office_revenue": metadata["box_office_revenue"]})
    category_text = ", ".join(categories) if categories else "Unknown"
    return {
        "item_id": f"cmu:{wikipedia_movie_id}",
        "domain": "movie",
        "title": title,
        "description": summary,
        "display_text": f"{title}. Genres: {category_text}. Plot: {summary}",
        "categories": categories,
        "metadata": metadata_fields,
        "signals": signals,
        "domain_metadata": {
            "freebase_movie_id": metadata["freebase_movie_id"],
        },
        "source": {
            "dataset": "cmu_movie_summary_corpus",
            "license": "Creative Commons Attribution-ShareAlike",
            "original_id": wikipedia_movie_id,
            "url": "https://www.cs.cmu.edu/~ark/personas/",
        },
    }


def normalize_cmu_movie_summary(raw_dir: Path, output_path: Path, limit: int | None = None) -> int:
    raw_dir = Path(raw_dir)
    metadata_path = raw_dir / "movie.metadata.tsv"
    plot_path = raw_dir / "plot_summaries.txt"
    if not metadata_path.exists():
        raise FileNotFoundError(f"missing CMU metadata file: {metadata_path}")
    if not plot_path.exists():
        raise FileNotFoundError(f"missing CMU plot summaries file: {plot_path}")

    metadata_by_id = _metadata_by_movie_id(metadata_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as output:
        for wikipedia_movie_id, summary in _iter_plot_summaries(plot_path):
            metadata = metadata_by_id.get(wikipedia_movie_id)
            if metadata is None:
                continue
            output.write(
                json.dumps(
                    _catalog_item(wikipedia_movie_id, summary, metadata),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
            count += 1
            if limit is not None and count >= limit:
                break
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize the CMU Movie Summary Corpus into catalog JSONL.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    count = normalize_cmu_movie_summary(args.raw_dir, args.output, args.limit)
    print(f"Wrote {count} movie catalog items to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

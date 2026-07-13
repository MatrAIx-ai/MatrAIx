#!/usr/bin/env python3
"""Render persona assignments from JSONL, graph codes, or npy stores.

Examples:
  python persona/synthesis/scripts/render_personas.py \
    --jsonl persona/synthesis/reports/combinatorial_vs_graph_100_20260703/full_dag_graph_100.jsonl \
    --mode text --count 5

  python persona/synthesis/scripts/render_personas.py \
    --codes /tmp/personas_1000000.codes.gz --sample 100 --mode both --out sample.rendered.jsonl

  python persona/synthesis/scripts/render_personas.py \
        --npy-prefix /path/to/personas_1M \
    --index 0 --mode text
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.render import (  # noqa: E402,F401
    BUCKETS,
    CORE_ORDER,
    DEFAULT_DIMS_PATH,
    EXCLUDE_CATEGORY,
    EXCLUDE_PREFIX,
    STATE_IDS,
    _clause,
    _fix_articles,
    _is_default,
    load_dims,
    render,
)
from persona.synthesis.scripts.decode_persona_codes import (  # noqa: E402
    _iter_decoded_rows,
    _load_schema,
)
from persona.synthesis.sampler import codes_schema_path  # noqa: E402

def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _load_npy_store(prefix: Path) -> tuple[np.ndarray, list[str], dict[str, list[Any]]]:
    matrix = np.load(str(prefix) + ".npy", mmap_mode="r")
    codebook = json.loads(Path(str(prefix) + ".codebook.json").read_text())
    return matrix, codebook["columns"], codebook["values"]


def _decode_npy_row(row: np.ndarray, columns: list[str], values: dict[str, list[Any]]) -> dict[str, Any]:
    return {column: values[column][int(row[index])] for index, column in enumerate(columns)}


def _iter_npy(prefix: Path) -> Iterator[dict[str, Any]]:
    matrix, columns, values = _load_npy_store(prefix)
    for row in matrix:
        yield _decode_npy_row(row, columns, values)


def _iter_codes(codes_path: Path, schema_path: Path | None) -> Iterator[dict[str, Any]]:
    schema = _load_schema(codes_path, schema_path)
    yield from _iter_decoded_rows(codes_path, schema)


def _selected_rows(
    rows: Iterable[dict[str, Any]],
    *,
    index: int | None,
    start: int,
    count: int | None,
    sample: int | None,
    seed: int,
) -> Iterator[tuple[int, dict[str, Any]]]:
    if sample is not None:
        rng = np.random.default_rng(seed)
        reservoir: list[tuple[int, dict[str, Any]]] = []
        for row_index, row in enumerate(rows):
            if len(reservoir) < sample:
                reservoir.append((row_index, row))
                continue
            replacement = int(rng.integers(0, row_index + 1))
            if replacement < sample:
                reservoir[replacement] = (row_index, row)
        for row_index, row in sorted(reservoir, key=lambda item: item[0]):
            yield row_index, row
        return

    stop = None if count is None else start + count
    for row_index, row in enumerate(rows):
        if index is not None:
            if row_index == index:
                yield row_index, row
                return
            if row_index > index:
                return
            continue
        if row_index < start:
            continue
        if stop is not None and row_index >= stop:
            return
        yield row_index, row


def _write_record(
    output: Any,
    *,
    mode: str,
    row_index: int,
    assignment: dict[str, Any],
    dims: dict[str, dict[str, Any]] | None,
    stdout_spacing: bool,
    max_clauses_per_bucket: int | None,
) -> None:
    if mode == "attrs":
        output.write(json.dumps(assignment, ensure_ascii=False) + "\n")
    elif mode == "text":
        assert dims is not None
        output.write(render(assignment, dims, max_clauses_per_bucket=max_clauses_per_bucket) + "\n")
        if stdout_spacing:
            output.write("\n")
    else:
        assert dims is not None
        record = {
            "index": row_index,
            "text": render(assignment, dims, max_clauses_per_bucket=max_clauses_per_bucket),
            "attrs": assignment,
        }
        output.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--jsonl", type=Path, help="attribute JSONL input")
    source.add_argument("--codes", type=Path, help="graph persona codes input (.codes or .codes.gz)")
    source.add_argument("--npy-prefix", type=Path, help="combinatorial npy store prefix")
    parser.add_argument("--schema", type=Path, default=None, help="schema sidecar for --codes")
    parser.add_argument("--dims", type=Path, default=DEFAULT_DIMS_PATH, help="dimensions JSON with phrase/defaultValue")
    parser.add_argument("--mode", choices=["attrs", "text", "both"], default="text")
    parser.add_argument("--index", type=int, default=None, help="single row index")
    parser.add_argument("--start", type=int, default=0, help="start row for range mode")
    parser.add_argument("--count", type=int, default=None, help="number of rows in range mode")
    parser.add_argument("--sample", type=int, default=None, help="random sample size; materializes selected input")
    parser.add_argument("--seed", type=int, default=0, help="seed for --sample")
    parser.add_argument(
        "--max-clauses-per-bucket",
        type=int,
        default=30,
        help="maximum rendered clauses per thematic bucket; use 0 for no limit",
    )
    parser.add_argument("--out", type=Path, default=None, help="output path; default stdout")
    args = parser.parse_args()

    if args.jsonl is not None:
        rows = _iter_jsonl(args.jsonl)
    elif args.codes is not None:
        rows = _iter_codes(args.codes, args.schema or codes_schema_path(args.codes))
    else:
        rows = _iter_npy(args.npy_prefix)

    dims = load_dims(args.dims) if args.mode in {"text", "both"} else None
    max_clauses = None if args.max_clauses_per_bucket == 0 else args.max_clauses_per_bucket
    output = args.out.open("w", encoding="utf-8") if args.out else sys.stdout
    try:
        for row_index, assignment in _selected_rows(
            rows,
            index=args.index,
            start=args.start,
            count=args.count,
            sample=args.sample,
            seed=args.seed,
        ):
            _write_record(
                output,
                mode=args.mode,
                row_index=row_index,
                assignment=assignment,
                dims=dims,
                stdout_spacing=args.out is None and args.mode == "text",
                max_clauses_per_bucket=max_clauses,
            )
    finally:
        if args.out:
            output.close()


if __name__ == "__main__":
    main()

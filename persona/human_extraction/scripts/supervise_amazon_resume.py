#!/usr/bin/env python3
"""Validate Amazon continuation buckets and automatically retry gaps."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PARTIAL_BUCKETS = {
    "0f", "10", "13", "16", "1e", "22", "29",
    "2f", "32", "36", "3d", "3f", "47", "4d",
}
UNTOUCHED_BUCKETS = {"30", *(f"{value:02x}" for value in range(0x68, 0x100))}
TARGET_BUCKETS = sorted(PARTIAL_BUCKETS | UNTOUCHED_BUCKETS)
HF_EXISTING_UNIQUE = 38_219
SEEDED_PARTIAL_UNIQUE = 3_549


def compact_array(values: list[int]) -> str:
    if not values:
        return ""
    result: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        result.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    result.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(result)


def read_ids(path: Path) -> tuple[set[str], int]:
    user_ids: set[str] = set()
    invalid = 0
    if not path.exists():
        return user_ids, invalid
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
                user_id = row.get("user_id")
                if not user_id:
                    invalid += 1
                    continue
                user_ids.add(str(user_id))
            except (json.JSONDecodeError, TypeError):
                invalid += 1
    return user_ids, invalid


def submit_retry(args: argparse.Namespace, buckets: list[str]) -> tuple[str, str]:
    array_spec = compact_array(sorted(int(bucket, 16) for bucket in buckets)) + "%40"
    job_name = f"amazon_resume_h200_r{args.round}"
    job_id = subprocess.check_output(
        [
            "sbatch", "--parsable", f"--job-name={job_name}",
            f"--array={array_spec}",
            f"--export=ALL,OUT_DIR={args.out_dir},LIMIT=0",
            str(args.jobs_dir / "extract_shard_amazon_h200.job"),
        ],
        cwd=args.jobs_dir,
        text=True,
    ).strip()
    next_supervisor = subprocess.check_output(
        [
            "sbatch", "--parsable", "--job-name=amazon_resume_supervisor",
            f"--dependency=afterany:{job_id}", "--kill-on-invalid-dep=yes",
            f"--export=ALL,ROUND={args.round + 1}",
            str(args.jobs_dir / "supervise_amazon_resume.job"),
        ],
        cwd=args.jobs_dir,
        text=True,
    ).strip()
    return job_id, next_supervisor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--jobs-dir", type=Path, required=True)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    selection = pd.read_parquet(args.selection, columns=["user_id", "user_bucket"])
    selected = {
        str(bucket): set(group.user_id.astype(str))
        for bucket, group in selection.groupby("user_bucket")
    }
    report: dict[str, object] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "round": args.round,
        "target_buckets": len(TARGET_BUCKETS),
        "buckets": {},
    }
    incomplete: list[str] = []
    total_have = total_target = 0
    for bucket in TARGET_BUCKETS:
        expected = selected[bucket]
        actual, invalid = read_ids(args.out_dir / f"shard_{bucket}.jsonl")
        missing = expected - actual
        extra = actual - expected
        total_have += len(actual & expected)
        total_target += len(expected)
        state = "complete" if not missing and not extra and invalid == 0 else "incomplete"
        if state != "complete":
            incomplete.append(bucket)
        report["buckets"][bucket] = {
            "state": state,
            "rows_unique": len(actual),
            "selected": len(expected),
            "missing": len(missing),
            "extra": len(extra),
            "invalid_lines": invalid,
        }
    report.update({
        "complete_buckets": len(TARGET_BUCKETS) - len(incomplete),
        "incomplete_buckets": incomplete,
        "continuation_users_complete": total_have,
        "continuation_users_target": total_target,
        "continuation_users_missing": total_target - total_have,
        "new_users_complete": total_have - SEEDED_PARTIAL_UNIQUE,
        "global_users_complete": HF_EXISTING_UNIQUE + total_have - SEEDED_PARTIAL_UNIQUE,
    })
    args.out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = args.out_dir / "supervisor_progress.json"
    progress_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in (
        "round", "complete_buckets", "continuation_users_complete",
        "continuation_users_missing", "global_users_complete",
    )}, indent=2))

    if not incomplete:
        completion = args.out_dir / "EXTRACTION_COMPLETE.json"
        completion.write_text(json.dumps(report, indent=2) + "\n")
        print(f"AMAZON_EXTRACTION_COMPLETE users={report['global_users_complete']}")
        return
    if args.dry_run:
        print(f"DRY_RUN incomplete_buckets={','.join(incomplete)}")
        return
    if args.round >= args.max_rounds:
        raise SystemExit(
            f"maximum retry rounds reached ({args.max_rounds}); "
            f"still incomplete: {','.join(incomplete)}"
        )
    job_id, supervisor_id = submit_retry(args, incomplete)
    event = {
        "round": args.round,
        "retry_job_id": job_id,
        "next_supervisor_job_id": supervisor_id,
        "buckets": incomplete,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    with (args.out_dir / "supervisor_events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")
    print(
        f"RETRY_SUBMITTED round={args.round} job_id={job_id} "
        f"next_supervisor={supervisor_id} buckets={len(incomplete)}"
    )


if __name__ == "__main__":
    main()
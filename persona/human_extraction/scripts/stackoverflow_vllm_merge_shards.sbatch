#!/bin/bash
#SBATCH --job-name=so-vllm-merge
#SBATCH --account=torch_pr_543_general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%j.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%j.err
#SBATCH --mail-type=FAIL,END
#SBATCH --mail-user=yl6586@nyu.edu

# Validate and merge one completed sharded run without deleting its shard files.
# For one RTX array job:
#   array_job=$(sbatch --parsable stackoverflow_vllm_sharded_rtx6000_bf16_tp1.sbatch)
#   sbatch --dependency=afterok:$array_job \
#     --export=ALL,YEAR=2025,SHARD_COUNT=8,RUN_TAG=qwen36-bf16 \
#     stackoverflow_vllm_merge_shards.sbatch
#
# For mixed RTX/H200 arrays, use --dependency=afterok:<rtx_job>:<h200_job>.

set -euo pipefail

WORKDIR="${WORKDIR:-/scratch/yl6586/MatrAIx}"
SURVEY_ROOT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey"
IMAGE="${IMAGE:-/scratch/yl6586/containers/vllm-v0.19.0.sif}"

YEAR="${YEAR:-2025}"
SHARD_COUNT="${SHARD_COUNT:-8}"
RUN_TAG="${RUN_TAG:-qwen36-bf16}"
MODEL="${MODEL:-Qwen/Qwen3.6-35B-A3B}"

case "$YEAR" in
  2023) SURVEY_REL="2023/results_2023_completeness_60.csv" ;;
  2024) SURVEY_REL="2024/results_2024_completeness_60_attention.csv" ;;
  2025) SURVEY_REL="2025/results_2025_completeness_60.csv" ;;
  *)
    echo "ERROR: YEAR must be one of 2023, 2024, or 2025; got $YEAR" >&2
    exit 2
    ;;
esac

if [[ ! "$SHARD_COUNT" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: SHARD_COUNT must be a positive integer; got $SHARD_COUNT" >&2
  exit 2
fi
if [[ ! "$RUN_TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "ERROR: RUN_TAG may contain only letters, digits, dot, underscore, and hyphen" >&2
  exit 2
fi
if ! command -v flock >/dev/null 2>&1; then
  echo "ERROR: flock is required for merge locking" >&2
  exit 1
fi

SURVEY_CSV="$SURVEY_ROOT/$SURVEY_REL"
RUN_DIR="$SURVEY_ROOT/sharded_runs/$RUN_TAG/year_${YEAR}/shards_${SHARD_COUNT}"
MERGED_OUTPUT="$RUN_DIR/merged.jsonl"
MERGE_LOCK="$RUN_DIR/merged.jsonl.lock"

for required_file in "$IMAGE" "$SURVEY_CSV"; do
  if [[ ! -f "$required_file" ]]; then
    echo "ERROR: Required file not found: $required_file" >&2
    exit 1
  fi
done
if [[ ! -d "$RUN_DIR" ]]; then
  echo "ERROR: Run directory does not exist: $RUN_DIR" >&2
  exit 1
fi

mkdir -p /scratch/yl6586/slurm_logs
cd "$WORKDIR"

exec 9>"$MERGE_LOCK"
if ! flock -n 9; then
  echo "ERROR: another merge is already running for $RUN_DIR" >&2
  exit 75
fi

echo "=== Stack Overflow shard merge ==="
echo "job_id=$SLURM_JOB_ID host=$(hostname)"
echo "year=$YEAR run_tag=$RUN_TAG model=$MODEL shard_count=$SHARD_COUNT"
echo "run_dir=$RUN_DIR"

apptainer exec \
  --bind /scratch:/scratch \
  --pwd "$WORKDIR" \
  "$IMAGE" \
  /usr/bin/python3 - \
  "$SURVEY_CSV" "$RUN_DIR" "$YEAR" "$SHARD_COUNT" "$MODEL" <<'PY'
import csv
import json
import os
import sys
from pathlib import Path

survey_csv = Path(sys.argv[1])
run_dir = Path(sys.argv[2])
year = int(sys.argv[3])
shard_count = int(sys.argv[4])
model = sys.argv[5]

csv.field_size_limit(100_000_000)
with survey_csv.open(encoding="utf-8-sig", newline="") as handle:
    total_rows = sum(1 for _ in csv.DictReader(handle))
if total_rows < 1:
    raise SystemExit(f"Survey contains no data rows: {survey_csv}")
if shard_count > total_rows:
    raise SystemExit(
        f"SHARD_COUNT={shard_count} exceeds survey row count {total_rows}"
    )

merged_path = run_dir / "merged.jsonl"
job_id = os.environ.get("SLURM_JOB_ID", str(os.getpid()))
temp_path = run_dir / f".merged.jsonl.tmp.{job_id}.{os.getpid()}"
if temp_path.exists():
    raise SystemExit(f"Temporary merge output already exists: {temp_path}")

common_provenance = None
written = 0
try:
    with temp_path.open("x", encoding="utf-8", newline="") as merged:
        for shard_id in range(shard_count):
            start = total_rows * shard_id // shard_count
            end = total_rows * (shard_id + 1) // shard_count
            shard_path = run_dir / f"shard_{shard_id:03d}.jsonl"
            if not shard_path.is_file():
                raise ValueError(f"Missing shard output: {shard_path}")

            expected_row = start
            with shard_path.open(encoding="utf-8") as shard:
                for line_number, line in enumerate(shard, 1):
                    if not line.strip():
                        raise ValueError(f"Blank line at {shard_path}:{line_number}")
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"Invalid JSON at {shard_path}:{line_number}: {error}"
                        ) from error

                    required = {
                        "year": year,
                        "model": model,
                        "backend": "vllm",
                        "extractor_version": "stackoverflow_vllm_v2",
                    }
                    for key, value in required.items():
                        if record.get(key) != value:
                            raise ValueError(
                                f"Incompatible {key} at {shard_path}:{line_number}: "
                                f"{record.get(key)!r} != {value!r}"
                            )

                    provenance = (
                        record.get("manifest_version"),
                        record.get("source_catalog_sha256"),
                    )
                    if not all(isinstance(value, str) and value for value in provenance):
                        raise ValueError(
                            f"Missing manifest provenance at {shard_path}:{line_number}"
                        )
                    if common_provenance is None:
                        common_provenance = provenance
                    elif provenance != common_provenance:
                        raise ValueError(
                            f"Incompatible manifest provenance at "
                            f"{shard_path}:{line_number}: {provenance!r} != "
                            f"{common_provenance!r}"
                        )

                    row_index = record.get("row_index")
                    if type(row_index) is not int:
                        raise ValueError(
                            f"Invalid row_index at {shard_path}:{line_number}: "
                            f"{row_index!r}"
                        )
                    if row_index != expected_row:
                        if row_index < expected_row:
                            issue = "duplicate or out-of-order"
                        else:
                            issue = "missing"
                        raise ValueError(
                            f"{issue} row_index in shard {shard_id}: expected "
                            f"{expected_row}, got {row_index} at "
                            f"{shard_path}:{line_number}"
                        )
                    if not start <= row_index < end:
                        raise ValueError(
                            f"Out-of-range row_index {row_index} in shard {shard_id}; "
                            f"expected [{start}, {end})"
                        )

                    merged.write(line if line.endswith("\n") else line + "\n")
                    expected_row += 1
                    written += 1

            if expected_row != end:
                raise ValueError(
                    f"Incomplete shard {shard_id}: expected rows [{start}, {end}), "
                    f"stopped at {expected_row}"
                )

        if written != total_rows:
            raise ValueError(
                f"Merged row count {written} does not match survey row count {total_rows}"
            )
        merged.flush()
        os.fsync(merged.fileno())

    os.replace(temp_path, merged_path)
except Exception:
    temp_path.unlink(missing_ok=True)
    raise

print(
    f"Merged {written} validated rows from {shard_count} shards into "
    f"{merged_path}"
)
print(
    f"manifest_version={common_provenance[0]} "
    f"source_catalog_sha256={common_provenance[1]}"
)
PY

echo "Merge completed: $MERGED_OUTPUT"
echo "merged_rows=$(wc -l < "$MERGED_OUTPUT")"

#!/bin/bash
#SBATCH --job-name=so-vllm-shard-h200
#SBATCH --account=torch_pr_543_general
#SBATCH --comment="preemption=yes;requeue=true"
#SBATCH --gres=gpu:1
#SBATCH --constraint=h200
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --array=0-7%8
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%A_%a.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%A_%a.err
#SBATCH --mail-type=FAIL,END
#SBATCH --mail-user=yl6586@nyu.edu

# H200 companion to stackoverflow_vllm_sharded_rtx6000_bf16_tp1.sbatch.
# Both files use the same shard calculation and output layout, so they may
# contribute disjoint array indices to one run.
#
# Example: submit H200 shards 6-7 alongside RTX shards 0-5:
#   sbatch --array=6-7 --export=ALL,YEAR=2025,SHARD_COUNT=8,RUN_TAG=qwen36-bf16 \
#     stackoverflow_vllm_sharded_h200.sbatch

set -euo pipefail

WORKDIR="${WORKDIR:-/scratch/yl6586/MatrAIx}"
SCRIPT="$WORKDIR/persona/human_extraction/scripts/extract_personas_stackoverflow_vllm_v2.py"
SURVEY_ROOT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey"
IMAGE="${IMAGE:-/scratch/yl6586/containers/vllm-v0.19.0.sif}"

YEAR="${YEAR:-2025}"
SHARD_COUNT="${SHARD_COUNT:-8}"
SHARD_ID="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required; submit this file with sbatch --array}"
RUN_TAG="${RUN_TAG:-qwen36-bf16}"
MODEL="${MODEL:-Qwen/Qwen3.6-35B-A3B}"

case "$YEAR" in
  2023)
    SURVEY_REL="2023/results_2023_completeness_60.csv"
    MAPPING_REL="2023/stackoverflow_column_mapping_2023.csv"
    ;;
  2024)
    SURVEY_REL="2024/results_2024_completeness_60_attention.csv"
    MAPPING_REL="2024/stackoverflow_column_mapping_2024.csv"
    ;;
  2025)
    SURVEY_REL="2025/results_2025_completeness_60.csv"
    MAPPING_REL="2025/stackoverflow_column_mapping_2025.csv"
    ;;
  *)
    echo "ERROR: YEAR must be one of 2023, 2024, or 2025; got $YEAR" >&2
    exit 2
    ;;
esac

if [[ ! "$SHARD_COUNT" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: SHARD_COUNT must be a positive integer; got $SHARD_COUNT" >&2
  exit 2
fi
if [[ ! "$SHARD_ID" =~ ^(0|[1-9][0-9]*)$ ]] || (( SHARD_ID >= SHARD_COUNT )); then
  echo "ERROR: shard ID $SHARD_ID must be in [0, $((SHARD_COUNT - 1))]" >&2
  exit 2
fi
if [[ ! "$RUN_TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "ERROR: RUN_TAG may contain only letters, digits, dot, underscore, and hyphen" >&2
  exit 2
fi

SURVEY_CSV="$SURVEY_ROOT/$SURVEY_REL"
MAPPING_CSV="$SURVEY_ROOT/$MAPPING_REL"
RUN_DIR="$SURVEY_ROOT/sharded_runs/$RUN_TAG/year_${YEAR}/shards_${SHARD_COUNT}"
OUTPUT="$RUN_DIR/shard_$(printf '%03d' "$SHARD_ID").jsonl"
LOCK="$OUTPUT.lock"

export HF_HOME="${HF_HOME:-/scratch/yl6586/.cache/huggingface}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-$HF_HOME/hub}"
export HF_XET_CACHE="${HF_XET_CACHE:-$HF_HOME/xet}"
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-/scratch/yl6586/.cache/vllm}"
export TMPDIR="${TMPDIR:-/scratch/yl6586/.cache/tmp}"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

if [[ -n "${SLURM_TMPDIR:-}" ]]; then
  export APPTAINER_TMPDIR="$SLURM_TMPDIR"
else
  unset APPTAINER_TMPDIR
fi

for required_file in "$IMAGE" "$SCRIPT" "$SURVEY_CSV" "$MAPPING_CSV"; do
  if [[ ! -f "$required_file" ]]; then
    echo "ERROR: Required file not found: $required_file" >&2
    exit 1
  fi
done
if ! command -v flock >/dev/null 2>&1; then
  echo "ERROR: flock is required for per-shard output locking" >&2
  exit 1
fi

mkdir -p \
  "$HF_HOME" \
  "$HF_HUB_CACHE" \
  "$HF_XET_CACHE" \
  "$VLLM_CACHE_ROOT" \
  "$TMPDIR" \
  "$RUN_DIR" \
  /scratch/yl6586/slurm_logs
cd "$WORKDIR"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "ERROR: shard $SHARD_ID is already running; lock is held: $LOCK" >&2
  exit 75
fi

APPTAINER_BASE=(
  exec
  --bind /scratch:/scratch
  --pwd "$WORKDIR"
  "$IMAGE"
)

TOTAL_ROWS="$(
  apptainer "${APPTAINER_BASE[@]}" /usr/bin/python3 - "$SURVEY_CSV" <<'PY'
import csv
import sys

csv.field_size_limit(100_000_000)
with open(sys.argv[1], encoding="utf-8-sig", newline="") as handle:
    print(sum(1 for _ in csv.DictReader(handle)))
PY
)"
if [[ ! "$TOTAL_ROWS" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: failed to determine a positive survey row count; got $TOTAL_ROWS" >&2
  exit 1
fi
if (( SHARD_COUNT > TOTAL_ROWS )); then
  echo "ERROR: SHARD_COUNT=$SHARD_COUNT exceeds TOTAL_ROWS=$TOTAL_ROWS" >&2
  exit 2
fi

START_ROW=$(( TOTAL_ROWS * SHARD_ID / SHARD_COUNT ))
END_ROW=$(( TOTAL_ROWS * (SHARD_ID + 1) / SHARD_COUNT ))
LIMIT=$(( END_ROW - START_ROW ))

echo "=== Stack Overflow sharded H200 production ==="
echo "job_id=$SLURM_JOB_ID array_task=$SHARD_ID host=$(hostname)"
echo "year=$YEAR run_tag=$RUN_TAG model=$MODEL"
echo "total_rows=$TOTAL_ROWS shard_count=$SHARD_COUNT range=[$START_ROW,$END_ROW) limit=$LIMIT"
echo "output=$OUTPUT"
echo "existing_output_rows=$(test -f "$OUTPUT" && wc -l < "$OUTPUT" || echo 0)"
nvidia-smi

apptainer "${APPTAINER_BASE[@]}" /usr/bin/python3 - \
  "$OUTPUT" "$YEAR" "$MODEL" "$START_ROW" "$END_ROW" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
year = int(sys.argv[2])
model = sys.argv[3]
start = int(sys.argv[4])
end = int(sys.argv[5])
if not path.is_file():
    raise SystemExit(0)

seen = set()
with path.open(encoding="utf-8") as handle:
    for line_number, line in enumerate(handle, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid JSON at {path}:{line_number}: {error}")
        expected = {
            "year": year,
            "model": model,
            "backend": "vllm",
            "extractor_version": "stackoverflow_vllm_v2",
        }
        for key, value in expected.items():
            if record.get(key) != value:
                raise SystemExit(
                    f"Incompatible {key} at {path}:{line_number}: "
                    f"{record.get(key)!r} != {value!r}"
                )
        row_index = record.get("row_index")
        if type(row_index) is not int or not start <= row_index < end:
            raise SystemExit(
                f"Out-of-range row_index at {path}:{line_number}: "
                f"{row_index!r} not in [{start}, {end})"
            )
        if row_index in seen:
            raise SystemExit(f"Duplicate row_index {row_index} in {path}")
        seen.add(row_index)
print(f"Validated {len(seen)} existing rows in {path}")
PY

APPTAINER_GPU=(
  exec
  --nv
  --bind /scratch:/scratch
  --pwd "$WORKDIR"
  "$IMAGE"
)

apptainer "${APPTAINER_GPU[@]}" \
  /usr/bin/python3 \
  "$SCRIPT" \
  --year "$YEAR" \
  --survey-root "$SURVEY_ROOT" \
  --execute \
  --model "$MODEL" \
  --start-row "$START_ROW" \
  --limit "$LIMIT" \
  --batch-profiles 16 \
  --max-num-seqs 64 \
  --max-model-len 32768 \
  --max-tokens 8192 \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --quantization none \
  --gpu-memory-utilization 0.90 \
  --download-dir "$HF_HUB_CACHE" \
  --output "$OUTPUT"

echo "Shard completed: shard=$SHARD_ID range=[$START_ROW,$END_ROW) output=$OUTPUT"
echo "final_output_rows=$(wc -l < "$OUTPUT")"

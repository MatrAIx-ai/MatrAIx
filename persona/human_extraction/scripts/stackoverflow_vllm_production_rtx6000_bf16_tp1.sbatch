#!/bin/bash
#SBATCH --job-name=so-vllm-prod-rtx-bf16
#SBATCH --account=torch_pr_543_general
#SBATCH --comment="preemption=yes;requeue=true"
#SBATCH --gres=gpu:1
#SBATCH --constraint=rtx6000
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%j.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%j.err
#SBATCH --mail-type=FAIL,END
#SBATCH --mail-user=yl6586@nyu.edu

set -euo pipefail

WORKDIR=/scratch/yl6586/MatrAIx
SCRIPT="$WORKDIR/persona/human_extraction/scripts/extract_personas_stackoverflow_vllm_v2.py"
SURVEY_ROOT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey"
OUTPUT="$SURVEY_ROOT/extraction_stackoverflow_v2_rtx6000_bf16_tp1_2025.jsonl"
IMAGE=/scratch/yl6586/containers/vllm-v0.19.0.sif

export HF_HOME=/scratch/yl6586/.cache/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_XET_CACHE="$HF_HOME/xet"
export VLLM_CACHE_ROOT=/scratch/yl6586/.cache/vllm
export TMPDIR=/scratch/yl6586/.cache/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

# Avoid inheriting an expired temporary path from the submitting shell.
if [[ -n "${SLURM_TMPDIR:-}" ]]; then
    export APPTAINER_TMPDIR="$SLURM_TMPDIR"
else
    unset APPTAINER_TMPDIR
fi

for required_file in \
  "$IMAGE" \
  "$SCRIPT" \
  "$SURVEY_ROOT/2025/results_2025_completeness_60.csv" \
  "$SURVEY_ROOT/2025/stackoverflow_column_mapping_2025.csv"; do
    if [[ ! -f "$required_file" ]]; then
        echo "ERROR: Required file not found: $required_file" >&2
        exit 1
    fi
done

mkdir -p \
  "$HF_HOME" \
  "$HF_HUB_CACHE" \
  "$HF_XET_CACHE" \
  "$VLLM_CACHE_ROOT" \
  "$TMPDIR" \
  "$(dirname "$OUTPUT")" \
  /scratch/yl6586/slurm_logs
cd "$WORKDIR"

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Image: $IMAGE"
echo "Output: $OUTPUT"
echo "Existing output rows: $(test -f "$OUTPUT" && wc -l < "$OUTPUT" || echo 0)"
nvidia-smi

APPTAINER_ARGS=(
  exec
  --nv
  --bind /scratch:/scratch
  --pwd "$WORKDIR"
  "$IMAGE"
)

echo "Running one-GPU RTX Pro 6000 production preflight..."
apptainer "${APPTAINER_ARGS[@]}" /usr/bin/python3 - <<'PY'
import torch
import vllm

if not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA is not available inside the container; the image CUDA build may "
        "be incompatible with the node driver"
    )

device_count = torch.cuda.device_count()
print(f"torch={torch.__version__}")
print(f"vllm={vllm.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"visible_gpu_count={device_count}")

if device_count != 1:
    raise RuntimeError(f"Expected exactly 1 visible GPU, got {device_count}")

properties = torch.cuda.get_device_properties(0)
name = properties.name
capability = torch.cuda.get_device_capability(0)
memory_gib = properties.total_memory / 1024**3

print(f"gpu_0={name}")
print(f"gpu_0_compute_capability={capability[0]}.{capability[1]}")
print(f"gpu_0_memory_gib={memory_gib:.1f}")

if capability < (12, 0):
    raise RuntimeError(
        f"Expected compute capability 12.0 or newer, got "
        f"{capability[0]}.{capability[1]}"
    )
if memory_gib < 90:
    raise RuntimeError(
        f"Expected about 96 GiB of GPU memory, got {memory_gib:.1f} GiB"
    )
PY

# Each batch makes 45 same-schema chunk-outer calls. Compatible rows already
# present in this RTX-specific output are skipped when the job is resubmitted.
apptainer "${APPTAINER_ARGS[@]}" \
  /usr/bin/python3 \
  "$SCRIPT" \
  --year 2023 \
  --survey-root "$SURVEY_ROOT" \
  --execute \
  --model Qwen/Qwen3.6-35B-A3B \
  --batch-profiles 8 \
  --max-num-seqs 8 \
  --max-model-len 32768 \
  --max-tokens 8192 \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --quantization none \
  --gpu-memory-utilization 0.90 \
  --download-dir "$HF_HUB_CACHE" \
  --output "$OUTPUT"

echo "RTX Pro 6000 BF16 production run completed: $OUTPUT"
echo "Final output rows: $(wc -l < "$OUTPUT")"

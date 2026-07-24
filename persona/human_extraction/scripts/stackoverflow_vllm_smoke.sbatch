#!/bin/bash
#SBATCH --job-name=so-vllm-smoke
#SBATCH --account=torch_pr_543_general
#SBATCH --comment="preemption=yes;requeue=true"
#SBATCH --gres=gpu:1
#SBATCH --constraint=h200
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%j.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%j.err
#SBATCH --mail-type=FAIL,END
#SBATCH --mail-user=yl6586@nyu.edu

set -euo pipefail

WORKDIR=/scratch/yl6586/MatrAIx
SCRIPT="$WORKDIR/persona/human_extraction/scripts/extract_personas_stackoverflow_vllm_v2.py"
OUTPUT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey/smoke_vllm_v2_2025_${SLURM_JOB_ID}.jsonl"

IMAGE=/scratch/yl6586/containers/vllm-v0.19.0.sif

if [[ ! -f "$IMAGE" ]]; then
    echo "ERROR: Apptainer image not found: $IMAGE" >&2
    exit 1
fi

export HF_HOME=/scratch/yl6586/.cache/huggingface
export HF_HUB_CACHE=/scratch/yl6586/.cache/huggingface
export VLLM_CACHE_ROOT=/scratch/yl6586/.cache/vllm
export VLLM_WORKER_MULTIPROC_METHOD=spawn

mkdir -p "$HF_HOME" "$HF_HUB_CACHE" "$VLLM_CACHE_ROOT"
cd "$WORKDIR"

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Image: $IMAGE"
echo "Output: $OUTPUT"
nvidia-smi

# V2 runs all 45 manifest-defined schemas chunk-outer; one respondent bounds this GPU smoke.
apptainer exec \
  --nv \
  --bind /scratch:/scratch \
  --pwd "$WORKDIR" \
  "$IMAGE" \
  /usr/bin/python3 \
  "$SCRIPT" \
  --year 2025 \
  --start-row 0 \
  --limit 1 \
  --execute \
  --batch-profiles 1 \
  --max-num-seqs 64 \
  --tensor-parallel-size 1 \
  --quantization none \
  --gpu-memory-utilization 0.90 \
  --download-dir "$HF_HUB_CACHE" \
  --output "$OUTPUT"

echo "Smoke test completed: $OUTPUT"

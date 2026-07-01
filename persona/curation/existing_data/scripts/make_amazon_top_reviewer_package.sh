#!/usr/bin/env bash
#
# Export Amazon Reviews 2023 histories for a rank slice from the checked-in
# top-10K reviewer queue, then build a worker-facing Amazon collaborator package.
#
# Usage:
#   persona/curation/existing_data/scripts/make_amazon_top_reviewer_package.sh 0:100 alice
#
# Optional environment overrides:
#   TOP_REVIEWER_QUEUE=/path/to/reviewer_ids.md
#   MATRIX_DATA_ROOT=/path/to/local/raw/cache
#   MATRIX_PACKAGE_OUT_ROOT=/path/to/packages
#   MATRIX_DIMENSIONS=/path/to/persona/schema/dimensions.json
#   AMAZON_REVIEWS_REPO_ID=MatrAIx/MatrAIx
#   AMAZON_REVIEWS_ARTIFACT_PREFIX=amazon/modal_artifacts/amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000
#   AMAZON_CATEGORIES=all
#   HF_TOKEN=...
#   REUSE_HISTORIES=1
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${MATRIX_REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../../.." && pwd)}"

RANGE="${1:-}"
WORKER_ID="${2:-worker}"
DIMENSION_SCOPE="${3:-supported}"

if [[ -z "${RANGE}" || ! "${RANGE}" =~ ^[0-9]+:[0-9]+$ ]]; then
  echo "usage: $0 START:END [worker_id] [supported|all]" >&2
  echo "  e.g. $0 0:100 alice" >&2
  exit 2
fi
if [[ "${DIMENSION_SCOPE}" != "supported" && "${DIMENSION_SCOPE}" != "all" ]]; then
  echo "dimension scope must be 'supported' or 'all'" >&2
  exit 2
fi

START="${RANGE%%:*}"
END="${RANGE##*:}"
if (( START >= END )); then
  echo "range start must be less than range end: ${RANGE}" >&2
  exit 2
fi
COUNT=$((END - START))

TOP_REVIEWER_QUEUE="${TOP_REVIEWER_QUEUE:-${REPO_ROOT}/persona/curation/existing_data/samples/amazon_reviews_2023/top_reviewers/amazon_top_10000_rich_persona_reviewer_ids_2018_2023.md}"
DIMENSIONS="${MATRIX_DIMENSIONS:-${REPO_ROOT}/persona/schema/dimensions.json}"
DATA_ROOT="${MATRIX_DATA_ROOT:-${TMPDIR:-/tmp}/matraix_existing_data}"
PACKAGE_OUT_ROOT="${MATRIX_PACKAGE_OUT_ROOT:-${TMPDIR:-/tmp}/matraix_packages}"
HF_REPO_ID="${AMAZON_REVIEWS_REPO_ID:-MatrAIx/MatrAIx}"
HF_ARTIFACT_PREFIX="${AMAZON_REVIEWS_ARTIFACT_PREFIX:-amazon/modal_artifacts/amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000}"
HF_CATEGORIES="${AMAZON_CATEGORIES:-all}"

ASSIGNMENT_ID="AMZ_TOP10K_${START}_${END}"
DATASET_ID="matraix_amazon_reviews_2023_top10k_${START}_${END}"
RUN_DIR="${DATA_ROOT}/amazon_reviews_2023/top_reviewers/${ASSIGNMENT_ID}"
SELECTED_IDS="${RUN_DIR}/reviewer_ids_${START}_${END}.txt"
USER_HISTORIES="${RUN_DIR}/user_histories_${START}_${END}.jsonl"
OUT_DIR="${PACKAGE_OUT_ROOT}/${ASSIGNMENT_ID}_${WORKER_ID}"

if [[ ! -f "${TOP_REVIEWER_QUEUE}" ]]; then
  echo "top reviewer queue not found: ${TOP_REVIEWER_QUEUE}" >&2
  exit 2
fi
if [[ ! -f "${DIMENSIONS}" ]]; then
  echo "persona dimensions not found: ${DIMENSIONS}" >&2
  exit 2
fi

mkdir -p "${RUN_DIR}" "${PACKAGE_OUT_ROOT}"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

echo ">> selecting top-reviewer ranks ${RANGE} from ${TOP_REVIEWER_QUEUE}"
python3 - "${TOP_REVIEWER_QUEUE}" "${START}" "${END}" "${SELECTED_IDS}" <<'PY'
import re
import sys
from pathlib import Path

queue_path = Path(sys.argv[1])
start = int(sys.argv[2])
end = int(sys.argv[3])
out_path = Path(sys.argv[4])

ids = re.findall(r"^\d+\.\s+`([^`]+)`", queue_path.read_text(encoding="utf-8"), re.M)
if end > len(ids):
    raise SystemExit(f"requested end rank {end} exceeds queue size {len(ids)}")
selected = ids[start:end]
if not selected:
    raise SystemExit("selected reviewer slice is empty")
out_path.write_text("\n".join(selected) + "\n", encoding="utf-8")
print(f"wrote {len(selected)} reviewer ids to {out_path}")
PY

if [[ "${REUSE_HISTORIES:-0}" == "1" && -s "${USER_HISTORIES}" ]]; then
  echo ">> reusing existing histories: ${USER_HISTORIES}"
else
  echo ">> exporting Amazon review histories from Hugging Face"
  TOKEN_ARGS=()
  [[ -n "${HF_TOKEN:-}" ]] && TOKEN_ARGS=(--token "${HF_TOKEN}")
  python3 persona/curation/existing_data/scripts/export_hf_amazon_user_histories.py \
    --user-ids "${SELECTED_IDS}" \
    --repo-id "${HF_REPO_ID}" \
    --artifact-prefix "${HF_ARTIFACT_PREFIX}" \
    --categories "${HF_CATEGORIES}" \
    --output "${USER_HISTORIES}" \
    "${TOKEN_ARGS[@]}"
fi

DATASET_SHA256="$(python3 -c 'import hashlib,sys; h=hashlib.sha256(); f=open(sys.argv[1],"rb"); [h.update(c) for c in iter(lambda: f.read(1024*1024), b"")]; print(h.hexdigest())' "${USER_HISTORIES}")"

SCOPE_ARGS=()
[[ "${DIMENSION_SCOPE}" == "all" ]] && SCOPE_ARGS=(--all-dimensions)

echo ">> building worker package ${ASSIGNMENT_ID} for ${WORKER_ID}"
python3 persona/curation/existing_data/scripts/make_package.py \
  --source amazon \
  --user-histories "${USER_HISTORIES}" \
  --dimensions "${DIMENSIONS}" \
  --range "0:${COUNT}" \
  --out-dir "${OUT_DIR}" \
  --assignment-id "${ASSIGNMENT_ID}" \
  --worker-id "${WORKER_ID}" \
  --dataset-id "${DATASET_ID}" \
  --dataset-sha256 "${DATASET_SHA256}" \
  --force \
  "${SCOPE_ARGS[@]}"

echo ""
echo "done. package directory:"
echo "   ${OUT_DIR}"
echo "archive:"
echo "   ${OUT_DIR}.tar.gz"

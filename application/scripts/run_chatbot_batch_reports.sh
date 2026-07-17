#!/usr/bin/env bash
# Run a 6-persona Harbor batch for a synthetic mental-health chatbot task,
# refresh aggregation, and print the Playground Runs URL for PDF export.
#
# Usage (from repo root, on the matching feature branch):
#   cp application/playground/.env.local.example application/playground/.env.local
#   # Anthropic-only (simplest): ANTHROPIC_API_KEY=sk-ant-...
#   # Or Qwen sidecar + Anthropic persona: QWEN_API_KEY=... and ANTHROPIC_API_KEY=...
#   ./application/scripts/run_chatbot_batch_reports.sh anxiety
#   ./application/scripts/run_chatbot_batch_reports.sh depression
#
# Requires: Docker, uv, built Playground frontend (for PDF via Runs UI).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

TASK_KIND="${1:-}"
if [[ "$TASK_KIND" != "anxiety" && "$TASK_KIND" != "depression" ]]; then
  echo "Usage: $0 anxiety|depression" >&2
  exit 1
fi

ENV_FILE="$REPO_ROOT/application/playground/.env.local"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${QWEN_API_KEY:-}" && -n "${DASHSCOPE_API_KEY:-}" ]]; then
  export QWEN_API_KEY="$DASHSCOPE_API_KEY"
fi

# Ignore template placeholder keys so auto-detect picks Anthropic when configured.
if [[ "${OPENAI_API_KEY:-}" == "sk-your-key-here" ]]; then
  unset OPENAI_API_KEY
fi

missing=()
[[ -z "${ANTHROPIC_API_KEY:-}" ]] && missing+=("ANTHROPIC_API_KEY (persona agent)")
has_sidecar_key=false
if [[ -n "${QWEN_API_KEY:-}" || -n "${DASHSCOPE_API_KEY:-}" || -n "${OPENAI_API_KEY:-}" || -n "${ANTHROPIC_API_KEY:-}" ]]; then
  has_sidecar_key=true
fi
if [[ "$has_sidecar_key" == "false" ]]; then
  missing+=("sidecar LLM key: QWEN_API_KEY, DASHSCOPE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")
fi
if ((${#missing[@]})); then
  echo "Missing keys in application/playground/.env.local:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi

if [[ "$TASK_KIND" == "anxiety" ]]; then
  TASK_PATH="application/tasks/chat_synthetic-anxiety-support"
  JOB_NAME="chat-synthetic-anxiety-support-batch-n6"
  SIDEcar_DIR="environment/task-environments/application/chatbot-api-sidecar_anxiety"
  COMPOSE_FILE="standalone-compose.yaml"
  UPSTREAM_ENV="CHATBOT_UPSTREAM_ANXIETY"
  UPSTREAM_URL="http://127.0.0.1:8905"
  export ANXIETY_AGENT_PROVIDER="${ANXIETY_AGENT_PROVIDER:-anthropic}"
  if [[ "${ANXIETY_AGENT_PROVIDER}" == "anthropic" && -z "${ANXIETY_AGENT_MODEL:-}" ]]; then
    export ANXIETY_AGENT_MODEL="claude-sonnet-4-6"
  fi
else
  TASK_PATH="application/tasks/chat_synthetic-depression-support"
  JOB_NAME="chat-synthetic-depression-support-batch-n6"
  SIDEcar_DIR="environment/task-environments/application/chatbot-api-sidecar_depression"
  COMPOSE_FILE="standalone-compose.yaml"
  UPSTREAM_ENV="CHATBOT_UPSTREAM_DEPRESSION"
  UPSTREAM_URL="http://127.0.0.1:8906"
  export DEPRESSION_AGENT_PROVIDER="${DEPRESSION_AGENT_PROVIDER:-anthropic}"
  if [[ "${DEPRESSION_AGENT_PROVIDER}" == "anthropic" && -z "${DEPRESSION_AGENT_MODEL:-}" ]]; then
    export DEPRESSION_AGENT_MODEL="claude-sonnet-4-6"
  fi
fi

if [[ ! -d "$REPO_ROOT/$TASK_PATH" ]]; then
  echo "Task not found: $TASK_PATH (checkout the matching feature branch)" >&2
  exit 1
fi

export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/environment/runtime:${REPO_ROOT}/packages/playground/src:${REPO_ROOT}/application/playground${PYTHONPATH:+:${PYTHONPATH}}"

echo "[1/5] Sampling personas from the task strategy..."
SAMPLE_RESULT="$(
  uv run python - "$TASK_PATH" <<'PY'
import json
import sys
from pathlib import Path

from backend.service.persona_pool_service import PersonaPoolService

task_path = sys.argv[1]
strategy = json.loads((Path(task_path) / "persona_strategy.json").read_text())
result = PersonaPoolService.from_repo(repo_root=Path.cwd()).sample_pool(
    persona_pool=strategy.get("pool") or "persona/datasets/bench-dev-sample",
    sample_size=int(strategy.get("sampleSize") or 6),
    seed=int(strategy.get("seed") or 42),
    sources=strategy.get("sources") or None,
    dimension_filters=strategy.get("dimensionFilters") or None,
    stratify_fields=strategy.get("stratifyFields") or None,
    sample_size_per_value_group=strategy.get("sampleSizePerValueGroup"),
    task_path=task_path,
    auto_ensure_strategy_pool=True,
)
print("{}|{}".format(result["pool"], " ".join(result["personaIds"])))
PY
)"
IFS='|' read -r PERSONA_POOL PERSONA_IDS_RAW <<< "$SAMPLE_RESULT"
read -r -a PERSONA_IDS <<< "$PERSONA_IDS_RAW"
if [[ "${#PERSONA_IDS[@]}" -ne 6 ]]; then
  echo "Expected 6 strategy personas, got ${#PERSONA_IDS[@]}: $PERSONA_IDS_RAW" >&2
  exit 1
fi
echo "Selected strategy personas from $PERSONA_POOL: ${PERSONA_IDS[*]}"

echo "[2/5] Starting sidecar ($SIDEcar_DIR)..."
(
  cd "$REPO_ROOT/$SIDEcar_DIR"
  export QWEN_API_KEY="${QWEN_API_KEY:-}"
  export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-}"
  export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
  export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
  export ANXIETY_AGENT_PROVIDER="${ANXIETY_AGENT_PROVIDER:-}"
  export ANXIETY_AGENT_MODEL="${ANXIETY_AGENT_MODEL:-}"
  export DEPRESSION_AGENT_PROVIDER="${DEPRESSION_AGENT_PROVIDER:-}"
  export DEPRESSION_AGENT_MODEL="${DEPRESSION_AGENT_MODEL:-}"
  docker compose -f "$COMPOSE_FILE" up --build -d
)
for _ in $(seq 1 30); do
  if curl -sf "$UPSTREAM_URL/health" >/dev/null; then
    break
  fi
  sleep 2
done
curl -sf "$UPSTREAM_URL/health" >/dev/null || {
  echo "Sidecar not healthy at $UPSTREAM_URL" >&2
  exit 1
}

echo "[3/5] Generating job YAML (sample-size 6)..."
export "$UPSTREAM_ENV=$UPSTREAM_URL"
export ANTHROPIC_API_KEY
CONFIG="$REPO_ROOT/configs/jobs/application-task-job-recipe/${JOB_NAME}.yaml"
uv run python application/scripts/generate_application_job.py \
  --task "$TASK_PATH" \
  --dataset "$PERSONA_POOL" \
  --execution-mode auto \
  --sample-size 6 \
  --seed 42 \
  --persona-ids "${PERSONA_IDS[@]}" \
  --name "$JOB_NAME" \
  --job-name "$JOB_NAME" \
  --out "$CONFIG"

echo "[4/5] Running Harbor batch (this may take several minutes)..."
echo "Stopping standalone sidecar so Harbor trials can bind ${UPSTREAM_URL}..."
(
  cd "$REPO_ROOT/$SIDEcar_DIR"
  docker compose -f "$COMPOSE_FILE" down || true
)
export MATRIX_CHATBOT_TASK_PATH="$TASK_PATH"
export ANTHROPIC_API_KEY
export "$UPSTREAM_ENV=$UPSTREAM_URL"
JOB_DIR="$REPO_ROOT/jobs/$JOB_NAME"
if [[ -d "$JOB_DIR" ]]; then
  echo "Removing previous job directory: $JOB_DIR"
  rm -rf "$JOB_DIR"
fi
uv run harbor run -c "$CONFIG"

echo "[5/5] Refreshing batch aggregation..."
uv run python application/scripts/report_job.py "$JOB_NAME" --no-llm

echo
echo "Done. Open Playground Runs and export PDF:"
echo "  http://127.0.0.1:8765  →  Runs  →  $JOB_NAME"
echo "  Expand 'Show detailed report', then Download PDF."

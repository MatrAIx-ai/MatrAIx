#!/bin/bash
# Launch the real Ollama sample-collection run (run_real.py), fully
# detached from the calling shell so it survives the terminal closing.
set -euo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TASK_DIR/../../.." && pwd)"

cd "$TASK_DIR"
rm -f output/real_run_results.json output/run_real.log
mkdir -p output

if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  source "$REPO_ROOT/.venv/bin/activate"
else
  echo "No .venv found at $REPO_ROOT/.venv — using system python3." >&2
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "ERROR: ollama CLI not found. Install it and run 'ollama pull llama3.1' first." >&2
  exit 1
fi

if ! ollama list | grep -q "llama3.1"; then
  echo "ERROR: llama3.1 model not found locally. Run 'ollama pull llama3.1' first." >&2
  exit 1
fi

nohup python3 -u run_real.py > output/run_real.log 2>&1 &
disown
echo "Launched, PID: $!"
echo "Log: $TASK_DIR/output/run_real.log"

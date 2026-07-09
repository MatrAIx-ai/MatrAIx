#!/bin/bash
# Orchestrates the full 1000-product Amazon harvest, unattended:
#
#   1. discovery  — best-seller pages -> output/candidates.json
#                   (looped: a rerun retries listing pages lost to blocks)
#   2. harvest    — product pages -> output/harvest.jsonl (checkpointed;
#                   each rerun resumes; reruns separated by a long quiet
#                   pause so a hard block episode can clear)
#   3. assemble   — output/harvest.jsonl -> fixtures/products_1k.json
#
# Every stage is idempotent and resumable, so this script itself can be
# rerun safely if the machine sleeps or the process dies.
#
# Usage:  nohup bash scripts/run_full_harvest.sh > output/harvest_run.log 2>&1 &
set -uo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$TASK_DIR/../../.." && pwd)"
cd "$TASK_DIR"
mkdir -p output

if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  source "$REPO_ROOT/.venv/bin/activate"
fi

TARGET="${TARGET:-1000}"
CANDIDATE_FLOOR="${CANDIDATE_FLOOR:-1200}"
DELAY="${DELAY:-25}"

count_candidates() {
  python3 -c "
import json, pathlib
p = pathlib.Path('output/candidates.json')
print(len(json.loads(p.read_text())['candidates']) if p.exists() else 0)
"
}

count_accepted() {
  [ -f output/harvest.jsonl ] && wc -l < output/harvest.jsonl | tr -d ' ' || echo 0
}

echo "=== stage 1: discovery (floor: $CANDIDATE_FLOOR candidates) ==="
for attempt in 1 2 3; do
  n=$(count_candidates)
  if [ "$n" -ge "$CANDIDATE_FLOOR" ]; then
    break
  fi
  echo "--- discovery attempt $attempt (have $n) ---"
  python3 -u scripts/discover_products.py --out output/candidates.json --delay "$DELAY"
  sleep 120
done
echo "discovery done: $(count_candidates) candidates"

echo "=== stage 2: harvest (target: $TARGET) ==="
for attempt in 1 2 3 4 5 6; do
  n=$(count_accepted)
  if [ "$n" -ge "$TARGET" ]; then
    break
  fi
  echo "--- harvest attempt $attempt (have $n/$TARGET) ---"
  python3 -u scripts/harvest.py \
    --candidates output/candidates.json \
    --out output/harvest \
    --target "$TARGET" \
    --delay "$DELAY"
  n=$(count_accepted)
  if [ "$n" -lt "$TARGET" ]; then
    echo "harvest exited at $n/$TARGET — quiet pause 15 min before resume"
    sleep 900
  fi
done

echo "=== stage 3: assemble ==="
python3 scripts/assemble_dataset.py \
  --harvest output/harvest.jsonl \
  --out fixtures/products_1k.json

echo "=== full harvest run complete: $(count_accepted) accepted ==="

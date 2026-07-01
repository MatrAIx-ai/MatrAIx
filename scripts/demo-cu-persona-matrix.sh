#!/usr/bin/env bash
# Run macOS + iOS notification-preferences demos with two personas each.
# Results land in separate jobs/ dirs (one job_name per config).
#
# Requires:
#   USE_COMPUTER_API_KEY, USE_COMPUTER_RESERVATION_ID, ANTHROPIC_API_KEY
#
# Usage:
#   ./scripts/demo-cu-persona-matrix.sh
#   ./scripts/demo-cu-persona-matrix.sh macos   # only macOS pair
#   ./scripts/demo-cu-persona-matrix.sh ios     # only iOS pair

set -euo pipefail
cd "$(dirname "$0")/.."

for v in USE_COMPUTER_API_KEY USE_COMPUTER_RESERVATION_ID ANTHROPIC_API_KEY; do
  if [[ -z "${!v:-}" ]]; then
    echo "Missing $v" >&2
    exit 1
  fi
done

FILTER="${1:-all}"
LOG="jobs/demo-cu-persona-matrix.log"
mkdir -p jobs

run_job() {
  local cfg="$1"
  local name="${cfg%.yaml}"
  echo "=== $(date -Iseconds) $name ===" | tee -a "$LOG"
  rm -rf "jobs/$name"
  uv run harbor run -c "configs/jobs/example-job-recipe/$cfg" 2>&1 | tee -a "$LOG"
}

MACOS=(
  appSim-demo-cu-macos-p0042.yaml
  appSim-demo-cu-macos-p1206.yaml
)
IOS=(
  appSim-demo-cu-ios-p0042.yaml
  appSim-demo-cu-ios-p1206.yaml
)

case "$FILTER" in
  all)
    for c in "${MACOS[@]}" "${IOS[@]}"; do run_job "$c"; done
    ;;
  macos)
    for c in "${MACOS[@]}"; do run_job "$c"; done
    ;;
  ios)
    for c in "${IOS[@]}"; do run_job "$c"; done
    ;;
  *)
    echo "Unknown filter: $FILTER (use all|macos|ios)" >&2
    exit 1
    ;;
esac

echo "Done. Artifacts under jobs/appSim-demo-cu-*/ — log: $LOG"

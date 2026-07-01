#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/personabench-macos-notification-preferences

cat > /tmp/personabench-macos-notification-preferences/decision.json <<'EOF'
{
  "keep_notifications_on": true,
  "app_reviewed": "Mail",
  "reason": "I want delivery updates for orders but prefer banner style over full-screen alerts."
}
EOF

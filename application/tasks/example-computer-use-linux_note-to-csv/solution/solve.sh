#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/os-app-linux-note-to-csv

cat > /tmp/os-app-linux-note-to-csv/cleaned_list.csv <<'EOF'
item,quantity,priority
oat milk,2,urgent
batteries,4,normal
trash bags,1,low
EOF

cat > /tmp/os-app-linux-note-to-csv/submission.json <<'EOF'
{
  "output_file": "/tmp/os-app-linux-note-to-csv/cleaned_list.csv",
  "rows_written": 3,
  "format": "csv",
  "reason": "CSV keeps the shopping note compact and easy to sort later in a spreadsheet."
}
EOF

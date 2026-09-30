#!/bin/bash
set -euo pipefail
ABLATION_DIR="$(cd "$(dirname "$0")" && pwd)"
REPOSITORY_DIR="$(cd "$ABLATION_DIR/../../.." && pwd)"
PYTHON="${ABLATION_PYTHON:-python3}"
"$PYTHON" -u "$ABLATION_DIR/scripts/run_ablation.py" --config "$ABLATION_DIR/configs/e1_mac.json" --root "$REPOSITORY_DIR" "$@"
if [ -f "$ABLATION_DIR/scripts/analyze_ablation.py" ]; then
  "$PYTHON" "$ABLATION_DIR/scripts/analyze_ablation.py"
fi

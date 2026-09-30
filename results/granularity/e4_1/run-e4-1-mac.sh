#!/bin/bash
set -euo pipefail
E4_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec "${ABLATION_PYTHON:-python3}" -B "$E4_DIR/scripts/run_e4_1.py" "$@"

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ "${1:-portable}" == portable && "$#" -le 1 ]] || {
  printf 'Usage: ./reproduce.sh [portable]\n' >&2
  exit 2
}
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -B tools/verify_release.py
"$PYTHON_BIN" -B tools/reproduce_tables.py
mkdir -p work
RUN_DIR=$(mktemp -d "$PWD/work/portable-XXXXXXXX")
"$PYTHON_BIN" -B package/reproduce_latest.py all --quick --out "$RUN_DIR/latest"
"$PYTHON_BIN" -B package/reproduce_basis.py all --quick --out "$RUN_DIR/basis"
printf 'Portable checks completed: %s\n' "$RUN_DIR"

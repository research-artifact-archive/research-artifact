#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
mode="${1:-portable}"
exec python3 -I -S -B tools/verify.py "$mode"

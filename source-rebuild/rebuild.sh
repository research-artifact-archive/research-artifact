#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -z "${JAVA_HOME:-}" ]; then
    echo "JAVA_HOME must point to JDK 17." >&2
    exit 2
fi
exec python3 "$SCRIPT_DIR/rebuild.py" --java-home "$JAVA_HOME" "$@"

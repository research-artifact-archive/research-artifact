#!/bin/bash
# Start only after the already-running E2 process exits; the E1 runner also locks.
set -euo pipefail
ABLATION_DIR="$(cd "$(dirname "$0")" && pwd)"
E2_PID="${1:?Usage: run-e1-after-e2.sh E2_RUNNER_PID}"
while kill -0 "$E2_PID" 2>/dev/null; do
  E2_COMMAND="$(ps -p "$E2_PID" -o command= || true)"
  case "$E2_COMMAND" in
    *run_ablation.py*e2_mac.json*) sleep 10 ;;
    *) echo "PID no longer identifies E2; continuing to terminal-state check"; break ;;
  esac
done
"${ABLATION_PYTHON:-python3}" - "$ABLATION_DIR" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'scripts'))
from ablation_common import read_json, read_trial, planned_jobs
config = read_json(root / 'configs/e2_mac.json')
pending = []
for job in planned_jobs(config):
    trial = read_trial(root / 'raw/e2_mac/pass1_1200s/runs' / job['job_id'] / 'meta.json')
    if trial['status'] in {'NOT_RUN', 'RUNNING', 'INCOMPLETE'}:
        pending.append(job['job_id'])
if pending:
    raise SystemExit('E2 first pass is incomplete; E1 not started: ' + ', '.join(pending))
print('E2 process exited and all 27 first attempts are terminal. Starting separate E1 CLI smoke.', flush=True)
PY
"${ABLATION_PYTHON:-python3}" "$ABLATION_DIR/scripts/smoke_e1.py"
exec bash "$ABLATION_DIR/run-e1-mac.sh"

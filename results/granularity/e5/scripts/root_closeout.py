#!/usr/bin/env python3
"""Finish reporting after the frozen experiment and final tables have terminated."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

E5 = Path(__file__).resolve().parents[1]


def main():
    if not (E5 / 'raw/runner_finished.json').exists() or not (E5 / 'build/final_tables_ready.json').exists():
        print(json.dumps({'status': 'WAITING_FOR_FINAL_TABLES'}))
        return
    receipt = E5 / 'build/root_closeout.json'
    if receipt.exists():
        print(receipt.read_text())
        return
    with (E5 / 'build/final_independent_review.log').open('x') as log:
        checked = subprocess.run([sys.executable, '-B', str(E5 / 'build/check_e5_independent.py'), '--final'],
                                 stdout=log, stderr=subprocess.STDOUT)
    audit_file = E5 / 'build/final_independent_review.json'
    audit = json.loads(audit_file.read_text()) if audit_file.exists() else {}
    result = {'at': datetime.now().astimezone().isoformat(), 'independent_returncode': checked.returncode,
              'independent_status': audit.get('status', 'MISSING')}
    if checked.returncode or audit.get('status') != 'PASS':
        result['status'] = 'REVIEW_REQUIRED'
    else:
        with (E5 / 'build/write_handoff.log').open('x') as log:
            written = subprocess.run([sys.executable, '-B', str(E5 / 'scripts/write_handoff.py')],
                                     stdout=log, stderr=subprocess.STDOUT)
        result['handoff_returncode'] = written.returncode
        result['status'] = 'HANDOFF_WRITTEN' if written.returncode == 0 else 'REVIEW_REQUIRED'
    with receipt.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

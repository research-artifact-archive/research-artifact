#!/usr/bin/env python3
"""Wait for the fixed runner and freshly collect; never launches Java."""
import datetime, hashlib, json, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
assert not (HERE/'build/tables_generated.json').exists()
while not (HERE/'raw/runner_finished.json').exists():
    time.sleep(10)
results=[]
for script in ['analyze.py','write_tables.py']:
    result=subprocess.run([sys.executable,str(HERE/script)],capture_output=True,text=True)
    target=HERE/'build'/('final_'+script.replace('.py','')+'.log')
    with target.open('x') as stream:stream.write(result.stdout+result.stderr)
    results.append(dict(script=script,exit_code=result.returncode))
    if result.returncode:break
audit=json.loads((HERE/'validation/raw_table_audit.json').read_text()) if (HERE/'validation/raw_table_audit.json').exists() else {}
report=dict(status='PASS' if all(r['exit_code']==0 for r in results) and audit.get('status')=='PASS' and audit.get('terminal') else 'FAIL',
    at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),steps=results,
    statuses=audit.get('statuses',{}),native_latex='PENDING: agent must use built-in compiler',
    scope='Fresh derived tables after runner termination; no added trial and no Java invocation.')
with (HERE/'build/tables_generated.json').open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(report),flush=True)

#!/usr/bin/env python3
"""Wait for the fixed campaign, then run its already-authorized proof export once."""
import datetime as dt,fcntl,json,subprocess,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent;V=P/'v2';E6=P.parent
while not (V/'raw/runner_finished.json').exists():
 if dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))>=dt.datetime.fromisoformat('2026-09-29T18:26:00+09:00'):raise RuntimeError('Measurement series not finished in proof-export window')
 time.sleep(5)
# The marker is written immediately before the campaign returns. Observe lock release.
while True:
 with (E6/'tools/jvm.lock').open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);break
  except BlockingIOError:pass
 time.sleep(1)
results=[]
for name,command in [('validation_export',[sys.executable,'-B','-u',str(P/'validation_export/run_export.py')]),('fresh_analyze',[sys.executable,'-B',str(P/'analyze_pc2.py')])]:
 with (V/'build'/('final_'+name+'.log')).open('x') as log:
  result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 results.append({'step':name,'exit_code':result.returncode})
with (V/'build/export_and_tables_ready.json').open('x') as f:json.dump({'at':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),'steps':results},f,indent=2);f.write('\n')
print(results,flush=True)

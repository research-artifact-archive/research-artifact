#!/usr/bin/env python3
"""One-shot continuation of the preregistered E6 serial experiment queue."""
import datetime as dt,fcntl,hashlib,json,subprocess,sys,time
from pathlib import Path
E6=Path(__file__).resolve().parents[1];OUT=E6/'integration/remaining_queue';JST=dt.timezone(dt.timedelta(hours=9))
CUTOFF=dt.datetime.fromisoformat('2026-09-30T09:39:00+09:00')
FAMILIES=[('rolling_scale/v1','b08475469555ba6a59418d02dc8ecdc0ee5c0d870689abebf3648f8c4d30eb97'),('canary_controls/v1','a2dbc8846933a5ef1af97f0d4ba439343a29409b82c15fa1ea41713cc10dbf09')]
def now():return dt.datetime.now(JST)
def save(name,data):
 with (OUT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def unlocked():
 with (E6/'tools/jvm.lock').open('a+') as f:
  try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return False
  fcntl.flock(f.fileno(),fcntl.LOCK_UN);return True

def main():
 OUT.mkdir(parents=True,exist_ok=False)
 save('invocation.json',dict(started_at=now().isoformat(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),schedule=FAMILIES,wait_for='threads/v1/raw/runner_finished.json',scope='One-shot fixed queue; no retries, input edits, timing replacement or manuscript writes.'))
 while not (E6/'threads/v1/raw/runner_finished.json').exists() or not unlocked():
  if now()>=CUTOFF:
   save('finished.json',dict(status='NOT_RUN_DEADLINE',finished_at=now().isoformat()));return
  time.sleep(3)
 results=[]
 for family,expected in FAMILIES:
  if now()>=CUTOFF:
   results.append(dict(family=family,status='NOT_RUN_DEADLINE'));continue
  actual=hashlib.sha256((E6/family/'build/frozen_manifest.json').read_bytes()).hexdigest()
  assert actual==expected,(family,'manifest changed')
  phases=[];okay=True
  for phase in ['audit','preflight','run','analyze','audit']:
   if phase in ['preflight','run'] and now()>=CUTOFF:
    phases.append(dict(phase=phase,status='NOT_RUN_DEADLINE'));okay=False;break
   index=len(phases);label=family.replace('/','_')+'_'+str(index)+'_'+phase
   command=[sys.executable,'-B',str(E6/'tools/run_family.py'),str(E6/family),phase]
   started=now().isoformat()
   with (OUT/(label+'.log')).open('x') as f:code=subprocess.call(command,cwd=E6,stdout=f,stderr=subprocess.STDOUT)
   row=dict(phase=phase,started_at=started,finished_at=now().isoformat(),exit_code=code,log=label+'.log');phases.append(row);save(label+'.json',row)
   if code:okay=False;break
  results.append(dict(family=family,status='PHASES_COMPLETE' if okay else 'PHASE_FAILED_OR_DEADLINE',phases=phases))
 save('finished.json',dict(status='READY_FOR_ROOT_REVIEW',finished_at=now().isoformat(),results=results))
 print(json.dumps(dict(status='READY_FOR_ROOT_REVIEW',families=[r['family'] for r in results])),flush=True)
if __name__=='__main__':main()

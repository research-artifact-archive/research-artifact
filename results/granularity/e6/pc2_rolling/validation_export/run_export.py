#!/usr/bin/env python3
"""Validation replay only. Never replaces main-series values or retries TO cells."""
import datetime as dt,fcntl,hashlib,json,os,signal,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;PC=HERE.parent;V=PC/'v2';E6=PC.parent
DEADLINE=dt.datetime.fromisoformat('2026-09-29T18:29:00+09:00')
def now():return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def main():
 assert (V/'raw/runner_finished.json').exists(),'Measurement series must finish before validation replay'
 frozen=read(HERE/'frozen_manifest.json')
 for path,h in frozen['files'].items():assert sha(HERE/path)==h,path
 measurement=read(V/'build/frozen_manifest.json')
 for path,h in measurement['files'].items():assert sha(PC/path)==h,path
 lock=(E6/'tools/jvm.lock').open('a+');fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 checks=[]
 for name in measurement['schedule']:
  original=V/'raw'/name
  if not (original/'completion.json').exists():checks.append({'job_id':name,'status':'SKIP','reason':'Not completed'});continue
  completed=read(original/'completion.json')
  if completed['timed_out'] or completed['exit_code'] not in [0,6]:checks.append({'job_id':name,'status':'SKIP','reason':'TO/incomplete/error cells are not retried'});continue
  if (DEADLINE-now()).total_seconds()<190:checks.append({'job_id':name,'status':'SKIP','reason':'Insufficient time for 180 s replay before attempt deadline'});continue
  out=V/'validation/export'/name;out.mkdir(parents=True,exist_ok=False);inv=read(original/'invocation.json');command=inv['command'].copy()
  assert sha(Path(command[command.index('-cp')+1].split(os.pathsep)[-1]))==inv['jar_sha256']
  command[command.index('-cp')+1]=str(HERE/'classes')+os.pathsep+command[command.index('-cp')+1].split(os.pathsep)[-1]
  command[command.index('ltsa.updatingControllers.cli.Pc2DiagnosticRunner')]='ltsa.updatingControllers.cli.Pc2CertificateExportRunner'
  for option,file in [('--output','output.txt'),('--transitions','transitions.txt')]:command[command.index(option)+1]=str(out/file)
  k=command.index('--diagnostic-output');command[k]='--certificate-output';command[k+1]=str(out/'certificate.json')
  save(out/'invocation.json',{'at':now().isoformat(),'purpose':'validation-only replay, excluded from performance/comparison trials','original_invocation_sha256':sha(original/'invocation.json'),'original_completion_sha256':sha(original/'completion.json'),'command':command,'input_sha256':inv['input_sha256'],'jar_sha256':inv['jar_sha256'],'export_manifest_sha256':sha(HERE/'frozen_manifest.json'),'timeout_seconds':180})
  begin=time.monotonic();timeout=False
  with (out/'stdout.log').open('x') as stdout,(out/'stderr.log').open('x') as stderr:
   p=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
   try:code=p.wait(timeout=180)
   except subprocess.TimeoutExpired:
    timeout=True;os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    code=p.returncode
  save(out/'completion.json',{'at':now().isoformat(),'purpose':'validation diagnostics only; wall time is not a performance datum','exit_code':code,'timed_out':timeout,'diagnostic_wall_seconds':time.monotonic()-begin,'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
  issues=[]
  if timeout or code!=completed['exit_code'] or not (out/'certificate.json').exists():issues.append('Replay incomplete or exit differs')
  else:
   actual=read(out/'certificate.json');expected=read(original/'certificate_summary.json')
   for key in ['decision','states_discovered','successor_queries','materialized_transitions','worst_completion_rank','losing_region_states']:
    if actual.get(key)!=expected.get(key):issues.append(key+' differs from original completed measurement')
   if len(actual['states'])!=expected['certificate_states']:issues.append('Certificate size differs')
   if actual['decision']=='WIN':
    ids={q['id']:q for q in actual['states']}
    if any(not s['safe'] or s['physical_operational_arms']<1 for s in actual['states']):issues.append('WIN certificate physical availability/safety fails')
    if any(ids[a]['rank']<=ids[b]['rank'] for a,event,b in actual['strategy_edges']):issues.append('Rank edge fails')
   if actual['decision']=='LOSS' and len(actual['states'])!=actual['losing_region_states']:issues.append('LOSS size mismatch')
  result={'job_id':name,'status':'PASS' if not issues else 'INCONCLUSIVE','issues':issues,'certificate_file':str((out/'certificate.json').relative_to(PC)) if (out/'certificate.json').exists() else None};save(out/'comparison.json',result);checks.append(result);print(result,flush=True)
 save(V/'validation/export/summary.json',{'purpose':'Validation-only exports, not additional measured trials','at':now().isoformat(),'checks':checks})
 print('EXPORT_FINISHED',flush=True)
if __name__=='__main__':main()

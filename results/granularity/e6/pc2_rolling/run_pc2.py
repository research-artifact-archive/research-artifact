#!/usr/bin/env python3
import argparse,datetime as dt,fcntl,hashlib,json,os,signal,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;E6=HERE.parent
JAR=E6.parents[1]/'ablation_20260928/jars/e1.jar';JARSHA='ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
JAVA='/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home/bin/java'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def now():return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['endpoints','series']);ap.add_argument('--version',default='v2');a=ap.parse_args();v=HERE/a.version
 source=v/'inputs/ProductionCell_Arms2_Calibration.lts';assert sha(JAR)==JARSHA
 jobs=([('old_endpoint','C_DRILL_POLISH_CLEAN','none','otf'),('new_endpoint','C_CLEAN_PAINT_DRILL_CAL','none','otf'),('old_new_plant','PC2_NEW_ORIGINAL_1','none','otf'),('cal_new_plant','PC2_NEW_CALIBRATION_1','none','otf')] if a.phase=='endpoints' else [('lazy_none','UPDATE_CONTROLLER_PC2_CAL','none','otf'),('lazy_transfers','UPDATE_CONTROLLER_PC2_CAL','transfers','otf'),('direct_full_none','UPDATE_CONTROLLER_PC2_CAL','none','direct_full')])
 timeout=120 if a.phase=='endpoints' else 1200
 if a.phase=='series':
  manifest=json.loads((v/'build/frozen_manifest.json').read_text())
  for rel,expected in manifest['files'].items():assert sha(HERE/rel)==expected,rel
  assert manifest['jar_sha256']==sha(JAR)

 lock=(E6/'tools/jvm.lock').open('a+');fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 for name,target,merge,solver in jobs:
  out=v/('preflight' if a.phase=='endpoints' else 'raw')/name;out.mkdir(parents=True,exist_ok=False)
  if a.phase=='series' and dt.datetime.fromisoformat(now())>=dt.datetime.fromisoformat('2026-09-29T18:08:00+09:00'):
   save(out/'not_run.json',{'at':now(),'status':'NOT_RUN','reason':'PC2 18:29 attempt deadline; 1200s whole-JVM cells start before 18:08 only.'});continue
  command=[JAVA,'-Xmx32g','-Djava.awt.headless=true','-Dmtsa.revised.otf.solver='+solver,'-Dmtsa.otf.contractMerge='+merge,'-Dmtsa.otf.lazyControllableBuckets='+('true' if solver=='otf' else 'false'),'-Dmtsa.otf.guidedStateLimit=0','-Dmtsa.otf.guidedQueryLimit=0','-Dmtsa.otf.controllableActionOrder=endpoint_guided','-cp',str(JAR),'ltsa.updatingControllers.cli.SingleCompositionRunner','--lts',str(source),'--target',target,'--output',str(out/'output.txt'),'--transitions',str(out/'transitions.txt'),'--transition-output','full' if a.phase=='endpoints' else 'summary']
  if a.phase=='series':command[command.index(str(JAR))]=str(HERE/'build/classes')+os.pathsep+str(JAR);command[command.index('ltsa.updatingControllers.cli.SingleCompositionRunner')]='ltsa.updatingControllers.cli.Pc2DiagnosticRunner';command+=['--diagnostic-output',str(out/'certificate_summary.json')]
  save(out/'invocation.json',dict(at=now(),command=command,input_sha256=sha(source),jar_sha256=sha(JAR),heap='32g',timeout_seconds=timeout,timeout_scope='whole JVM',role='design endpoint preflight' if a.phase=='endpoints' else 'one-shot final campaign',merge=merge,solver=solver))
  started=time.monotonic();timedout=False
  with (out/'stdout.log').open('x') as stdout,(out/'stderr.log').open('x') as stderr:
   p=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
   try:code=p.wait(timeout=timeout)
   except subprocess.TimeoutExpired:
    timedout=True;os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    code=p.returncode
  save(out/'completion.json',dict(at=now(),exit_code=code,timed_out=timedout,wall_seconds=time.monotonic()-started,files={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
  print(name,code,'TO' if timedout else '',flush=True)
 save(v/('preflight' if a.phase=='endpoints' else 'raw')/'runner_finished.json',{'at':now(),'phase':a.phase,'jobs':[j[0] for j in jobs]})
 print('FINISHED',flush=True)
if __name__=='__main__':main()

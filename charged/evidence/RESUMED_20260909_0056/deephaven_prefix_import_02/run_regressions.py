from pathlib import Path
import datetime, hashlib, json, os, shutil, signal, subprocess, time, xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent
O=P/'regressions01';O.mkdir()
old=json.loads((P.parent/'deephaven_policy_01/regressions01/PLAN.json').read_text())
a=old['argv']+['--tests','io.deephaven.engine.table.impl.TestRetryMaximumKeyRepair']
co=Path(old['cwd']);started=time.time()
r={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':a,'cwd':str(co),'timeout_seconds':180,'expected_test_count':10,'purpose':'Four upstream regressions and six preserved MAX-key repair controls after strict hooks; no new deployment claim','source_hashes':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ('ConstructSnapshot.java','HierarchicalTableImpl.java','RetryStudyHooks.java')}}
(O/'PLAN.json').write_text(json.dumps(r,indent=2)+'\n')
with (O/'BUILD.log').open('xb') as log:
    child=subprocess.Popen(a,cwd=co,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    (O/'PROCESS.json').write_text(json.dumps({'pid':child.pid,'pgid':child.pid})+'\n')
    try:r['exit_code']=child.wait(timeout=180)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        r['timeout']=True
r['tests']=[]
for task,cl in [('test','io.deephaven.engine.table.impl.remote.TestConstructSnapshot'),('testOutOfBand','io.deephaven.engine.table.impl.TestTreeTable'),('testOutOfBand','io.deephaven.engine.table.impl.TestRetryMaximumKeyRepair')]:
    f=co/'engine/table/build/test-results'/task/('TEST-'+cl+'.xml')
    if f.exists() and f.stat().st_mtime>=started:
        shutil.copyfile(f,O/(cl+'.xml'));x=ET.parse(f).getroot();r['tests'].append({'class':cl,**{k:x.get(k) for k in ('tests','failures','errors','skipped')},'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
r['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
r['status']='SUCCESS' if r.get('exit_code')==0 and sum(int(x['tests']) for x in r['tests'])==10 and all(int(x['failures'])+int(x['errors'])+int(x['skipped'])==0 for x in r['tests']) else 'FAILURE'
(O/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

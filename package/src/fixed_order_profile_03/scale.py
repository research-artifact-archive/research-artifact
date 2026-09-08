from pathlib import Path
import collections,datetime,hashlib,importlib.util,json,os,signal,shutil,subprocess,sys,time,types
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=ROOT.parent;OLD=S/'fixed_order_profile_02/scale01'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
def prepare():
    out=ROOT/'scale01';out.mkdir();shutil.copytree(OLD/'inputs',out/'inputs');shutil.copy2(OLD/'INPUTS.json',out/'INPUTS.json')
    files=[ROOT/'SCALE_PLAN.md',ROOT/'PROOF_DRAFT.md',ROOT/'checker.py',ROOT/'scale.py',ROOT/'scale_worker.py',
        S/'fixed_order_profile_02/persistent.py',S/'fixed_order_profile_02/checker.py',S/'sweep_certificate_02/certificate.py',
        S/'final_evaluation_dag_01/structure.py',OLD/'RAW.jsonl',OLD/'MANIFEST.json',out/'INPUTS.json']
    files+=sorted((out/'inputs').glob('*.json'))
    save(out/'MANIFEST.json',dict(utc=now(),inputs=60,units=60,seconds_per_unit=5,rss_bytes=1073741824,poll_seconds=.05,campaign_seconds=330,
         python=sys.executable,python_sha256=sha(sys.executable),python_version=sys.version,rss_monitor='/bin/ps',rss_monitor_sha256=sha('/bin/ps'),
         old_method_reruns=0,constructor_changed=False,checker_changed=True,
         files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in files]))
    print('Frozen60sameinputs,newcheckeronly;old120outcomespreserved',flush=True)
def run():
    assert __debug__;out=ROOT/'scale01';m=json.loads((out/'MANIFEST.json').read_text())
    for f in m['files']:assert sha(S/f['path'])==f['sha256']
    assert sha(sys.executable)==m['python_sha256'];(out/'units').mkdir()
    previous=collections.defaultdict(dict)
    for r in map(json.loads,(OLD/'RAW.jsonl').read_text().splitlines()):previous[r['input_id']][r['method']]=r
    inputs=json.loads((out/'INPUTS.json').read_text());counts=collections.Counter();start=time.monotonic()
    save(out/'START.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(out/'MANIFEST.json')))
    with (out/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(inputs):
            unit=out/'units'/u['id'];unit.mkdir();row=dict(id=u['id'],method='persistent_shared_check',historical_statuses={k:r['status'] for k,r in previous[u['id']].items()})
            if time.monotonic()-start>=330 or now()>='2026-09-08T01:50:00+00:00':row['status']='NOT_RUN'
            else:
                argv=[sys.executable,str(ROOT/'scale_worker.py'),str(out/u['file']),str(unit)]
                save(unit/'COMMAND.json',dict(argv=argv,utc=now(),seconds=5,rss_bytes=1073741824))
                before=time.monotonic();peak=0;reason=None
                with (unit/'stdout.txt').open('wb') as stdout,(unit/'stderr.txt').open('wb') as stderr:
                    p=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
                    while p.poll() is None:
                        sample=subprocess.run(['/bin/ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True,timeout=2)
                        try:peak=max(peak,int(sample.stdout.strip())*1024)
                        except ValueError:pass
                        if time.monotonic()-before>5 or peak>1073741824 or time.monotonic()-start>330 or now()>='2026-09-08T01:50:00+00:00':
                            reason='RSS_LIMIT' if peak>1073741824 else 'WALL_LIMIT'
                            try:os.killpg(p.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                            break
                        time.sleep(.05)
                    code=p.wait()
                row.update(cold_seconds=time.monotonic()-before,peak_sampled_rss=peak,exit=code,limit_reason=reason)
                if reason:row['status']='TIMEOUT'
                elif code==0 and (unit/'RESULT.json').exists():row.update(json.loads((unit/'RESULT.json').read_text()))
                else:
                    stderr=(unit/'stderr.txt').read_text(errors='replace');row['status']='FAILURE' if 'AssertionError' in stderr else 'INVALID';row['error']=stderr[-4000:]
                if (unit/'CONSTRUCTION.json').exists():
                    receipt=json.loads((unit/'CONSTRUCTION.json').read_text());row['construction_before_check']=receipt
                    expected=previous[u['id']]['persistent']['construction_before_check']['artifact_sha256']
                    row['same_artifact_as_previous']=receipt['artifact_sha256']==expected
                    if not row['same_artifact_as_previous']:row.update(status='FAILURE',reason='changed_unchanged_constructor_artifact')
                if row['status']=='SUCCESS':
                    for method,old in previous[u['id']].items():
                        if old['status']=='SUCCESS' and old['values']!=row['values']:row.update(status='FAILURE',reason='historical_value_disagreement',disagreeing_method=method)
            counts[row['status']]+=1;save(unit/'TERMINAL.json',row);raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            if (index+1)%5==0:print(json.dumps(dict(inputs=index+1,counts=dict(counts))),flush=True)
    result=dict(utc=now(),units=60,counts={s:counts[s] for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},seconds=time.monotonic()-start,
        raw_sha256=sha(out/'RAW.jsonl'),old_raw_sha256=sha(OLD/'RAW.jsonl'),old_method_reruns=0)
    save(out/'SUMMARY.json',result);print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()

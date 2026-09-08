from pathlib import Path
import collections
import datetime
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent;S=ROOT.parent;OUT=ROOT/'run01'
OLD=S/'budget_oracle_01/benchmark01'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,data):
    with p.open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')

def prepare():
    OUT.mkdir();(OUT/'inputs').mkdir()
    units=load(OLD/'INPUTS.json');assert len(units)==48
    (OUT/'INPUTS.json').write_bytes((OLD/'INPUTS.json').read_bytes())
    for u in units:(OUT/'inputs'/(u['id']+'.json')).write_bytes((OLD/'inputs'/(u['id']+'.json')).read_bytes())
    files=[ROOT/p for p in ['PLAN.md','study.py','worker.py']]
    files += [S/p for p in ['dependency_hybrid_01/hybrid.py','dependency_hybrid_check_02/check.py',
        'dependency_curves_01/curves.py','sweep_certificate_02/certificate.py','final_evaluation_dag_01/structure.py']]
    files += [OLD/'RAW.jsonl',OLD/'MANIFEST.json',OUT/'INPUTS.json']+sorted((OUT/'inputs').glob('*.json'))
    save(OUT/'MANIFEST.json',dict(utc=now(),units=48,root_requests=288,
        python=sys.executable,python_sha256=sha(sys.executable),python_version=sys.version,platform=platform.platform(),
        cold_cap_seconds=5,rss_bytes=1073741824,rss_sample_seconds=.05,campaign_seconds=270,
        inputs_previously_observed=True,old_version_reruns=0,changed_checker=True,final_evaluation=False,
        files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in files]))
    print('Frozen48new-versionunits; old96outcomes retained',flush=True)

def run():
    assert __debug__;manifest=load(OUT/'MANIFEST.json')
    for r in manifest['files']:assert sha(S/r['path'])==r['sha256']
    assert sha(manifest['python'])==manifest['python_sha256']
    units=load(OUT/'INPUTS.json');old=collections.defaultdict(dict)
    for line in (OLD/'RAW.jsonl').read_text().splitlines():
        row=json.loads(line);old[row['id']][row['method']]=row
    assert len(old)==48 and all(len(v)==2 for v in old.values())
    save(OUT/'START.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(OUT/'MANIFEST.json')))
    start=time.monotonic();results=[];counts=collections.Counter()
    with (OUT/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(units):
            dest=OUT/'units'/u['id'];dest.mkdir(parents=True)
            row=dict(id=u['id'],group=u['group'],prices=u['prices'],n=u['n'],budgets=u['budgets'],
                method='all_budget_sweep',historical_statuses={k:r['status'] for k,r in old[u['id']].items()})
            if time.monotonic()-start>=270 or now()>='2026-09-08T01:50:00+00:00':
                row.update(status='NOT_RUN',reason='campaign_or_closeout_limit')
            else:
                cmd=[manifest['python'],'-B',str(ROOT/'worker.py'),str(OUT/'inputs'/(u['id']+'.json')),str(dest)]
                save(dest/'COMMAND.json',dict(argv=cmd,wall_seconds=5,rss_bytes=1073741824))
                before=time.monotonic();rss=0;reason=None
                with (dest/'stdout.txt').open('xb') as stdout,(dest/'stderr.txt').open('xb') as stderr:
                    p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,start_new_session=True)
                    while p.poll() is None:
                        if time.monotonic()-before>=5:reason='wall_timeout'
                        elif time.monotonic()-start>=270:reason='campaign_cap'
                        else:
                            q=subprocess.run(['/bin/ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True,timeout=2)
                            try:rss=max(rss,int(q.stdout.strip())*1024)
                            except ValueError:pass
                            if rss>1073741824:reason='memory_limit'
                        if reason:
                            try:os.killpg(p.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                            break
                        time.sleep(.05)
                    code=p.wait(timeout=5)
                row.update(cold_seconds=time.monotonic()-before,exit_code=code,sampled_peak_rss_bytes=rss)
                result=None
                if (dest/'RESULT.json').exists():
                    try:result=load(dest/'RESULT.json')
                    except Exception as e:row['parse_error']=repr(e)
                if reason:row.update(status='FAILURE' if reason=='memory_limit' else 'TIMEOUT',reason=reason,partial_result=result)
                elif code or result is None:row.update(status='INVALID',reason='process_or_missing_result',partial_result=result)
                else:row.update(result)
                if row['status']=='SUCCESS':
                    discrepancies=[]
                    for method,previous in old[u['id']].items():
                        if previous['status']=='SUCCESS' and previous['values']!=row['values']:discrepancies.append(method+'_values')
                        if method=='all_budget' and previous['status']=='SUCCESS' and previous['artifact_sha256']!=row['artifact_sha256']:discrepancies.append('all_budget_artifact')
                    row['historical_discrepancies']=discrepancies
                    if discrepancies:row.update(status='FAILURE',reason='historical_disagreement')
            counts[row['status']]+=1;results.append(row)
            raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            if (index+1)%8==0:print(json.dumps(dict(completed=index+1,counts=dict(counts))),flush=True)
    summary=dict(utc=now(),units=len(results),counts=dict(counts),seconds=time.monotonic()-start,
        raw_sha256=sha(OUT/'RAW.jsonl'),old_raw_unchanged=sha(OLD/'RAW.jsonl')==next(r['sha256'] for r in manifest['files'] if r['path']=='budget_oracle_01/benchmark01/RAW.jsonl'),
        cold_seconds_all_units=sum(r.get('cold_seconds',0) for r in results),
        historical_transitions=dict(collections.Counter(old[r['id']]['all_budget']['status']+'->'+r['status'] for r in results)),
        final_evaluation=False,old_version_reruns=0)
    save(OUT/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()

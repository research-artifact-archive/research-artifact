from pathlib import Path
import argparse,copy,datetime,hashlib,json,signal,sys,time,traceback
import strong

HERE=Path(__file__).resolve().parent
OLD=strong.OLD
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):
    with (HERE/name).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')

def prepare():
    files=[HERE/'PLAN.md',HERE/'strong.py',Path(__file__)]+[OLD/name for name in ['RAW.jsonl','RUNS.json','CASES.json','study.py','ChargedCallbacks.java','MANIFEST.json']]
    save('MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={str(p):sha(p) for p in files},
        ordinary=3094,original_controls=4,new_controls=6,new_native_executions=0,python=sys.version,total_seconds=300))
    print('bound3098 saved rows and6 new checker controls')

def mutate(row,name):
    r=copy.deepcopy(row)
    if name=='irrelevant_stats':r['untrusted_statistics']={'ignored':-1}
    if name=='wrong_failure_jobs':r['failures']=[[2,1],[3,1]]
    if name=='wrong_failure_epoch':r['failures']=[[1,1],[2,1]]
    if name=='failed_output_committed':
        for e in r['events']:
            if e['kind']=='D' and e['job']==2:assert e['id']==14;e['id']=13
        r['completed'][2]=13
    if name=='wrong_final_live':r['live'][0]=1
    return r

def accepted(check,case,run,row):
    try:return True,check(case,run,row),None
    except Exception:return False,None,traceback.format_exc()

def expired(*args):raise TimeoutError('registered recheck cap')

def run():
    m=json.loads((HERE/'MANIFEST.json').read_text())
    for p,h in m['files'].items():assert sha(Path(p))==h
    save('RUN_STARTED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(HERE/'MANIFEST.json')))
    runs=json.loads((OLD/'RUNS.json').read_text());cases={x['id']:x for x in json.loads((OLD/'CASES.json').read_text())}
    rows={x['id']:x for x in map(json.loads,(OLD/'RAW.jsonl').read_text().splitlines())};results=[];start=time.monotonic()
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,300)
    try:
        for spec in runs:
            ok,result,error=accepted(strong.verify_run,cases[spec['case']],spec,rows[spec['id']])
            expected=spec['expected_accept'];r=dict(id=spec['id'],control=spec['control'],accepted=ok,expected_accept=expected,
                status='SUCCESS' if ok==expected else 'FAILURE',result=result,error=error)
            results.append(r)
            if r['status']=='FAILURE' and not (HERE/'FIRST_ADVERSE.json').exists():save('FIRST_ADVERSE.json',dict(run=spec,raw=rows[spec['id']],result=r))
    finally:signal.setitimer(signal.ITIMER_REAL,0)
    save('VERIFICATION.json',results)
    target=next(r for r in runs if r['id']=='run-000364');c=cases[target['case']];original=rows[target['id']]
    controls=[]
    for name in ['unchanged','irrelevant_stats','wrong_failure_jobs','wrong_failure_epoch','failed_output_committed','wrong_final_live']:
        row=mutate(original,name);expected=name in ['unchanged','irrelevant_stats']
        old,_,old_error=accepted(strong.legacy.verify_run,c,target,row)
        new,_,new_error=accepted(strong.verify_run,c,target,row)
        controls.append(dict(id=name,expected_accept=expected,old_accepted=old,new_accepted=new,
                             status='SUCCESS' if new==expected else 'FAILURE',old_error=old_error,new_error=new_error,
                             mutated_record=row))
    save('CONTROLS.json',controls)
    summary=dict(saved_rows=len(runs),new_native_executions=0,
        ordinary={s:sum(r['status']==s and not r['control'] for r in results) for s in ['SUCCESS','FAILURE']},
        original_controls={s:sum(r['status']==s and r['control'] for r in results) for s in ['SUCCESS','FAILURE']},
        new_controls={s:sum(r['status']==s for r in controls) for s in ['SUCCESS','FAILURE']},
        elapsed_seconds=time.monotonic()-start,original_raw_sha256=sha(OLD/'RAW.jsonl'))
    save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);a=p.parse_args();{'prepare':prepare,'run':run}[a.command]()

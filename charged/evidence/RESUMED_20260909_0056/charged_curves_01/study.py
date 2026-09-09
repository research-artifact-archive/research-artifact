import argparse
import datetime
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import random
import signal
import sys
import time
import traceback
import compiler
import checker

HERE=Path(__file__).resolve().parent
STOP=datetime.datetime(2026,9,9,1,tzinfo=datetime.timezone.utc).timestamp()


def save(name,data):
    with (HERE/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    cases=[];sources=[]
    for tag in ['01','02']:
        old=HERE.parent/f'charged_guaranteed_{tag}'
        inputs=json.loads((old/'INPUTS.json').read_text())
        rows={r['id']:r for r in map(json.loads,(old/'RAW.jsonl').read_text().splitlines())}
        for case in inputs:
            row=rows[case['id']];assert row['status']=='SUCCESS'
            cases.append({'id':tag+'/'+case['id'],'jobs':case['jobs'],'edges':case['edges'],
                          'kind':'OBSERVED_REPLAY','expected_primitive':row['primitive'],
                          'budgets':list(range(len(row['primitive'])))})
        sources.extend([old/'INPUTS.json',old/'RAW.jsonl'])
    rng=random.Random(202609090130)
    for k in range(576):
        large=k>=512;n=2+k%7 if large else 1+k%8
        jobs=[[rng.getrandbits(128) if large else rng.randrange(21) for _ in range(5)] for _ in range(n)]
        for row in jobs:row[0]+=1
        edges=[[i,j] for i in range(n) for j in range(i+1,n) if rng.random()<0.35]
        cases.append({'id':f'new-{k:04d}','jobs':jobs,'edges':edges,
                      'kind':'ENCODED_MAGNITUDE' if large else 'FRESH_SCALAR',
                      'budgets':[0,1,2,4,16,2**64,2**128] if large else list(range(17))})
    save('INPUTS.json',cases)
    files=[HERE/name for name in ['PLAN.md','DERIVATION_01.md','compiler.py','checker.py','study.py','INPUTS.json']]+sources+[compiler.SOURCE]
    save('MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'files':{str(p):sha(p) for p in files},'cases':len(cases),'python':sys.version,
                         'unit_seconds':5,'campaign_seconds':300,'stop_utc':'2026-09-09T01:00:00Z'})
    print('materialized',len(cases),'compiler units')


def scalar(case,max_budget):
    jobs=case['jobs'];edges=case['edges'];n=len(jobs)
    @lru_cache(None)
    def f(mask,budget):
        if not mask:return 0
        options=[]
        for i,(w,p,g,v,r) in enumerate(jobs):
            if not mask>>i&1 or any(j==i and mask>>h&1 for h,j in edges):continue
            child=mask^(1<<i);m=min(v,g+r)
            options.append(w+p+g+r+f(child,budget))
            options.append(w+m+f(child,budget) if not budget else w+m+max(f(child,budget),f(mask,budget-1)))
            options.append(w+g+r+f(child,budget) if not budget else max(w+g+r+f(child,budget),2*w+p+g+r+f(child,budget-1)))
        return min(options)
    return [f((1<<n)-1,b) for b in range(max_budget+1)]


def execute(case):
    start=time.monotonic();data=compiler.compile_case(case);construction=time.monotonic()-start
    encoded=json.dumps(data,separators=(',',':'));loaded=json.loads(encoded)
    checked=checker.check(loaded)
    loaded['curves']={int(k):v for k,v in loaded['curves'].items()}
    loaded['actions']={int(k):v for k,v in loaded['actions'].items()}
    f=loaded['curves'][data['full']];base=data['baseline']
    expected=scalar(case,16 if case['kind']=='ENCODED_MAGNITUDE' else max(case['budgets']))
    for b,e in enumerate(expected):assert checker.value(f,b)+base==e,('scalar',b,e,checker.value(f,b)+base)
    if case['kind']=='OBSERVED_REPLAY':assert expected==case['expected_primitive'],'prior primitive mismatch'
    results=[]
    for b in case['budgets']:
        chosen=compiler.choose(loaded,data['full'],b)
        assert chosen[0]==checker.value(f,b)
        results.append({'budget':b,'total_value':base+checker.value(f,b),'action':chosen[1:]})
    run_bounds=[]
    for mask,profile in data['curves'].items():
        slopes={t for j,(c,p,d,s) in enumerate(data['prices']) if mask>>j&1 for t in [c,s]}
        count=len(profile)-1
        assert count<=2*len(slopes),('candidate run bound',mask,count,slopes)
        run_bounds.append(count)
    return {'id':case['id'],'kind':case['kind'],'status':'SUCCESS','states':data['states'],
            'root_positive_runs':len(f)-1,'maximum_state_positive_runs':max(run_bounds),
            'serialized_bytes':len(encoded.encode()),'artifact_sha256':hashlib.sha256(encoded.encode()).hexdigest(),
            'construction_seconds':construction,'check':checked,'queries':results,
            'scalar_checked_roots':len(expected)},data


def alarm(sig,frame):raise TimeoutError('registered wall cap')


def run():
    manifest=json.loads((HERE/'MANIFEST.json').read_text())
    for p,h in manifest['files'].items():assert sha(Path(p))==h,p
    cases=json.loads((HERE/'INPUTS.json').read_text());start=time.monotonic();rows=[]
    save('RUN_STARTED.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':sha(HERE/'MANIFEST.json')})
    signal.signal(signal.SIGALRM,alarm)
    with (HERE/'RAW.jsonl').open('x') as raw:
        for case in cases:
            t=time.monotonic();left=min(300-(t-start),STOP-time.time())
            if left<=0:row={'id':case['id'],'kind':case['kind'],'status':'NOT_RUN'}
            else:
                signal.setitimer(signal.ITIMER_REAL,min(5,left))
                try:row,data=execute(case)
                except TimeoutError as e:row={'id':case['id'],'kind':case['kind'],'status':'TIMEOUT','error':str(e)}
                except AssertionError:
                    row={'id':case['id'],'kind':case['kind'],'status':'FAILURE','error':traceback.format_exc()}
                except Exception:row={'id':case['id'],'kind':case['kind'],'status':'INVALID','error':traceback.format_exc()}
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['elapsed_seconds']=time.monotonic()-t;rows.append(row)
            raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
            if row['status'] not in ['SUCCESS','NOT_RUN'] and not (HERE/'FIRST_ADVERSE.json').exists():
                save('FIRST_ADVERSE.json',{'input':case,'result':row})
    summary={'planned':len(cases),'recorded':len(rows),
             'status_counts':{s:sum(r['status']==s for r in rows) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
             'by_kind':{kind:{s:sum(r['status']==s and r['kind']==kind for r in rows) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']} for kind in ['OBSERVED_REPLAY','FRESH_SCALAR','ENCODED_MAGNITUDE']},
             'elapsed_seconds':time.monotonic()-start,'raw_sha256':sha(HERE/'RAW.jsonl')}
    save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run'])
    {'prepare':prepare,'run':run}[parser.parse_args().command]()

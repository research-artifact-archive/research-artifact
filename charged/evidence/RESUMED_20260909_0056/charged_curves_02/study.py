import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import traceback
import compiler
import basis
import checker

HERE=Path(__file__).resolve().parent
STOP=datetime.datetime(2026,9,9,1,tzinfo=datetime.timezone.utc).timestamp()
CONTROL_IDS=['unmodified','untrusted_stats','price','baseline','available','fast','empty_curve','tail','origin','basis_intercept','missing_zero_slope']


def save(name,x):
    with (HERE/name).open('x') as f:json.dump(x,f,indent=2);f.write('\n')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    source=HERE.parent/'charged_curves_01/INPUTS.json'
    save('INPUTS.json',json.loads(source.read_text()))
    files=[HERE/name for name in ['PLAN.md','VALUE_ONLY_CHECKER_LIMITATION.md','compiler.py','basis.py','checker.py','study.py','INPUTS.json']]+[source,compiler.SOURCE,HERE.parent/'charged_curves_01/DERIVATION_02.md']
    save('MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'files':{str(p):sha(p) for p in files},'cases':3183,'controls':CONTROL_IDS,'python':sys.version,
         'unit_seconds':5,'total_seconds':300,'stop_utc':'2026-09-09T01:00:00Z'})
    print('materialized3183 observed compiler inputs and11 controls')


def controls():
    case={'jobs':[(3,2,0,0,0),(7,2,0,0,0),(5,6,0,0,0),(1,2,0,0,0)],'edges':[(0,1),(0,2),(1,3)]}
    good=json.loads(json.dumps(basis.compile_case(case)));rows=[]
    for ident in CONTROL_IDS:
        d=copy.deepcopy(good);full=str(d['full'])
        if ident=='untrusted_stats':d['stats']={'generated':True,'arbitrary_counter':-1000000}
        if ident=='price':d['prices'][0][0]+=1
        if ident=='baseline':d['baseline']+=1
        if ident=='available':d['actions'][full]['available']=[]
        if ident=='fast':d['actions'][full]['fast']=len(case['jobs'])
        if ident=='empty_curve':del d['curves']['0']
        if ident=='tail':d['curves'][full][-1][2]=1
        if ident=='origin':d['curves'][full][0][1]=1
        if ident=='basis_intercept':d['bases'][full]['0']+=1
        if ident=='missing_zero_slope':del d['bases'][full]['0']
        try:checker.check(d);accepted=True;error=None
        except Exception as e:accepted=False;error=repr(e)
        expected=ident in ['unmodified','untrusted_stats']
        rows.append({'id':ident,'expected_accept':expected,'accepted':accepted,
                     'status':'SUCCESS' if accepted==expected else 'FAILURE','error':error})
    return rows


def expired(sig,frame):raise TimeoutError('registered unit/campaign cap')


def run():
    m=json.loads((HERE/'MANIFEST.json').read_text())
    for p,h in m['files'].items():assert sha(Path(p))==h,p
    cases=json.loads((HERE/'INPUTS.json').read_text());start=time.monotonic();rows=[]
    save('RUN_STARTED.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':sha(HERE/'MANIFEST.json')})
    signal.signal(signal.SIGALRM,expired)
    with (HERE/'RAW.jsonl').open('x') as raw:
        for case in cases:
            t=time.monotonic();left=min(300-(t-start),STOP-time.time());row={'id':case['id'],'kind':case['kind']}
            if left<=0:row['status']='NOT_RUN'
            else:
                signal.setitimer(signal.ITIMER_REAL,min(5,left))
                try:
                    t1=time.monotonic();one=compiler.compile_case(case);a=time.monotonic()-t1
                    t1=time.monotonic();two=basis.compile_case(case);b=time.monotonic()-t1
                    assert one['curves']==two['curves'],'normalized curves differ'
                    encoded=json.dumps(two,separators=(',',':'));loaded=json.loads(encoded)
                    checked=checker.check(loaded)
                    row.update(status='SUCCESS',states=two['states'],root_basis_lines=len(two['bases'][two['full']]),
                               maximum_basis_lines=max(map(len,two['bases'].values())),
                               root_positive_runs=len(two['curves'][two['full']])-1,
                               serialized_bytes=len(encoded.encode()),artifact_sha256=hashlib.sha256(encoded.encode()).hexdigest(),
                               run_compiler_seconds=a,basis_compiler_seconds=b,check=checked)
                    if case['id']=='02/published-four-job-zero-fee':save('EXAMPLE_CERTIFICATE.json',loaded)
                except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
                except AssertionError:row.update(status='FAILURE',error=traceback.format_exc())
                except Exception:row.update(status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['elapsed_seconds']=time.monotonic()-t;rows.append(row)
            raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
            if row['status'] not in ['SUCCESS','NOT_RUN'] and not (HERE/'FIRST_ADVERSE.json').exists():save('FIRST_ADVERSE.json',{'input':case,'result':row})
    control_rows=controls();save('CONTROLS.json',control_rows)
    summary={'planned':len(cases),'recorded':len(rows),
             'status_counts':{s:sum(r['status']==s for r in rows) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
             'controls':len(control_rows),'control_failures':sum(r['status']!='SUCCESS' for r in control_rows),
             'elapsed_seconds':time.monotonic()-start,'raw_sha256':sha(HERE/'RAW.jsonl')}
    save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run'])
    {'prepare':prepare,'run':run}[parser.parse_args().command]()

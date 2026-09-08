from pathlib import Path
from functools import lru_cache
import collections
import datetime
import hashlib
import importlib.util
import itertools
import json
import os
import random
import signal
import sys
import time
import traceback
import types

ROOT=Path(__file__).resolve().parent;S=ROOT.parent
sys.dont_write_bytecode=True
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj);return obj
hybrid=load_module('pair_hybrid',S/'dependency_hybrid_01/hybrid.py')
sweep=load_module('pair_sweep',S/'sweep_certificate_02/certificate.py')
packed=load_module('pair_packed',S/'dependency_hybrid_check_02/check.py')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,obj):
    with (ROOT/name).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
def transform(original):
    a=[2*x for x in original];D=sum(original);m=len(a)
    return a,D,dict(cp=[[3*D+1,x] for x in a]+[[2*D,x] for x in a],edges=[[i,m+i] for i in range(m)])
def prepare():
    units=[]
    def put(a,group,selected):
        doubled,D,case=transform(a)
        units.append(dict(id=f'pair-{len(units):05}',original=list(a),a=doubled,D=D,
            case=case,budget=1,threshold=3*D,group=group,compiler_selected=selected))
    for m in range(1,7):
        for a in itertools.product(range(1,6),repeat=m):put(a,'EXHAUSTIVE_ORDERED',m<=3)
    assert len(units)==19530
    rng=random.Random(202609080829)
    for k in range(256):
        m=2+k%5;a=[rng.randint(1,9)*(1<<32)+rng.randrange(1024) for _ in range(m)]
        put(a,'WIDE_BINARY',k<16)
    assert len(units)==19786 and sum(u['compiler_selected'] for u in units)==171
    save('INPUTS.json',units)
    modules=set();seen=set();todo=[hybrid,sweep,packed]
    while todo:
        m=todo.pop()
        if id(m) in seen:continue
        seen.add(id(m));p=getattr(m,'__file__',None)
        if not p:continue
        p=Path(p).resolve()
        if p.suffix!='.py' or not p.is_relative_to(S):continue
        modules.add(p)
        todo.extend(x for x in vars(m).values() if isinstance(x,types.ModuleType))
    paths=modules|{ROOT/x for x in ['PLAN.md','PROOF_DRAFT.md','check.py','INPUTS.json']}
    save('MANIFEST.json',dict(utc=now(),units=len(units),compiler_selected=171,
        python=sys.executable,python_sha256=sha(sys.executable),python_version=sys.version,
        per_unit_seconds=2,campaign_seconds=180,closeout_utc='2026-09-08T01:50:00+00:00',
        files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]))
    print('Frozen19786units;171all-budgetsubchecks',flush=True)

def solve(case):
    n=len(case['cp']);pred=[0]*n;choices={}
    for u,v in case['edges']:pred[v]|=1<<u
    @lru_cache(None)
    def value(mask):
        if not mask:return 0
        best=None
        for i,(c,p) in enumerate(case['cp']):
            if mask>>i&1 and not pred[i]&mask:
                child=value(mask^(1<<i))
                candidate=min((p+child,i,'P'),(max(c,child),i,'F'))
                if best is None or candidate<best:best=candidate
        assert best is not None;choices[mask]=best;return best[0]
    mask=(1<<n)-1;v=value(mask);policy=[]
    while mask:
        _,i,mode=choices[mask];policy.append([i,mode]);mask^=1<<i
    return v,policy,value.cache_info().currsize

def scan(case,policy):
    done=set();paid=worst=0;branches=[]
    assert len(policy)==len(case['cp'])
    for i,mode in policy:
        assert type(i) is int and 0<=i<len(policy) and i not in done
        assert all(u in done for u,v in case['edges'] if v==i)
        c,p=case['cp'][i]
        if mode=='P':paid+=p
        else:
            assert mode=='F';branches.append([i,paid+c]);worst=max(worst,paid+c)
        done.add(i)
    return max(worst,paid),dict(no_failure=paid,first_failures=branches)

def unit(u):
    a=u['a'];D=u['D'];m=len(a);case=u['case'];cp=case['cp']
    assert len(cp)==2*m and case['edges']==[[i,m+i] for i in range(m)]
    assert all(cp[i]==[3*D+1,a[i]] and cp[m+i]==[2*D,a[i]] for i in range(m))
    assert sum(a)==2*D and all(x>0 for x in a)
    source_witness=next((mask for mask in range(1<<m) if sum(a[i] for i in range(m) if mask>>i&1)==D),None)
    value,policy,states=solve(case);scanned,branches=scan(case,policy)
    assert value==scanned and (value<=u['threshold'])==(source_witness is not None)
    recovered=None;constructed=None
    if value<=u['threshold']:
        assert all(mode=='P' for i,mode in policy if i<m)
        recovered=[i-m for i,mode in policy if i>=m and mode=='F']
        assert sum(a[i] for i in recovered)==D
    if source_witness is not None:
        selected=[i for i in range(m) if source_witness>>i&1]
        witness=[]
        for i in selected:witness.extend([[i,'P'],[m+i,'F']])
        for i in range(m):
            if i not in selected:witness.extend([[i,'P'],[m+i,'P']])
        cost,witness_branches=scan(case,witness);assert cost<=u['threshold']
        constructed=dict(policy=witness,value=cost,branches=witness_branches)
    compiled=None
    if u['compiler_selected']:
        data=hybrid.compile_case(case);encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
        (ROOT/'artifacts'/(u['id']+'.json')).write_bytes(encoded);data=json.loads(encoded)
        report=(packed if data['route']=='ordered' else sweep).check(data)
        assert not report['violations'] and hybrid.value(hybrid.load(data),1)==value
        compiled=dict(sha256=hashlib.sha256(encoded).hexdigest(),bytes=len(encoded),report=report)
    return dict(source_partition=source_witness is not None,source_witness_mask=source_witness,
        value=value,threshold=u['threshold'],states=states,policy=policy,branches=branches,
        recovered_partition=recovered,constructed=constructed,compiled=compiled)

def alarm(sig,frame):raise TimeoutError('fixed pair-hardness cap')
def run():
    assert __debug__;manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for r in manifest['files']:assert sha(S/r['path'])==r['sha256']
    assert sha(sys.executable)==manifest['python_sha256']
    inputs=json.loads((ROOT/'INPUTS.json').read_text());(ROOT/'artifacts').mkdir()
    save('RUN_STARTED.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
    start=time.monotonic();counts=collections.Counter();stats=collections.Counter();signal.signal(signal.SIGALRM,alarm)
    with (ROOT/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(inputs):
            before=time.monotonic()
            if before-start>=180 or now()>='2026-09-08T01:50:00+00:00':row=dict(id=u['id'],status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(2,180-(before-start)))
                try:row=dict(id=u['id'],status='SUCCESS',**unit(u))
                except AssertionError:row=dict(id=u['id'],status='FAILURE',error=traceback.format_exc())
                except TimeoutError:row=dict(id=u['id'],status='TIMEOUT',error=traceback.format_exc())
                except Exception:row=dict(id=u['id'],status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=time.monotonic()-before;counts[row['status']]+=1
            if row['status']=='SUCCESS':
                stats['positive' if row['source_partition'] else 'negative']+=1
                stats['states']+=row['states'];stats['compiler_checked']+=u['compiler_selected']
            raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            if (index+1)%2000==0:print(json.dumps(dict(completed=index+1,counts=dict(counts))),flush=True)
    result=dict(utc=now(),units=len(inputs),counts={k:counts[k] for k in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
        stats=dict(stats),seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'RAW.jsonl'))
    save('SUMMARY.json',result);print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()

import datetime
from functools import lru_cache
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
CURVES=HERE.parent/'charged_curves_02'
sys.path.insert(0,str(CURVES))
import basis
import checker as curve_checker

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
    with (HERE/n).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def write(n,s):
    with (HERE/n).open('x') as f:f.write(s)
def ordinary(case):
    jobs=case['jobs'];n=len(jobs);pred=[sum(1<<a for a,b in case['edges'] if b==i) for i in range(n)]
    @lru_cache(None)
    def f(mask,b):
        if not mask or not b:return 0
        return min(q for q,i,mode in choices(mask,b))
    def choices(mask,b):
        out=[]
        for i,(w,p,g,v,r) in enumerate(jobs):
            if mask>>i&1 and not pred[i]&mask:
                m=min(v,g+r);d=g+r-m;child=f(mask^(1<<i),b)
                cached=d+child if b==0 else d+max(child,w+p+f(mask^(1<<i),b-1))
                fast=child if b==0 else max(child,w+m+f(mask,b-1))
                out.extend([(cached,i,0),(fast,i,1),(p+d+child,i,2)])
        return out
    def choose(mask,b):return min(choices(mask,b))
    def paths(mask,b,path='',trace=(),cost=0):
        if not mask:yield path,list(trace),cost;return
        q,i,mode=choose(mask,b);w,p,g,v,r=jobs[i];rest=mask^(1<<i)
        if mode==2:
            yield from paths(rest,b,path,trace+(f'{i}:P',),cost+w+p+g+r);return
        prefix='C' if mode==0 else ('V' if v<=g+r else 'A')
        paid=w+g+r if mode==0 else w+min(v,g+r)
        yield from paths(rest,b,path+'S',trace+(f'{i}:{prefix}S',),cost+paid)
        if b:
            target=rest if mode==0 else mask
            failed=paid+w+p if mode==0 else paid
            yield from paths(target,b-1,path+'F',trace+(f'{i}:{prefix}F',),cost+failed)
    return f,choose,paths

def prepare():
    old=json.loads((HERE.parent/'charged_guaranteed_02/INPUTS.json').read_text())
    cases=old[:32]+old[-2:]
    assert len(cases)==34 and len({c['id'] for c in cases})==34
    for c in cases:c['native_source_input_previously_observed']=True
    controls=[{'id':'native-parent-control','jobs':[[2,5,1,1,1],[2,5,1,1,1]],'edges':[[0,1]],'native_source_input_previously_observed':False},
              {'id':'native-fee-control','jobs':[[2,5,2,1,2]],'edges':[],'native_source_input_previously_observed':False}]
    all_cases=cases+controls;builds=[];case_lines=[];run_lines=[];runs=[]
    for case in all_cases:
        t=time.perf_counter();data=basis.compile_case(case);data=json.loads(json.dumps(data));audit=curve_checker.check(data)
        name=case['id'];cf='curve_'+name+'.tsv';write(cf,'\n'.join(str(mask)+'\t'+';'.join(':'.join(map(str,row)) for row in f) for mask,f in sorted(data['curves'].items(),key=lambda z:int(z[0])))+'\n')
        save('certificate_'+name+'.json',data)
        builds.append({'id':name,'seconds':time.perf_counter()-t,'audit':audit})
        cols=[','.join(str(row[k]) for row in case['jobs']) for k in range(5)]
        pred=[sum(1<<a for a,b in case['edges'] if b==i) for i in range(len(case['jobs']))]
        case_lines.append('\t'.join([name]+cols+[','.join(map(str,pred)),cf]))
    def add(case,layout,kind,b,outcomes,seed,mutant,trace=None,cost=None,control=False):
        rid=f'run-{len(runs):06d}'
        record={'id':rid,'case':case['id'],'layout':layout,'kind':kind,'budget':b,'outcomes':outcomes,'seed':seed,'mutant':mutant,'control':control,'expected_accept':mutant=='none'}
        if trace is not None:record.update(expected_trace=trace,expected_cost=8*cost)
        runs.append(record);run_lines.append('\t'.join(map(str,[rid,case['id'],layout,kind,b,outcomes or '-',seed,mutant])))
    for case in cases:
        f,choose,paths=ordinary(case);full=(1<<len(case['jobs']))-1
        for b in range(5):
            expected=list(paths(full,b));baseline=sum(w+min(v,g+r) for w,p,g,v,r in case['jobs'])
            assert max(c for p,t,c in expected)==baseline+f(full,b)
            for layout in ['distinct','colliding']:
                for outcomes,trace,cost in expected:add(case,layout,'replay',b,outcomes,0,'none',trace,cost)
        for b in [1,2,4,8]:
            for layout in ['distinct','colliding']:
                for seed in [2026090901,2026090902,2026090903]:add(case,layout,'concurrent',b,'',seed,'none')
    parent,fee=controls
    for mutant in ['none','live_parent']:add(parent,'colliding','postwrite',1,'SS',0,mutant,control=True)
    for mutant in ['none','skip_conditional_fee']:add(fee,'distinct','replay',1,'S',0,mutant,control=True)
    write('CASES.tsv','\n'.join(case_lines)+'\n');write('RUNS.tsv','\n'.join(run_lines)+'\n');save('CASES.json',all_cases);save('RUNS.json',runs);save('BUILD_CHECKS.json',builds)
    sources=[HERE/'PLAN.md',HERE/'ChargedCallbacks.java',HERE/'study.py',HERE.parent/'charged_callback_theory_01/PROOF_DRAFT.md',CURVES/'basis.py',CURVES/'compiler.py',CURVES/'checker.py',basis.compiler.SOURCE]
    manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':{str(p):sha(p) for p in sources},
        'materialized':{p.name:sha(p) for p in HERE.iterdir() if p.is_file() and (p.suffix in ['.tsv','.json'])},
        'cases':34,'control_cases':2,'runs':len(runs),'replay_runs':sum(r['kind']=='replay' and not r['control'] for r in runs),
        'concurrent_runs':sum(r['kind']=='concurrent' for r in runs),'control_runs':4,'all_paths_cells':34*5*2,
        'python':sys.version,'java_version':subprocess.check_output(['java','-version'],stderr=subprocess.STDOUT,text=True),
        'javac_version':subprocess.check_output(['javac','-version'],stderr=subprocess.STDOUT,text=True),
        'compile_argv':['javac','-d',str(HERE/'classes'),str(HERE/'ChargedCallbacks.java')],
        'run_argv':['java','-cp',str(HERE/'classes'),'ChargedCallbacks',str(HERE)],'native_wall_cap_seconds':180,
        'hard_stop_utc':'2026-09-09T05:00:00Z','protocol':'exploratory, no retries/exclusions'}
    save('MANIFEST.json',manifest);print(json.dumps({k:manifest[k] for k in ['cases','runs','replay_runs','concurrent_runs','control_runs','all_paths_cells']},indent=2))

def execute():
    m=json.loads((HERE/'MANIFEST.json').read_text())
    for p,h in m['sources'].items():assert sha(Path(p))==h,p
    for p,h in m['materialized'].items():assert sha(HERE/p)==h,p
    assert not (HERE/'RAW.jsonl').exists()
    save('RUN_STARTED.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':sha(HERE/'MANIFEST.json')})
    start=time.perf_counter();out=subprocess.run(m['compile_argv'],capture_output=True,text=True,timeout=30)
    write('COMPILE.stdout',out.stdout);write('COMPILE.stderr',out.stderr)
    save('COMPILE_RECEIPT.json',{'returncode':out.returncode,'seconds':time.perf_counter()-start,'classes':{str(p.relative_to(HERE)):sha(p) for p in (HERE/'classes').glob('*.class')}})
    if out.returncode:save('EXECUTION_RECEIPT.json',{'status':'COMPILE_FAILURE','native_started':False});return
    deadline=datetime.datetime.fromisoformat(m['hard_stop_utc'].replace('Z','+00:00')).timestamp();limit=min(180,deadline-time.time())
    if limit<=0:save('EXECUTION_RECEIPT.json',{'status':'NOT_RUN_DEADLINE','native_started':False});return
    start=time.perf_counter()
    with (HERE/'RAW.jsonl').open('x') as stdout,(HERE/'RUN.stderr').open('x') as stderr:
        proc=subprocess.Popen(m['run_argv'],stdout=stdout,stderr=stderr,start_new_session=True)
        status='FINISHED'
        try:code=proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            status='CAMPAIGN_TIMEOUT';os.killpg(proc.pid,signal.SIGTERM)
            try:code=proc.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
    save('EXECUTION_RECEIPT.json',{'status':status,'native_started':True,'returncode':code,'seconds':time.perf_counter()-start,'raw_sha256':sha(HERE/'RAW.jsonl')})

def signed(n):return (n+2**31)%2**32-2**31
def fold(a):
    s=0
    for x in a:s=signed(31*s+x)
    return s

def verify_run(case,run,row):
    assert row['status']=='SUCCESS',row['status']
    n=len(case['jobs']);pred=[{a for a,b in case['edges'] if b==i} for i in range(n)]
    values={};done={};epochs=set();protect=[0]*n;kernel_count=[0]*n;work=0
    for event in row['events']:
        kind=event['kind'];i=event['job'];ident=event['id'];assert 0<=i<n
        if kind=='D':
            assert i not in done and pred[i]<=done.keys() and ident in values
            assert values[ident]['job']==i and values[ident]['kind']=='K'
            done[i]=ident;continue
        assert ident not in values
        if kind=='I':
            length=8*case['jobs'][i][0]-len(pred[i]);a=[17*(i+1)+31*k for k in range(length)];bg=0
        else:
            src=values[event['source']];assert src['job']==i
            if kind=='B':
                a=[signed(3*x+7) for x in src['a']];bg=src['bg']+1;assert event['epoch']==bg
                assert (i,bg) not in epochs;epochs.add((i,bg))
            elif kind=='K':
                assert pred[i]<=done.keys();parents=event['parents'];assert len(parents)==n
                parent=0
                for j in range(n):
                    if j in pred[i]:
                        assert parents[j]==done[j],('captured parent',i,j,parents[j],done[j])
                        parent=signed(31*parent+values[parents[j]]['seed'])
                    else:assert parents[j]==-1
                a=[signed(1664525*x+1013904223+parent) for x in src['a']];bg=src['bg'];work+=len(pred[i])+len(a)
                protect[i]+=int(event['inside']);kernel_count[i]+=1
            else:raise AssertionError(('event kind',kind))
        seed=fold(a);assert seed==event['seed'],('wrong value',kind,i,ident)
        values[ident]={'a':a,'seed':seed,'bg':bg,'job':i,'kind':kind}
    assert len(done)==n and row['completed']==[done[i] for i in range(n)]
    assert all(ident in values and values[ident]['job']==i for i,ident in enumerate(row['live']))
    assert row['writes']==len(epochs)<=run['budget']
    if run['kind']=='concurrent':assert row['writes']==run['budget']
    failures=[tuple(x) for x in row['failures']]
    assert len(failures)==len(set(failures)) and set(failures)<=epochs
    callbacks=[0]*n;conditionals=[0]*n;expected_kernels=[0]*n;expected_protected=[0]*n
    mask=(1<<n)-1;b=run['budget'];f,choose,paths=ordinary(case)
    for a in row['trace']:
        si,act=a.split(':');i=int(si);q,j,mode=choose(mask,b);assert i==j
        w,p,g,v,r=case['jobs'][i]
        if act=='P':
            assert mode==2;callbacks[i]+=1;expected_kernels[i]+=1;expected_protected[i]+=1;mask^=1<<i
        else:
            code,outcome=act;assert code==('C' if mode==0 else ('V' if v<=g+r else 'A'))
            assert outcome in ['S','F'];expected_kernels[i]+=1
            if code=='V':conditionals[i]+=1
            else:callbacks[i]+=1
            if outcome=='F':
                assert b>0;b-=1
                if code=='C':expected_kernels[i]+=1;expected_protected[i]+=1
            if outcome=='S' or code=='C':mask^=1<<i
    assert mask==0 and len(failures)==run['budget']-b
    assert kernel_count==expected_kernels and protect==expected_protected
    assert row['work']==work and row['protected_calls']==protect and row['callbacks']==callbacks and row['conditionals']==conditionals
    cost=work+8*sum(p*protect[i]+(g+r)*callbacks[i]+v*conditionals[i] for i,(w,p,g,v,r) in enumerate(case['jobs']))
    assert row['cost']==cost,('fee accounting',row['cost'],cost)
    ceiling=8*(sum(w+min(v,g+r) for w,p,g,v,r in case['jobs'])+f((1<<n)-1,run['budget']))
    assert row['ceiling']==ceiling and cost<=ceiling,('bound',cost,ceiling)
    if 'expected_trace' in run:assert row['trace']==run['expected_trace'] and cost==run['expected_cost']
    return {'cost':cost,'ceiling':ceiling,'failures':len(failures),'writes':row['writes'],'kernel_calls':sum(kernel_count)}

def check():
    runs=json.loads((HERE/'RUNS.json').read_text());cases={c['id']:c for c in json.loads((HERE/'CASES.json').read_text())}
    raw=[]
    if (HERE/'RAW.jsonl').exists():
        for line in (HERE/'RAW.jsonl').read_text().splitlines():raw.append(json.loads(line))
    assert len({r['id'] for r in raw})==len(raw);got={r['id']:r for r in raw};assert set(got)<={r['id'] for r in runs}
    rows=[];groups={}
    for run in runs:
        record={'id':run['id'],'control':run['control']};row=got.get(run['id'])
        if row is None:record.update(status='NOT_RUN',reason='missing native output')
        else:
            accepted=False;error=''
            try:result=verify_run(cases[run['case']],run,row);accepted=True
            except Exception:error=traceback.format_exc()
            if run['control']:
                record.update(status='SUCCESS' if accepted==run['expected_accept'] and row['status']=='SUCCESS' else 'FAILURE',expected_accept=run['expected_accept'],actual_accept=accepted,error=error,native_status=row['status'])
            elif row['status']!='SUCCESS':record.update(status=row['status'],error=row['error'])
            elif not accepted:record.update(status='FAILURE',error=error)
            else:
                record.update(status='SUCCESS',**result)
                if run['kind']=='replay':
                    key=(run['case'],run['budget'],run['layout']);group=groups.setdefault(key,{'max':0,'ceiling':result['ceiling'],'count':0});group['max']=max(group['max'],result['cost']);group['count']+=1
        rows.append(record)
    primary=[r for r in rows if not r['control']];controls=[r for r in rows if r['control']]
    groups_ok=len(groups)==34*5*2 and all(g['max']==g['ceiling'] for g in groups.values())
    summary={'planned':len(runs),'native_recorded':len(raw),'primary_planned':len(primary),
        'primary_status_counts':{s:sum(r['status']==s for r in primary) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
        'control_planned':len(controls),'control_status_counts':{s:sum(r['status']==s for r in controls) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
        'replay_cells_observed':len(groups),'replay_cells_planned':340,'all_replay_maxima_equal':groups_ok,
        'raw_sha256':sha(HERE/'RAW.jsonl') if (HERE/'RAW.jsonl').exists() else None,
        'arbitrary_java_interleavings_exhausted':False,'production_input':False,'actual_api_latency_measured':False}
    save('VERIFICATION.json',rows);save('REPLAY_GROUPS.json',[{'case':k[0],'budget':k[1],'layout':k[2],**v} for k,v in groups.items()]);save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':{'prepare':prepare,'execute':execute,'check':check}[sys.argv[1]]()

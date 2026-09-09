from pathlib import Path
import copy,datetime,hashlib,itertools,json,os,random,signal,subprocess,sys,time,traceback
HERE=Path(__file__).resolve().parent
UP=HERE.parent/'charged_curves_02';sys.path.insert(0,str(UP))
import compiler,basis,checker
DEST=HERE/'attempt01'
TRIPLES=[(1,0,0),(1,1,3),(1,7,1),(1,3,7),(2,1,0),(2,3,2),(2,7,7),(4,0,7),(4,1,3),(4,7,1),(7,3,7),(7,7,3)]
STOP=datetime.datetime(2026,9,9,4,50,tzinfo=datetime.timezone.utc).timestamp()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def eligible(case):
    n=len(case['jobs']);done=set();t=[]
    for w,p,g,v,r in case['jobs']:
        if v<g+r:return False
        t.append(min(w+g+r,w+p))
    if any(t[u]>t[v] for u,v in case['edges']):return False
    while len(done)<n:
        ready={i for i in range(n) if i not in done and all(u in done for u,v in case['edges'] if v==i)}
        if not ready:return False
        done.update(ready)
    return True
def order_for(case):
    n=len(case['jobs']);done=set();order=[]
    t=[min(w+g+r,w+p) for w,p,g,v,r in case['jobs']]
    while len(order)<n:
        ready=[i for i in range(n) if i not in done and all(u in done for u,v in case['edges'] if v==i)]
        assert ready
        i=min(ready,key=lambda i:(t[i],i));done.add(i);order.append(i)
    return order
def compatible(jobs,index):
    order=sorted(range(len(jobs)),key=lambda i:(min(jobs[i][0]+jobs[i][2]+jobs[i][4],jobs[i][0]+jobs[i][1]),i))
    return [[u,v] for a,u in enumerate(order) for b,v in enumerate(order) if a<b and (a*7+b*3+index)%5==0]
def prepare():
    DEST.mkdir();inputs=[]
    for n in range(1,6):
        for ids in itertools.combinations_with_replacement(range(len(TRIPLES)),n):
            jobs=[[w,p,0,k,k] for w,p,k in (TRIPLES[i] for i in ids)]
            for graph in ['independent','compatible']:
                inputs.append(dict(id='grid-'+str(len(inputs)),kind=graph,case=dict(jobs=jobs,edges=[] if graph=='independent' else compatible(jobs,len(inputs)))))
    rng=random.Random(202609090747)
    for k in range(160):
        n=1+k%8;jobs=[]
        for i in range(n):
            w=rng.randint(1,30);p=rng.randint(0,90);fee=rng.randint(0,90);v=fee+rng.randint(0,60)
            z=2**96 if k%5==0 else 1;jobs.append([w*z,p*z,0,v*z,fee*z])
        inputs.append(dict(id='seed-'+str(k),kind='fresh',case=dict(jobs=jobs,edges=compatible(jobs,k) if k%2 else [])))
    for case in json.loads((HERE.parent/'charged_callback_native_01/CASES.json').read_text()):
        if all(v>=g+r for w,p,g,v,r in case['jobs']):
            c=dict(jobs=case['jobs'],edges=[]);inputs.append(dict(id='observed-'+case['id'],kind='observed-prices-independent',case=c))
    controls=[dict(id='positive',case=dict(jobs=[[1,1,0,2,2],[2,2,0,2,2]],edges=[[0,1]]),expected=True),
              dict(id='reverse_edge',case=dict(jobs=[[1,1,0,2,2],[2,2,0,2,2]],edges=[[1,0]]),expected=False),
              dict(id='cycle',case=dict(jobs=[[1,1,0,2,2],[1,1,0,2,2]],edges=[[0,1],[1,0]]),expected=False),
              dict(id='common_fee_counter',case=dict(jobs=[[w,w,0,5,6] for w in [1,1,1,2]],edges=[]),expected=False)]
    save(DEST/'INPUTS.json',inputs);save(DEST/'CONTROLS_INPUT.json',controls)
    files=[HERE/'PLAN.md',Path(__file__),DEST/'INPUTS.json',DEST/'CONTROLS_INPUT.json']+[UP/p for p in ['compiler.py','basis.py','checker.py']]+[compiler.SOURCE]
    save(DEST/'MANIFEST.json',dict(inputs=len(inputs),input_classes=dict((k,sum(i['kind']==k for i in inputs)) for k in sorted({i['kind'] for i in inputs})),sources={str(p):sha(p) for p in files},maximum_unit_seconds=5,maximum_campaign_seconds=180,known_candidate_proof_before_outcomes=True,commutation_lengths=list(range(5)),commutation_slopes=[1,2,4,7],commutation_a=[1,2,4],commutation_s_offsets=['same','plus1','eight'],commutation_q=[0,1,3,10]))
    print('fixed inputs',len(inputs))
def scalar(case,budget):
    from functools import lru_cache
    jobs=case['jobs'];n=len(jobs)
    @lru_cache(None)
    def f(mask,b):
        if not mask or not b:return 0
        options=[]
        for i,(w,p,g,v,r) in enumerate(jobs):
            if not mask>>i&1 or any(vv==i and mask>>u&1 for u,vv in case['edges']):continue
            child=mask^(1<<i);x=f(child,b);c=w+g+r;s=w+p
            options.extend([p+x,max(x,c+f(mask,b-1)),max(x,s+f(child,b-1))])
        return min(options)
    return [f((1<<n)-1,b) for b in range(budget+1)]
def sorted_curves(case):
    order=order_for(case);curves={len(order):[(0,0,0)]}
    for k in reversed(range(len(order))):
        w,p,g,v,r=case['jobs'][order[k]];t=min(w+g+r,w+p);child=curves[k+1]
        curves[k]=compiler.base.lower(compiler.base.shift_value(child,p),compiler.base.floor_slopes(child,t))
    return order,curves
def check_runtime(case,order,curves):
    checks=0
    for k,i in enumerate(order):
        own,child=curves[k],curves[k+1];w,p,g,v,r=case['jobs'][i];c=w+g+r;s=w+p
        probes={0,1,2**64}
        for f in [own,child]:
            for x,y,d in f:probes.update([max(0,x-1),x,x+1])
        for b in probes:
            x=compiler.base.at(child,b);y=compiler.base.at(own,b)
            choices=[(p+x,'P'),(x if b==0 else max(x,c+compiler.base.at(own,b-1)),'A'),(x if b==0 else max(x,s+compiler.base.at(child,b-1)),'C')]
            value,mode=min(choices);assert value==y,(k,b,choices,own,child)
            if mode=='P':success=p+x;assert success<=y
            elif mode=='C':
                assert x<=y
                if b:assert s+compiler.base.at(curves[k+1],b-1)<=y
            else:
                assert x<=y
                if b:assert c+compiler.base.at(curves[k],b-1)<=y
            checks+=1
    return checks
def commutation():
    results=[]
    def prefix(slopes):
        out=[0]
        for d in slopes:out.append(out[-1]+d)
        return out
    def r(slopes,a,q):
        f=prefix(slopes);raised=prefix([max(a,d) for d in slopes]);v=[min(x+q,y) for x,y in zip(f,raised)]
        return [y-x for x,y in zip(v,v[1:])]
    def insert(slopes,s):return sorted(slopes+[s],reverse=True)
    for n in range(5):
        for ms in itertools.combinations_with_replacement([1,2,4,7],n):
            slopes=sorted(ms,reverse=True)+[0]*32
            for a,q in itertools.product([1,2,4],[0,1,3,10]):
                for s in [a,a+1,8]:
                    left=r(insert(slopes,s),a,q);right=insert(r(slopes,a,q),s)
                    assert left==right,(ms,a,q,s,left,right)
                    results.append(dict(marginals=ms,a=a,premium=q,insert=s,equal=True))
    return results
def worker():
    m=json.loads((DEST/'MANIFEST.json').read_text());assert all(sha(Path(p))==h for p,h in m['sources'].items())
    save(DEST/'RUN_STARTED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(DEST/'MANIFEST.json')))
    started=time.monotonic();results=[]
    def expiry(*args):raise TimeoutError('fixed input/campaign limit')
    signal.signal(signal.SIGALRM,expiry)
    with (DEST/'RAW.jsonl').open('x') as f:
        for item in json.loads((DEST/'INPUTS.json').read_text()):
            left=min(180-(time.monotonic()-started),STOP-time.time());row=dict(id=item['id'],kind=item['kind'])
            if left<=0:row['status']='NOT_RUN'
            else:
                signal.setitimer(signal.ITIMER_REAL,min(5,left))
                try:
                    case=item['case'];assert eligible(case)
                    full=compiler.compile_case(case);cert=basis.compile_case(case);checker.check(json.loads(json.dumps(cert)));assert full['curves']==cert['curves']
                    order,curves=sorted_curves(case);assert curves[0]==full['curves'][full['full']]
                    maximum=16 if len(case['jobs'])<=5 else 4;values=scalar(case,maximum)
                    assert values==[compiler.base.at(curves[0],b) for b in range(maximum+1)]
                    checks=check_runtime(case,order,curves)
                    row.update(status='SUCCESS',order=order,curve=curves[0],scalar_values=values,runtime_checks=checks,baseline=full['baseline'])
                except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
                except Exception:row.update(status='FAILURE',error=traceback.format_exc());
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            results.append(row);f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush()
            if row['status']!='SUCCESS' and not (DEST/'FIRST_ADVERSE.json').exists():save(DEST/'FIRST_ADVERSE.json',dict(input=item,result=row))
    controls=[]
    for c in json.loads((DEST/'CONTROLS_INPUT.json').read_text()):
        actual=eligible(c['case']);controls.append(dict(id=c['id'],actual=actual,expected=c['expected'],met=actual==c['expected']))
    save(DEST/'CONTROLS.json',controls)
    try:comm=commutation();save(DEST/'COMMUTATION.json',comm);comm_status='SUCCESS'
    except Exception:comm=[];save(DEST/'COMMUTATION_FAILURE.json',dict(error=traceback.format_exc()));comm_status='FAILURE'
    counts={s:sum(r['status']==s for r in results) for s in ['SUCCESS','FAILURE','TIMEOUT','NOT_RUN']}
    summary=dict(inputs=m['inputs'],recorded=len(results),counts=counts,controls=len(controls),controls_met=sum(c['met'] for c in controls),commutation_units=len(comm),commutation_status=comm_status,seconds=time.monotonic()-started,universal_proof_by_tests=False)
    save(DEST/'SUMMARY.json',summary);print(json.dumps(summary,indent=2))
def run():
    with (DEST/'stdout.txt').open('xb') as f,(DEST/'stderr.txt').open('xb') as e:
        p=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'worker'],stdout=f,stderr=e,start_new_session=True)
        try:code=p.wait(timeout=min(200,STOP-time.time()))
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);code=p.wait()
    save(DEST/'PROCESS.json',dict(returncode=code))
    if (DEST/'SUMMARY.json').exists():print((DEST/'SUMMARY.json').read_text())
    else:raise RuntimeError('worker did not complete')
if __name__=='__main__':{'prepare':prepare,'worker':worker,'run':run}[sys.argv[1]]()

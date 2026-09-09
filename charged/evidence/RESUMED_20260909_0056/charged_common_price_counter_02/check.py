from pathlib import Path
import datetime,hashlib,itertools,json,signal,sys,time
HERE=Path(__file__).resolve().parent
UP=HERE.parent/'charged_curves_02'
sys.path.insert(0,str(UP))
import compiler,basis,checker

def scalar(case,maximum):
    jobs,edges=case['jobs'],case['edges'];n=len(jobs);full=(1<<n)-1
    states={full};pending=[full];ready={}
    while pending:
        s=pending.pop();a=[i for i in range(n) if s>>i&1 and not any(v==i and s>>u&1 for u,v in edges)]
        assert not s or a
        ready[s]=a
        for i in a:
            t=s^(1<<i)
            if t not in states:states.add(t);pending.append(t)
    previous={s:0 for s in states};out=[0]
    for b in range(1,maximum+1):
        current={0:0}
        for s in sorted(states-{0}):
            options=[]
            for i in ready[s]:
                w,p,g,v,r=jobs[i];d=g+r-min(v,g+r);c=w+min(v,g+r);t=s^(1<<i)
                options += [p+d+current[t],max(current[t],c+previous[s]),d+max(current[t],w+p+previous[t])]
            current[s]=min(options)
        out.append(current[full]);previous=current
    return out

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')

def main():
    dest=HERE/'attempt01';dest.mkdir()
    inputs=[dict(id='scale'+str(z),jobs=[[z*w,z*w,0,5*z,6*z] for w in [1,1,1,2]],edges=[]) for z in [1,4]]
    save(dest/'INPUTS.json',inputs)
    files=[HERE/'PLAN.md',Path(__file__),dest/'INPUTS.json']+[UP/x for x in ['compiler.py','basis.py','checker.py']]+[compiler.SOURCE]
    save(dest/'MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in files],budgets=list(range(10)),known_expected_budget1={'scale1':[6,5,5],'scale4':[24,20,20]},status='FIXED_BEFORE_COMPUTATIONAL_VERIFICATION'))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('30second bound')));signal.alarm(30)
    start=time.monotonic();results=[]
    for case in inputs:
        c=compiler.compile_case(case);cert=basis.compile_case(case);checker.check(cert)
        actual=[compiler.base.at(c['curves'][c['full']],b) for b in range(10)]
        assert actual==scalar(case,9)
        orders=[]
        for order in itertools.permutations(range(4)):
            fixed=dict(jobs=case['jobs'],edges=list(zip(order,order[1:])))
            f=compiler.compile_case(fixed);values=[compiler.base.at(f['curves'][f['full']],b) for b in range(10)]
            assert values==scalar(fixed,9)
            orders.append(dict(order=order,values=values,profile=f['curves'][f['full']]))
        z=case['jobs'][0][0];asc=orders[0]['values'][1];reverse=next(o['values'][1] for o in orders if o['order']==(3,0,1,2))
        assert (asc,reverse,actual[1])==(6*z,5*z,5*z)
        results.append(dict(id=case['id'],baseline=c['baseline'],unrestricted=actual,ascending_excess=asc,alternative_excess=reverse,orders=orders))
    signal.alarm(0);save(dest/'RESULTS.json',results)
    summary=dict(status='SUCCESS',inputs=2,fixed_order_cases=48,budget_roots=500,seconds=time.monotonic()-start,general_common_fee_ascending_conjecture='REFUTED',equal_fee_case='UNRESOLVED',native_execution=False)
    save(dest/'SUMMARY.json',summary);print(json.dumps(summary))

if __name__=='__main__':main()

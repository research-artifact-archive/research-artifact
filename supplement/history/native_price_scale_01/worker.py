import datetime,hashlib,importlib.util,json,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
COMP=HERE.parents[1]/'quantitative_progress/adaptive_retry_control/compiler.py'
SCREEN=COMP.with_name('screened_solver.py')
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def ordered(g,screen=False):
    n=len(g['jobs']);B=g['budget'];base=sum(g['normal_costs'])
    jobs=sorted(g['jobs'],key=lambda x:(x[1],x[0]));P=sum(p for p,c in jobs)
    assert all(0<=p<=c for p,c in jobs)
    assert all(p*jobs[0][1]==c*jobs[0][0] for p,c in jobs)
    if B==0:return dict(value=base,root_saturated=True,bellman_cells=0,bound_cells=0)
    if B>=n:return dict(value=base+P,root_saturated=True,bellman_cells=0,bound_cells=0)
    root=None
    if screen:
        root=module(SCREEN,'root_bounds').bounds(g)
        if root['lower']==root['upper']:
            return dict(value=base+root['upper'],root_screened=True,root_bounds=root,bellman_cells=0,bound_cells=0)
    f=[0]*(B+1);cells=bound_cells=screened=0;total=0
    if screen:
        T=[P+B*max(c for p,c in jobs)+1]*(B+1);S=[0]*(B+1);largest=[0]
        for p,c in reversed(jobs):largest.append(largest[-1]+p)
    for k,(p,c) in enumerate(reversed(jobs),1):
        previous_total=total;total+=p;out=[0]*(B+1);saturated=False
        for b in range(1,B+1):
            if screen:
                candidate=previous_total+b*c
                if candidate<T[b]:T[b]=candidate
                v=min(total,b*c)
                if v>S[b]:S[b]=v
                lower=max(largest[min(b,k)],S[b]);upper=min(total,T[b]);bound_cells+=1
                if lower>upper:raise AssertionError(('bound inversion',k,b,lower,upper))
            if saturated or b>=k:out[b]=total;saturated=True
            elif screen and lower==upper:out[b]=upper;screened+=1
            else:
                out[b]=min(p+f[b],max(f[b],c+out[b-1]));cells+=1
                if screen and not lower<=out[b]<=upper:raise AssertionError(('value outside bounds',k,b,out[b],lower,upper))
            if out[b]==total:saturated=True
        f=out
    return dict(value=base+f[B],root_saturated=False,root_screened=False,root_bounds=root,
                bellman_cells=cells,bound_cells=bound_cells,screened_cells=screened)

def exact(g):
    jobs=g['jobs'];n=len(jobs);old=[0]*(1<<n)
    for b in range(1,g['budget']+1):
        cur=[0]*(1<<n)
        for s in range(1,1<<n):
            candidates=[]
            for i,(p,c) in enumerate(jobs):
                if s>>i&1:
                    rest=s^(1<<i);candidates.extend([p+cur[rest],max(cur[rest],c+old[s])])
            cur[s]=min(candidates)
        old=cur
    return sum(g['normal_costs'])+old[-1]

def main():
    method,source,dest=sys.argv[1:];start=time.perf_counter();g=json.loads(Path(source).read_text());out=Path(dest)
    row=dict(method=method,status='SUCCESS')
    try:
        if method=='packed':
            comp=module(COMP,'compiler');ctrl=comp.compile_controller(g);data=comp.canonical(ctrl)
            (out/'controller.json').write_bytes(data)
            row.update(value=ctrl['value'],controller_bytes=len(data),thresholds=len(ctrl['protect_at_budget']),slope_runs=len(ctrl['value_slopes']),runtime_synthesis_calls=0)
        elif method=='ordered_saturation':row.update(ordered(g,False),controller_output=False)
        elif method=='screened_ordered':row.update(ordered(g,True),controller_output=False)
        else:raise ValueError(method)
    except Exception as e:row.update(status='INVALID',error=repr(e))
    row.update(worker_seconds=time.perf_counter()-start,peak_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               peak_rss_units='bytes' if sys.platform=='darwin' else 'KiB')
    (out/'RESULT.json').write_text(json.dumps(row,sort_keys=True)+'\n')
    print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()

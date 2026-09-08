"""Independent exact B1/B2 contingent-policy evaluation and scalar oracle."""
from functools import lru_cache

def validate(case):
    cp=case['cp'];n=len(cp)
    assert all(len(x)==2 and type(x[0]) is int and x[0]>0 and type(x[1]) is int and x[1]>=0 for x in cp)
    pred=[set() for _ in cp];seen=set()
    for u,v in case['edges']:
        assert type(u) is int and type(v) is int and 0<=u<n and 0<=v<n and u!=v and (u,v) not in seen
        seen.add((u,v));pred[v].add(u)
    done=set()
    while len(done)<n:
        ready={i for i in range(n) if i not in done and pred[i]<=done};assert ready,'cycle';done|=ready
    return pred

def scan_spine(case,spine,active):
    pred=validate(case);n=len(pred);done=set(range(n))-set(active);paid=0;fast=[]
    assert len(spine)==len(active)
    for i,mode in spine:
        assert type(i) is int and i in active and i not in done and pred[i]<=done
        c,p=case['cp'][i]
        if mode=='P':paid+=p
        elif mode=='F':fast.append(dict(job=i,prefix=paid,remaining=sorted(set(range(n))-done)))
        else:raise AssertionError(mode)
        done.add(i)
    assert len(done)==n
    return paid,fast

def check(case,artifact):
    assert artifact['schema']=='specified-budget-contingent-order-v1'
    budget=artifact['budget'];assert budget in (1,2)
    paid,fast=scan_spine(case,artifact['root'],set(range(len(case['cp']))))
    value=paid;branches=[]
    if budget==1:
        assert artifact['branches']=={}
        for x in fast:value=max(value,x['prefix']+case['cp'][x['job']][0])
    else:
        assert set(artifact['branches'])=={str(x['job']) for x in fast}
        for x in fast:
            subpaid,subfast=scan_spine(case,artifact['branches'][str(x['job'])],set(x['remaining']))
            sub=max([subpaid]+[y['prefix']+case['cp'][y['job']][0] for y in subfast])
            total=x['prefix']+case['cp'][x['job']][0]+sub
            value=max(value,total);branches.append(dict(first_failure=x['job'],remaining=x['remaining'],branch_value=sub,total=total))
    return dict(value=value,no_failure=paid,branches=branches)

def scalar(case,budget):
    pred=validate(case);cp=case['cp'];n=len(cp);pm=[sum(1<<u for u in ps) for ps in pred]
    @lru_cache(None)
    def value(mask,b):
        if not mask or not b:return 0
        previous=value(mask,b-1);actions=[]
        for i,(c,p) in enumerate(cp):
            if mask>>i&1 and not pm[i]&mask:
                child=value(mask^(1<<i),b)
                actions.extend([p+child,max(child,c+previous)])
        return min(actions)
    v=value((1<<n)-1,budget);return v,value.cache_info().currsize

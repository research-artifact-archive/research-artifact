"""Exact common-policy thresholds for an explicit fresh-preparation interface.

No native cost calibration is implied. Profile construction is outside this
module: inputs include every observable dirty set and its minimum write count.
"""
from functools import lru_cache

def compile_thresholds(jobs, edges, retries, toll, known_curve=None, export=False):
    n=len(jobs); full=(1<<n)-1
    predecessor=[sum(1<<a for a,b in edges if b==i) for i in range(n)]
    ceiling=sum(j['sigma'] for j in jobs)+retries*max(j['sigma'] for j in jobs)
    grouped=[]
    for j in jobs:
        by_count={}
        for o in j['observations']:
            by_count[o['c']]=max(by_count.get(o['c'],0),o['w'])
        grouped.append(tuple(sorted(by_count.items())))
    @lru_cache(None)
    def ready(s):
        return tuple(i for i in range(n) if s>>i&1 and not(predecessor[i]&s))
    @lru_cache(None)
    def value(s,b,t):
        if not s:return 0
        return min(max(toll+min(w+value(s^(1<<i),b-c,t), value(s,b-c,t-1) if t else float('inf')) for c,w in grouped[i] if c<=b) for i in ready(s))
    curve=list(known_curve) if known_curve is not None else [value(full,b,retries) for b in range(ceiling+2)]
    assert len(curve)>=ceiling+1
    table={}; actions={}
    def theta(s,t,e):
        key=(s,t,e)
        if key in table:return table[key]
        if not s:
            table[key]=curve[e]
            return table[key]
        options=[]
        for i in ready(s):
            margins=[]
            for c,w in grouped[i]:
                nxt=min(e+c,ceiling)
                accept=theta(s^(1<<i),t,nxt)-toll-w
                reject=theta(s,t-1,nxt)-toll if t else float('-inf')
                margins.append(max(accept,reject))
            options.append((min(margins),i))
        best=max(v for v,i in options)
        chosen=next(i for v,i in options if v==best)
        table[key]=best;actions[key]=chosen
        return best
    margin=theta(full,retries,0)
    result=dict(ceiling=ceiling,root_margin=margin,exists=margin>=0,curve=curve,threshold_states=len(table),value_states=value.cache_info().currsize)
    if export:
        result['certificate']=dict(schema='repair-toll-common-policy-v1',jobs=jobs,edges=edges,retries=retries,toll=toll,ceiling=ceiling,curve=curve,root=[full,retries,0],thresholds=[dict(state=list(k),value=v,job=actions.get(k)) for k,v in sorted(table.items())])
    return result

def run_certificate_policy(certificate, observation_masks):
    """Replay a finite observed history without receiving a writer budget."""
    jobs=certificate['jobs'];n=len(jobs);s=(1<<n)-1;t=certificate['retries'];e=0;paid=0;toll=certificate['toll'];E=certificate['ceiling']
    table={tuple(r['state']):r for r in certificate['thresholds']}
    trace=[]
    for mask in observation_masks:
        if not s:raise ValueError('observations after completion')
        row=table[s,t,e];i=row['job'];o=next(o for o in jobs[i]['observations'] if o['mask']==mask)
        nxt=min(e+o['c'],E);child=s^(1<<i)
        accept=paid+toll+o['w']<=table[child,t,nxt]['value']
        before=[s,t,e,paid]
        if accept:s=child;paid+=toll+o['w']
        elif t and paid+toll<=table[s,t-1,nxt]['value']:t-=1;paid+=toll
        else:raise ValueError('certificate has no feasible action')
        e=nxt;trace.append(dict(before=before,job=i,mask=mask,min_writes=o['c'],damage=o['w'],action='accept' if accept else 'reject',after=[s,t,e,paid]))
    return dict(completed=s==0,cost=paid,min_count_clipped=e,trace=trace)

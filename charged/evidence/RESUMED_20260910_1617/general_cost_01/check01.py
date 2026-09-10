#!/usr/bin/env python3
"""Exploratory contingent-policy vectors and heterogeneous-toll checks."""
from pathlib import Path
from functools import lru_cache
import itertools, json, time, datetime, hashlib

HERE = Path(__file__).resolve().parent
START = time.monotonic()

def bounded():
    if time.monotonic() - START > 300:
        raise TimeoutError('whole-study cap300seconds')

def pareto(vectors):
    unique = sorted(set(vectors))
    frontier = []
    for v in unique:
        if any(all(a <= b for a, b in zip(u, v)) for u in frontier):
            continue
        frontier = [u for u in frontier if not all(a <= b for a, b in zip(v, u))]
        frontier.append(v)
    return tuple(frontier)

def contingent_vectors(observations, q, toll):
    """Full observation branches, not least-write threshold states."""
    ceiling = q * max(c for _, c, _ in observations) + 1
    width = ceiling + 1
    @lru_cache(None)
    def tree(k):
        combined = (tuple([-1] * width),)
        for mask, count, damage in observations:
            accept = tuple(-1 if b < count else toll + damage for b in range(width))
            options = [accept]
            if k > 1:
                options += [tuple(-1 if b < count else toll + v[b-count] for b in range(width)) for v in tree(k-1)]
            combined = pareto(tuple(max(a,b) for a,b in zip(x,y)) for x in combined for y in options)
        bounded()
        return combined
    vectors = tree(q)
    informed = tuple(min(v[b] for v in vectors) for b in range(width))
    loss = min(max(a-b for a,b in zip(v,informed)) for v in vectors)
    @lru_cache(None)
    def zero_policy(k,b):
        return max(toll + (zero_policy(k-1,b-c) if k>1 and h>0 else h) for _,c,h in observations if c<=b)
    return {'q':q,'toll':toll,'observations':observations,'curve':informed,'vectors':vectors,'vector_count':len(vectors),'minimum_uniform_loss':loss,'positive_only_retry_curve':[zero_policy(q,b) for b in range(width)]}

def thresholds(jobs, edges, retries, tolls):
    n=len(jobs); full=(1<<n)-1
    pred=[sum(1<<a for a,b in edges if b==i) for i in range(n)]
    maxima=[max(o[2] for o in j) for j in jobs]
    saturation=[min(o[1] for o in j if o[2]==maxima[i]) for i,j in enumerate(jobs)]
    # This bound is for adversarially saturating all attempts, not profile enumeration cost.
    ceiling=sum(saturation)+retries*max(saturation)
    @lru_cache(None)
    def ready(s):return tuple(i for i in range(n) if s>>i&1 and not(pred[i]&s))
    @lru_cache(None)
    def value(s,b,t):
        if not s:return 0
        return min(max(tolls[i]+min(h+value(s^(1<<i),b-c,t),value(s,b-c,t-1) if t else float('inf')) for _,c,h in jobs[i] if c<=b) for i in ready(s))
    curve=tuple(value(full,b,retries) for b in range(ceiling+2))
    @lru_cache(None)
    def theta(s,t,e):
        if not s:return curve[e]
        return max(min(max(theta(s^(1<<i),t,min(e+c,ceiling))-tolls[i]-h,theta(s,t-1,min(e+c,ceiling))-tolls[i] if t else float('-inf')) for _,c,h in jobs[i]) for i in ready(s))
    margin=theta(full,retries,0)
    bounded()
    return {'exists':margin>=0,'margin':margin,'loss':-margin,'curve':curve,'maxima':maxima,'saturation':saturation,'states':theta.cache_info().currsize}

def main():
    results=[]; errors=[]
    fixtures=[('positive_toll_flat',[(0,0,0),(1,1,100)],2,1),('superadditive',[(0,0,0),(1,1,1),(2,1,1),(3,2,100)],2,0),('zero_singletons',[(0,0,0),(1,1,0),(2,1,0),(3,2,10)],2,0)]
    for name,obs,q,toll in fixtures:
        x=contingent_vectors(tuple(obs),q,toll); x['name']=name
        t=thresholds([obs],[],q-1,[toll]);x['threshold']=t
        if x['minimum_uniform_loss']!=t['loss'] or tuple(x['curve'][:len(t['curve'])])!=tuple(t['curve']):errors.append({'fixture':name,'type':'vector_threshold_mismatch'})
        results.append(x)
    assert results[0]['curve'][1]==2 and results[0]['minimum_uniform_loss']==1
    assert results[1]['curve'][3]==1 and results[1]['positive_only_retry_curve'][3]==100
    assert results[2]['minimum_uniform_loss']==0 and results[2]['curve'][:4]==(0,0,0,0)
    (HERE/'SINGLE_JOB_RESULTS.json').write_text(json.dumps(results,indent=2)+'\n')
    profiles=[[(0,0,0),(1,1,1)],[(0,0,0),(1,1,3)],[(0,0,0),(1,1,1),(2,1,2),(3,2,3)],[(0,0,0),(3,1,3)]]
    rows=[]
    with (HERE/'HETEROGENEOUS_ROWS.jsonl').open('x') as out:
        for pi,pj,ki,kj,r in itertools.product(range(4),range(4),range(1,5),range(1,5),[1,2]):
            jobs=[profiles[pi],profiles[pj]];tolls=[ki,kj]
            for edges in [[],[(0,1)],[(1,0)]]:
                x=thresholds(jobs,edges,r,tolls);suff=all(k>=w for k,w in zip(tolls,x['maxima']))
                sinks=[i for i in range(2) if not any(a==i for a,b in edges)]
                violation=any(tolls[i]<x['maxima'][i] for i in sinks)
                expected=x['exists']==suff if not edges else (not suff or x['exists']) and (not violation or not x['exists'])
                row={'profiles':[pi,pj],'tolls':tolls,'r':r,'edges':edges,**x,'condition_pass':expected}
                if not expected:errors.append(row)
                rows.append(row);out.write(json.dumps(row)+'\n')
    receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not errors else 'FAIL','single_job_fixtures':3,'heterogeneous_conditions':len(rows),'independent_conditions':sum(not x['edges'] for x in rows),'dag_conditions':sum(bool(x['edges']) for x in rows),'errors':errors,'seconds':time.monotonic()-START,'independence':'full contingent vectors independent of threshold for single jobs; heterogeneous recurrence is adapted author code, not independent oracle','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE/'RESULT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    assert not errors

if __name__=='__main__':main()

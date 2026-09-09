"""Unchanged original all-ready scalar reference, extracted with source binding."""
from functools import lru_cache

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

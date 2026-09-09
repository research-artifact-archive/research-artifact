"""Original-price scalar recurrence for one explicit completion order; no compact imports."""
from functools import lru_cache

def ordinary(case):
    jobs=case['jobs'];n=len(jobs);order=case['order'];mask=(1<<n)-1;cursors={}
    assert sorted(order)==list(range(n))
    pred=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(n)]
    for q,i in enumerate(order):
        assert not pred[i]&mask
        cursors[mask]=q;mask^=1<<i
    cursors[0]=n
    @lru_cache(None)
    def f(mask,b):
        assert mask in cursors and type(b) is int and b>=0
        if not mask or not b:return 0
        return min(x[0] for x in choices(mask,b))
    def choices(mask,b):
        assert mask in cursors and mask
        i=order[cursors[mask]];w,p,g,v,r=jobs[i];m=min(v,g+r);d=g+r-m
        child=f(mask^(1<<i),b)
        protected=p+d+child
        cheap=child if b==0 else max(child,w+m+f(mask,b-1))
        cached=d+child if b==0 else d+max(child,w+p+f(mask^(1<<i),b-1))
        return [(protected,0,i,2),(cheap,1,i,1),(cached,2,i,0)]
    def choose(mask,b):
        value,priority,i,mode=min(choices(mask,b));assert value==f(mask,b)
        return value,i,mode
    def paths(mask,b,path='',trace=(),cost=0):
        if not mask:yield path,list(trace),cost;return
        value,i,mode=choose(mask,b);w,p,g,v,r=jobs[i];child=mask^(1<<i)
        if mode==2:
            yield from paths(child,b,path,trace+(f'{i}:P',),cost+w+p+g+r);return
        label='C' if mode==0 else 'V' if v<=g+r else 'A'
        paid=w+g+r if mode==0 else w+min(v,g+r)
        yield from paths(child,b,path+'S',trace+(f'{i}:{label}S',),cost+paid)
        if b:
            yield from paths(child if mode==0 else mask,b-1,path+'F',trace+(f'{i}:{label}F',),cost+paid+(w+p if mode==0 else 0))
    return f,choose,paths

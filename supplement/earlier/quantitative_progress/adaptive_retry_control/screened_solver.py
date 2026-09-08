"""Strengthened baseline: elementary bounds, otherwise unrestricted exact DP."""
import itertools
def bounds(g):
    jobs=g['jobs'];B=g['budget'];blocks=[]
    for p,c in jobs:
        whole,rem=divmod(p,c)
        if whole:blocks.append((c,whole))
        if rem:blocks.append((rem,1))
    left=B;allocation=0
    for h,count in sorted(blocks,reverse=True):
        take=min(left,count);allocation+=h*take;left-=take
        if not left:break
    remaining=sum(p for p,c in jobs);upper=remaining;cut=0;subset=0
    for c,group in itertools.groupby(sorted(jobs,key=lambda x:x[1]),key=lambda x:x[1]):
        premiums=sum(p for p,d in group);subset=max(subset,min(remaining,B*c));remaining-=premiums
        if remaining+B*c<upper:upper=remaining+B*c;cut=c
    return dict(allocation_lower=allocation,subset_lower=subset,lower=max(allocation,subset),upper=upper,static_cut=cut)
def solve(g):
    bnd=bounds(g);n=len(g['jobs']);B=g['budget'];base=sum(g['normal_costs'])
    if bnd['lower']==bnd['upper']:
        return dict(value=base+bnd['upper'],screening_closed=True,bounds=bnd,controller=dict(order=list(range(n)),protected=[c>bnd['static_cut'] for p,c in g['jobs']]))
    if n<=18:
        size=1<<n;previous=[0]*size
        for b in range(1,B+1):
            current=[0]*size
            for mask in range(1,size):
                bits=mask;best=None
                while bits:
                    bit=bits & -bits;i=bit.bit_length()-1;bits-=bit;p,c=g['jobs'][i];child=current[mask^bit]
                    value=min(p+child,max(child,c+previous[mask]));best=value if best is None else min(best,value)
                current[mask]=best
            previous=current
        v=previous[-1];stats=dict(evaluated_cells=(size-1)*B+size)
    else:
        import sys
        from pathlib import Path
        sys.setrecursionlimit(10000);sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
        from adaptive_retry_budget import exact
        v,states=exact(g['jobs'],B);stats=dict(constructed_states=states)
    assert bnd['lower']<=v<=bnd['upper']
    return dict(value=base+v,screening_closed=False,bounds=bnd,**stats)

"""Exploratory exact rational/integer phase-game DP. No native execution."""
from functools import lru_cache


def values(cp, edges, max_r):
    n=len(cp);parents=[0]*n
    for a,b in edges:parents[b]|=1<<a
    all_mask=(1<<n)-1
    def ready(mask):return [i for i in range(n) if mask>>i&1 and not parents[i]&mask]
    def changed(r,z):
        # Each legal nonempty sequence of alternating clock boundaries changes consistency.
        out=[];left=r;phase=z
        while phase or left:
            if phase:phase=0
            else:left-=1;phase=1
            out.append((left,phase))
        return out
    @lru_cache(None)
    def full(mask,r,z):
        if not mask:return 0
        options=[]
        for i in ready(mask):
            w,p=cp[i];child=mask^(1<<i)
            options.append(p+full(child,r,0))
            choices=[full(child,r,z)]+[w+full(mask,rr,zz) for rr,zz in changed(r,z)]
            options.append(max(choices))
        return min(options)
    @lru_cache(None)
    def simple(mask,r,z):
        if not mask:return 0
        options=[]
        for i in ready(mask):
            w,p=cp[i];child=mask^(1<<i)
            options.append(p+simple(child,r,0))
            failure=[w+simple(mask,r-1,1)] if z==0 and r>0 else [w+simple(mask,r,0)] if z else []
            options.append(max([simple(child,r,z)]+failure))
        return min(options)
    bad=[]
    table={}
    for mask in range(1<<n):
        for r in range(max_r+1):
            a,b=full(mask,r,0),full(mask,r,1)
            if (a,b)!=(simple(mask,r,0),simple(mask,r,1)):bad.append(('recurrence',mask,r,a,b))
            if a>b:bad.append(('phase_order',mask,r,a,b))
            if r and full(mask,r-1,1)>a:bad.append(('interlace',mask,r))
            table[mask,r,0]=a;table[mask,r,1]=b
    return {'full':full,'simple':simple,'table':table,'violations':bad,'root':[(r,full(all_mask,r,0),full(all_mask,r,1)) for r in range(max_r+1)],'ready':ready}


if __name__=='__main__':
    import datetime,hashlib,json
    from pathlib import Path
    P=Path(__file__).resolve().parent;cases=[]
    for lam in (1,3,10):
        out=values([(4,4*lam),(104,104*lam)],[(0,1)],6)
        cases.append({'lambda':lam,'root_residuals':out['root'],'violations':out['violations'],'states_checked':len(out['table'])})
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'classification':'three fixed source-price profiles; exploratory finite DP only','program_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':cases}
    with (P/'DP_CHECK01.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))

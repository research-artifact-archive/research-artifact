"""Bounded checks of proof inequalities, separate from constructing scalar DP."""
import collections,itertools
import primitive
def subsets(mask):
    sub=mask
    while True:
        yield sub
        if not sub:break
        sub=(sub-1)&mask
def check(case):
    cp=case['cp'];n=len(cp);B=case['budget'];v=primitive.scalar(cp,case['edges'],B)
    pred=[sum(1<<a for a in ps) for ps in primitive.predecessors(n,case['edges'])]
    counts=collections.Counter()
    for mask in range(1<<n):
        avail=[i for i in range(n) if mask>>i&1 and not pred[i]&mask]
        available_mask=sum(1<<i for i in avail)
        for b in range(B+1):
            for small in subsets(mask):
                assert v[b][small]<=v[b][mask],('subset',mask,small,b)
                counts['subset_monotonicity']+=1
            for chosen in subsets(available_mask):
                outcomes=[]
                for failed in subsets(chosen):
                    spent=failed.bit_count()
                    if spent<=b:
                        remainder=(mask^chosen)|failed
                        outcomes.append(sum(c for i,(c,p) in enumerate(cp) if failed>>i&1)+v[b-spent][remainder])
                assert v[b][mask]<=max(outcomes),('one_pass',mask,chosen,b)
                counts['one_pass']+=1
            if b and avail:
                costs={i:max(v[b][mask^(1<<i)],cp[i][0]+v[b-1][mask]) for i in avail}
                cheapest=min(cp[i][0] for i in avail)
                for i in avail:
                    if cp[i][0]==cheapest:
                        for j in avail:
                            assert costs[i]<=costs[j],('cheapest_fast',mask,b,i,j)
                            counts['cheapest_fast']+=1
                for i in avail:
                    child=mask^(1<<i)
                    bound=max(v[b][child],cp[i][0]+cp[i][1]+v[b-1][child])
                    assert v[b][mask]<=bound,('cached_fallback',mask,b,i)
                    counts['cached_fallback']+=1
            if b:
                assert v[b][mask]>=v[b-1][mask],('budget_monotonicity',mask,b)
                counts['budget_monotonicity']+=1
            if 0<b<B:
                assert v[b][mask]-v[b-1][mask]>=v[b+1][mask]-v[b][mask],('concavity',mask,b)
                counts['concavity']+=1
    return dict(counts)

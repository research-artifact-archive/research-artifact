"""B1 exact DP with inherited allocation bounds and fixed-order incumbents."""
from functools import lru_cache
import certificate


def solve(case):
    pred,_=certificate.validate_case(case);cp=case['cp'];n=len(cp)
    pm=[sum(1<<j for j in xs) for xs in pred]
    stats=dict(closed_by_bounds=0,expanded=0,pruned_actions=0,child_calls=0)
    def available(mask):return [i for i in range(n) if mask>>i&1 and not pm[i]&mask]
    @lru_cache(None)
    def lower(mask):return max((min(c,p) for i,(c,p) in enumerate(cp) if mask>>i&1),default=0)
    def fixed(mask,key):
        order=[];pending=mask
        while pending:
            i=min(available(pending),key=key);order.append(i);pending^=1<<i
        value=0;cert=[]
        for i in reversed(order):
            c,p=cp[i];v,mode=min((p+value,'P'),(max(c,value),'F'))
            cert.append((i,mode));value=v
        return value,tuple(reversed(cert))
    @lru_cache(None)
    def value(mask):
        if not mask:return 0,()
        best,cert=min(fixed(mask,lambda i:(cp[i][0],i)),fixed(mask,lambda i:i))
        lb=lower(mask);assert lb<=best
        if lb==best:
            stats['closed_by_bounds']+=1;return best,cert
        stats['expanded']+=1;avail=available(mask);fast=min(avail,key=lambda i:(cp[i][0],i))
        actions=[]
        for i in avail:
            child=mask^(1<<i);cl=lower(child)
            actions.append((cp[i][1]+cl,i,'P'))
            if i==fast:actions.append((max(cp[i][0],cl),i,'F'))
        for estimate,i,mode in sorted(actions):
            if estimate>=best:stats['pruned_actions']+=1;continue
            stats['child_calls']+=1;cv,cc=value(mask^(1<<i))
            q=cp[i][1]+cv if mode=='P' else max(cp[i][0],cv)
            if q<best:best=q;cert=((i,mode),)+cc
            if best==lb:break
        return best,cert
    v,cert=value((1<<n)-1);cert=[list(x) for x in cert]
    report=certificate.scan(case,cert);assert report['value']==v
    stats.update(states=value.cache_info().currsize,cache_hits=value.cache_info().hits)
    return dict(status='SUCCESS',value=v,certificate=cert,certificate_report=report,stats=stats)

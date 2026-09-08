"""Exact specified-budget DP, inherited bounds and fixed-order incumbents."""
from functools import lru_cache
import checker

def solve(case,budget=2):
    pred=checker.validate(case);cp=case['cp'];n=len(cp);pm=[sum(1<<j for j in ps) for ps in pred]
    stats=dict(closed_by_bounds=0,expanded=0,pruned_actions=0);nodes={}
    def key(mask,b):return f'{mask}:{b}'
    def available(mask):return [i for i in range(n) if mask>>i&1 and not pm[i]&mask]
    @lru_cache(None)
    def lower(mask,b):
        chunks=[]
        for i,(c,p) in enumerate(cp):
            if mask>>i&1:
                q,r=divmod(p,c)
                if q:chunks.append((c,q))
                if r:chunks.append((r,1))
        value=0;left=b
        for h,m in sorted(chunks,reverse=True):
            used=min(left,m);value+=h*used;left-=used
        return value
    def fixed(mask,b,choose):
        order=[];pending=mask
        while pending:
            i=min(available(pending),key=choose);order.append(i);pending^=1<<i
        f=[[0]*(b+1) for _ in range(len(order)+1)];modes=[[] for _ in order]
        for k in range(len(order)-1,-1,-1):
            i=order[k];c,p=cp[i]
            for t in range(1,b+1):
                f[k][t],mode=min((p+f[k+1][t],'P'),(max(f[k+1][t],c+f[k][t-1]),'F'))
                modes[k].append(mode)
        return f[0][b],order,modes
    @lru_cache(None)
    def value(mask,b):
        nodekey=key(mask,b)
        if not mask or not b:
            nodes[nodekey]=dict(kind='zero',mask=mask,budget=b);return 0
        best,order,modes=min(fixed(mask,b,lambda i:(cp[i][0],i)),fixed(mask,b,lambda i:i))
        node=dict(kind='fixed',mask=mask,budget=b,order=order,modes=modes)
        lb=lower(mask,b);assert lb<=best
        if lb==best:
            stats['closed_by_bounds']+=1;nodes[nodekey]=node;return best
        stats['expanded']+=1;avail=available(mask);fast=min(avail,key=lambda i:(cp[i][0],i));actions=[]
        for i in avail:
            child=mask^(1<<i);cl=lower(child,b)
            actions.append((cp[i][1]+cl,i,'P'))
            if i==fast:actions.append((max(cl,cp[i][0]+lower(mask,b-1)),i,'F'))
        for estimate,i,mode in sorted(actions):
            if estimate>=best:stats['pruned_actions']+=1;continue
            child=mask^(1<<i);cv=value(child,b)
            if mode=='P':q=cp[i][1]+cv
            else:
                if max(cv,cp[i][0]+lower(mask,b-1))>=best:stats['pruned_actions']+=1;continue
                q=max(cv,cp[i][0]+value(mask,b-1))
            if q<best:
                best=q;node=dict(kind='choice',mask=mask,budget=b,job=i,mode=mode,success=key(child,b))
                if mode=='F':node['failure']=key(mask,b-1)
            if best==lb:break
        nodes[nodekey]=node;return best
    full=(1<<n)-1;v=value(full,budget);root=key(full,budget);needed=set();stack=[root]
    while stack:
        k=stack.pop()
        if k in needed:continue
        needed.add(k);node=nodes[k]
        if node['kind']=='choice':
            stack.append(node['success'])
            if node['mode']=='F':stack.append(node['failure'])
    artifact=dict(schema='specified-budget-screened-policy-v1',budget=budget,root=root,nodes={k:nodes[k] for k in sorted(needed)})
    stats.update(states=value.cache_info().currsize,cache_hits=value.cache_info().hits,policy_nodes=len(needed))
    return dict(status='SUCCESS',value=v,artifact=artifact,stats=stats)

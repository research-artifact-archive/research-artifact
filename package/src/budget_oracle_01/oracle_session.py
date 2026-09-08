"""Memoized concave-peak value oracle; inherits the DAG curve and bound theorems."""
from pathlib import Path
from functools import lru_cache
import heapq,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'dependency_hybrid_01'))
import hybrid

def make_oracle(case):
    cp=case['cp'];n=len(cp);hybrid.order_if_compatible(case)
    pred=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(n)]
    memo={};packs={};all_nodes={};stats=dict(search_nodes=0,bound_nodes=0,packed_nodes=0,peak_probes=0,cache_hits=0)
    def key(mask,b):return f'{mask}:{b}'
    @lru_cache(None)
    def structure(mask):
        jobs=[i for i in range(n) if mask>>i&1]
        available=[i for i in jobs if not pred[i]&mask]
        mapping={i:j for j,i in enumerate(jobs)}
        sub=dict(cp=[cp[i] for i in jobs],edges=[[mapping[u],mapping[v]] for u,v in case['edges'] if u in mapping and v in mapping])
        order=hybrid.order_if_compatible(sub)
        return jobs,available,sub,order
    @lru_cache(None)
    def bounds_data(mask):
        jobs,_,_,_=structure(mask);chunks=[]
        for i in jobs:
            c,p=cp[i];q,r=divmod(p,c)
            if q:chunks.append((c,q))
            if r:chunks.append((r,1))
        return sorted(chunks,reverse=True),sorted({0}|{cp[i][0] for i in jobs})
    def bounds(mask,b):
        chunks,thresholds=bounds_data(mask);left=b;lower=0
        for height,count in chunks:
            used=min(left,count);lower+=used*height;left-=used
            if not left:break
        upper,t=min((sum(cp[i][1] for i in range(n) if mask>>i&1 and cp[i][0]>t)+b*t,t) for t in thresholds)
        assert lower<=upper
        return lower,upper,t
    def value(mask,b):
        k0=key(mask,b)
        if k0 in memo:stats['cache_hits']+=1;return memo[k0]
        base=dict(mask=mask,budget=b)
        if not mask or not b:v=0;node=dict(**base,kind='zero',value=0)
        else:
            low,up,t=bounds(mask,b)
            if low==up:v=low;node=dict(**base,kind='bound',value=v,threshold=t);stats['bound_nodes']+=1
            else:
                jobs,available,sub,order=structure(mask)
                if order is not None:
                    if str(mask) not in packs:packs[str(mask)]=hybrid.compile_case(sub)
                    v=hybrid.value(packs[str(mask)],b);node=dict(**base,kind='packed',value=v);stats['packed_nodes']+=1
                else:
                    stats['search_nodes']+=1;i=min(available,key=lambda j:(cp[j][0],j));child=mask^(1<<i);c=cp[i][0]
                    h=min(cp[j][1]+value(mask^(1<<j),b) for j in available)
                    lo,hi=0,b+1
                    while hi-lo>1:
                        mid=(lo+hi)//2;stats['peak_probes']+=1
                        slope=value(child,mid)-value(child,mid-1)
                        if slope>=c:lo=mid
                        else:hi=mid
                    peak=lo;g=value(child,peak)
                    if peak:value(child,peak-1)
                    if peak<b:value(child,peak+1)
                    v=min(h,g+c*(b-peak));node=dict(**base,kind='peak',value=v,job=i,peak=peak)
        memo[k0]=v;all_nodes[k0]=node;return v
    def query(budget):
        assert type(budget) is int and budget>=0
        full=(1<<n)-1;v=value(full,budget);root=key(full,budget)
        def dependencies(node):
            if node['kind']!='peak':return []
            mask,b,i,k=node['mask'],node['budget'],node['job'],node['peak'];_,available,_,_=structure(mask)
            deps=[key(mask^(1<<j),b) for j in available];child=mask^(1<<i)
            deps+=[key(child,k)]
            if k:deps+=[key(child,k-1)]
            if k<b:deps+=[key(child,k+1)]
            return deps
        needed=set();todo=[root];needed_packs=set()
        while todo:
            name=todo.pop()
            if name in needed:continue
            needed.add(name);node=all_nodes[name];todo.extend(dependencies(node))
            if node['kind']=='packed':needed_packs.add(str(node['mask']))
        artifact=dict(schema='dag-budget-value-certificate-v1',input=case,budget=budget,root=root,root_value=v,nodes={k:all_nodes[k] for k in sorted(needed)},packed={k:packs[k] for k in sorted(needed_packs)})
        stats.update(memo_states=len(memo),certificate_nodes=len(needed),packed_masks=len(packs),certificate_packed_masks=len(needed_packs))
        return dict(status='SUCCESS',value=v,artifact=artifact,stats=dict(stats))
    return query

def solve_many(case,budgets):
    assert type(budgets) is list and budgets
    query=make_oracle(case);results=[query(b) for b in budgets];nodes={};packed={}
    for r in results:
        for k,v in r['artifact']['nodes'].items():
            if k in nodes:assert nodes[k]==v
            nodes[k]=v
        for k,v in r['artifact']['packed'].items():
            if k in packed:assert packed[k]==v
            packed[k]=v
    artifact=dict(schema='dag-budget-values-certificate-v1',input=case,budgets=budgets,values=[r['value'] for r in results],nodes={k:nodes[k] for k in sorted(nodes)},packed={k:packed[k] for k in sorted(packed)})
    return dict(status='SUCCESS',values=artifact['values'],artifact=artifact,stats=results[-1]['stats'],query_stats=[r['stats'] for r in results])

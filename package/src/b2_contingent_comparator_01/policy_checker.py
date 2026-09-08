"""Evaluate emitted screened-DP policy without its solver or bounds."""
from functools import lru_cache

def check(case,artifact):
    cp=case['cp'];n=len(cp);pred=[{u for u,v in case['edges'] if v==i} for i in range(n)]
    full=(1<<n)-1;B=artifact['budget'];nodes=artifact['nodes']
    assert artifact['schema']=='specified-budget-screened-policy-v1' and type(B) is int and B>=0
    assert artifact['root']==f'{full}:{B}'
    def topological(order,mask):
        assert len(order)==mask.bit_count();done={i for i in range(n) if not mask>>i&1}
        for i in order:
            assert type(i) is int and 0<=i<n and i not in done and pred[i]<=done;done.add(i)
        assert len(done)==n
    @lru_cache(None)
    def visit(mask,b):
        node=nodes[f'{mask}:{b}'];assert node['mask']==mask and node['budget']==b
        if node['kind']=='zero':assert not mask or b==0;return 0
        assert mask and b>0
        if node['kind']=='fixed':
            order=node['order'];modes=node['modes'];topological(order,mask)
            assert len(modes)==len(order) and all(len(row)==b and all(m in ('F','P') for m in row) for row in modes)
            @lru_cache(None)
            def follow(k,t):
                if k==len(order) or t==0:return 0
                i=order[k];c,p=cp[i]
                if modes[k][t-1]=='P':return p+follow(k+1,t)
                return max(follow(k+1,t),c+follow(k,t-1))
            return follow(0,b)
        assert node['kind']=='choice';i=node['job'];mode=node['mode']
        assert type(i) is int and 0<=i<n and mask>>i&1 and not any(mask>>u&1 for u in pred[i])
        child=mask^(1<<i);assert node['success']==f'{child}:{b}'
        normal=visit(child,b)
        if mode=='P':assert 'failure' not in node;return cp[i][1]+normal
        assert mode=='F' and node['failure']==f'{mask}:{b-1}'
        return max(normal,cp[i][0]+visit(mask,b-1))
    answer=visit(full,B);return dict(value=answer,visited_policy_nodes=visit.cache_info().currsize)

"""Preserve cost-compatible packing, add forced-order persistent compilation.

The general ideal compiler remains unchanged. Selection uses only input
structure/prices, not benchmark IDs or recorded outcomes. Verification takes
decoded JSON before load(); ideal execution uses load() as in the prior API.
"""
from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parent;S=ROOT.parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec)
    sys.modules[name]=obj;spec.loader.exec_module(obj);return obj
prior=module('dispatch_prior_hybrid',S/'dependency_hybrid_01/hybrid.py')
persistent=module('dispatch_persistent_order',S/'fixed_order_profile_02/persistent.py')
cap_check=module('dispatch_shared_cap',ROOT/'checker.py')
packed_check=module('dispatch_prior_packed_check',S/'dependency_hybrid_check_02/check.py')
sweep_check=module('dispatch_prior_sweep_check',S/'sweep_certificate_02/certificate.py')


def select(case):
    order=prior.order_if_compatible(case)  # Also validates the complete input.
    if order is not None:return 'ordered',order
    n=len(case['cp']);children=[[] for _ in range(n)];degree=[0]*n
    for a,b in case['edges']:children[a].append(b);degree[b]+=1
    ready=[i for i,d in enumerate(degree) if d==0];order=[]
    while ready:
        if len(ready)!=1:return 'ideal',None
        job=ready.pop();order.append(job)
        for other in children[job]:
            degree[other]-=1
            if degree[other]==0:ready.append(other)
    assert len(order)==n  # The prior validator already rejected cycles.
    return 'persistent_order',order


def compile_case(case):
    route,order=select(case)
    if route=='ordered':return prior.pack(case,order)
    if route=='persistent_order':return persistent.compile_case(case,order)
    data=prior.curves.compile_case(case);data['route']='ideal';return data


def check(data):
    route,order=select(data['input'])
    assert data['route']==route,('input_route_mismatch',data['route'],route)
    if 'normal_cost' in data:
        assert type(data['normal_cost']) is int
        assert data['normal_cost']==sum(c for c,p in data['input']['cp'])
    if route=='ordered':return packed_check.check(data)
    if route=='persistent_order':
        assert data['order']==order
        result=cap_check.check(data)
        stats=data['stats']
        assert isinstance(stats,dict) and set(stats)=={'allocated_nodes','construction_steps','serialized_nodes','root_runs'}
        assert all(type(x) is int and x>=0 for x in stats.values())
        assert stats['serialized_nodes']==len(data['nodes'])
        root=data['roots'][0]
        assert stats['root_runs']==(0 if root==-1 else data['nodes'][root][9])
        assert stats['allocated_nodes']>=stats['serialized_nodes']
        result['generation_counters_not_certified']=['allocated_nodes','construction_steps']
        return result
    return sweep_check.check(data)


def load(data):return prior.load(data)
def value(data,budget):
    return (persistent if data['route']=='persistent_order' else prior).value(data,budget)
def choose(data,state,budget):
    return (persistent if data['route']=='persistent_order' else prior).choose(data,state,budget)

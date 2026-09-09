"""Charged wrapper around the unchanged zero-fee root-cap packing constructor."""
from pathlib import Path
import importlib.util,sys

HERE=Path(__file__).resolve().parent
SCHEMA='charged-atomic-policy-v1'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def isolated_dependency(name,dep,consumer_name,consumer):
    previous=sys.modules.get(name);sys.modules[name]=dep
    try:return module(consumer_name,consumer)
    finally:
        if previous is None:sys.modules.pop(name,None)
        else:sys.modules[name]=previous

old_curves=module('_charged_compact_inherited_curves',HERE/'inherited/dependency_curves_01/curves.py')
packing=isolated_dependency('curves',old_curves,'_charged_compact_packing',HERE/'inherited/dependency_hybrid_01/hybrid.py')
GENERAL=None

def general_constructor():
    global GENERAL
    if GENERAL is None:
        p=HERE.parent/'charged_curves_02'
        compiler=module('_charged_compact_general_compiler',p/'compiler.py')
        GENERAL=isolated_dependency('compiler',compiler,'_charged_compact_general_basis',p/'basis.py')
    return GENERAL

def validate(case):
    if type(case) is not dict or set(case)!={'jobs','edges'}:raise ValueError('expected jobs and edges only')
    jobs,edges=case['jobs'],case['edges']
    if type(jobs) is not list or not jobs:raise ValueError('nonempty job list required')
    if not all(type(row) is list and len(row)==5 and all(type(x) is int and x>=0 for x in row) and row[0]>0 for row in jobs):raise ValueError('jobs require integer [w>0,p>=0,g>=0,v>=0,r>=0]')
    n=len(jobs)
    if type(edges) is not list or not all(type(e) is list and len(e)==2 and all(type(x) is int and 0<=x<n for x in e) and e[0]!=e[1] for e in edges):raise ValueError('malformed dependency edge')
    if len(set(map(tuple,edges)))!=len(edges):raise ValueError('duplicate dependency edge')
    return jobs,edges

def compile_case(case,force_general=False):
    jobs,edges=validate(case)
    separable=all(p==0 or v>=g+r for w,p,g,v,r in jobs)
    baseline=sum(w+min(v,g+r) for w,p,g,v,r in jobs)
    if separable and not force_general:
        effective=dict(cp=[[w+min(v,g+r) if v<g+r else min(w+g+r,w+p),p+max(0,g+r-v)] for w,p,g,v,r in jobs],edges=edges)
        order=packing.order_if_compatible(effective)
        if order is not None:
            backend=packing.pack(effective,order)
            return dict(schema=SCHEMA,input=case,route='compatible_reduced',baseline=baseline,
                        entry=dict(kind='cursor',value=0),backend=backend)
    backend=general_constructor().compile_case(case)
    return dict(schema=SCHEMA,input=case,route='charged_all_ideals',baseline=baseline,
                entry=dict(kind='mask',value=(1<<len(jobs))-1),backend=backend)

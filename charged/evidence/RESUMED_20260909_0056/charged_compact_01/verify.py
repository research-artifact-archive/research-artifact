"""Original-input binding and inherited equation checks; imports no constructor."""
from pathlib import Path
import importlib.util,json

HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
root_cap=module('_charged_compact_root_cap_checker',HERE/'inherited/dependency_hybrid_check_02/check.py')
general=module('_charged_compact_general_checker',HERE.parent/'charged_curves_02/checker.py')

def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON object key: '+key)
        result[key]=value
    return result
def loads(text):return json.loads(text,object_pairs_hook=unique_object)
def numeric_keys(table):
    assert type(table) is dict
    seen=set()
    for key in table:
        if type(key) is int:assert key>=0;number=key
        else:
            assert type(key) is str and key and key.isascii() and key.isdecimal()
            number=int(key);assert str(number)==key,'noncanonical numeric key'
        assert number not in seen,'numeric alias';seen.add(number)

def check(data,expected_input=None):
    if not __debug__:raise RuntimeError('assertions must be enabled')
    assert type(data) is dict and set(data)=={'schema','input','route','baseline','entry','backend'}
    assert data['schema']=='charged-atomic-policy-v1'
    case=data['input'];assert type(case) is dict and set(case)=={'jobs','edges'}
    jobs,edges=case['jobs'],case['edges'];assert type(jobs) is list and jobs
    assert all(type(row) is list and len(row)==5 and all(type(x) is int and x>=0 for x in row) and row[0]>0 for row in jobs)
    n=len(jobs);assert type(edges) is list
    assert all(type(e) is list and len(e)==2 and all(type(x) is int and 0<=x<n for x in e) and e[0]!=e[1] for e in edges)
    assert len(set(map(tuple,edges)))==len(edges)
    if expected_input is not None:assert case==expected_input,'external input binding differs'
    assert type(data['baseline']) is int and data['baseline']==sum(w+min(v,g+r) for w,p,g,v,r in jobs)
    entry=data['entry'];assert type(entry) is dict and set(entry)=={'kind','value'} and type(entry['value']) is int
    inner=data['backend'];assert type(inner) is dict
    if data['route']=='compatible_zero_delta':
        assert entry==dict(kind='cursor',value=0)
        assert all(v>=g+r for w,p,g,v,r in jobs),'positive delta in compact route'
        effective=[[w+min(g+r,p),p] for w,p,g,v,r in jobs]
        assert inner['input']==dict(cp=effective,edges=edges),'effective input or original dependencies differ'
        checked=root_cap.check(inner)
        # Original charged equations at the cap boundaries. The root-cap
        # equations and ordered-tail lemma justify the intervals between them.
        curve=root_cap.Curve(inner['value_slopes']);remaining=sum(p for w,p,g,v,r in jobs);points=0
        for i in inner['order']:
            w,p,g,v,r=jobs[i];child_cap=remaining-p;c=w+g+r;s=w+p
            u=curve.reaches(child_cap);v=curve.reaches(remaining)
            for b in {0,max(0,u-1),u,u+1,max(0,v-1),v,v+1}:
                own=min(curve.value(b),remaining);child=min(curve.value(b),child_cap)
                if b:
                    q=[p+child,max(child,c+min(curve.value(b-1),remaining)),max(child,s+min(curve.value(b-1),child_cap))]
                else:q=[p,0,0]
                assert own==min(q),'original charged branch differs'
                points+=1
            remaining=child_cap
        assert remaining==0
        return dict(route=data['route'],domain='ALL_NONNEGATIVE_INTEGER_BUDGETS_FOR_CURSOR_SUFFIXES',original_baseline_checked=True,charged_boundary_checks=points,inherited=checked,global_optimality_basis='zero-delta ordered equivalence and compatible-DAG corollary',constructor_imported=False)
    assert data['route']=='charged_all_ideals' and entry==dict(kind='mask',value=(1<<n)-1)
    assert inner['input']==case
    for name in ['curves','actions','bases']:numeric_keys(inner[name])
    for table in inner['bases'].values():numeric_keys(table)
    assert all(type(inner[name]) is int for name in ['full','states','baseline'])
    assert all(all(type(x) is int for x in row) for row in inner['prices'])
    for action in inner['actions'].values():
        assert type(action['fast']) is int and all(type(x) is int for x in action['available'])
    checked=general.check(inner)
    assert inner['baseline']==data['baseline']
    return dict(route=data['route'],domain='ALL_NONNEGATIVE_INTEGER_BUDGETS_FOR_REACHABLE_UNFINISHED_SETS',original_baseline_checked=True,inherited=checked,constructor_imported=False)

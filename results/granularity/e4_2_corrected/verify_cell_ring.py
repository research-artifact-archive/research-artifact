#!/usr/bin/env python3
"""Structural checks only: no solver, and no read of measured outcomes."""
import importlib.util
import itertools
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fixed_paper_witnesses', HERE.parents[1] / 'paper_witnesses' / 'check_witnesses.py')
ref = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ref
spec.loader.exec_module(ref)


def check(a):
    n = a['n']; stations = a['stations']; ordinary = a['ordinary']
    assert stations == [chr(65+i) for i in range(n)]
    assert a['boundaries'] == {'start':'s','stop':'t','precedence':[['s','t']]}
    assert ordinary == a['controllable']
    assert len(a['components']) == n
    cases = 0
    for versions in itertools.product(('old','new'), repeat=n):
        for holder in range(n):
            locals_ = ['h' if i == holder else 'e' for i in range(n)]
            assert any(locals_[i] not in a['components'][i]['transfer'] for i in range(n))
            for event in ordinary:
                target = []
                for i,c in enumerate(a['components']):
                    edges = c[versions[i]]['edges']; alphabet = {e[1] for e in edges}
                    successors = [e[2] for e in edges if e[:2] == [locals_[i],event]] if event in alphabet else [locals_[i]]
                    target.append(successors)
                for outcome in itertools.product(*target):
                    assert outcome.count('h') == 1, (n,versions,locals_,event,outcome)
            cases += 1
    for c in a['components']:
        assert c['transfer'] == {'e':['e']}
        for version in ('old','new'):
            assert set(c[version]['states']) == {'h','e'}
    return {'n':n,'versioned_one_holder_states_checked':cases,'product_conservation':'PASS','simultaneous_empty_transfer_unavailable':'PASS'}


def check_n2(a):
    fixed = ref.cell(False)
    for i,c in enumerate(a['components']):
        for version,v in [('old','o'),('new','n')]:
            actual=c[version]; f=fixed.components[i][v]
            assert set(actual['states']) == set(f.states)
            assert actual['initial'] == f.initial
            assert {e[1] for e in actual['edges']} == set(f.alphabet)
            edges={}
            for source,event,target in actual['edges']:edges.setdefault((source,event),set()).add(target)
            assert edges == {key:set(value) for key,value in f.edges.items()}
        assert {key:tuple(value) for key,value in c['transfer'].items()} == fixed.transfers[i]
    assert tuple(a['ordinary']) == fixed.ordinary
    assert not fixed.uc
    for name,idx in [('one',0),('old',1),('inspect',2)]:
        monitor=a['requirements'][name]
        for state in monitor['states']:
            for event in a['ordinary']+['rho_A','rho_B','s','t']:
                actual=next((t for q,e,t in monitor['changes'] if (q,e)==(state,event)),state)
                expected='E' if state=='E' else fixed.monitor_edges.get((idx,state,event),state)
                assert actual==expected,(name,state,event,actual,expected)
    assert set(map(tuple,a['boundaries']['precedence']))==set(fixed.precedence)
    closure,edges=ref.enumerate_game(fixed)
    assert len(closure)==56 and sum(fixed.safe(q) for q in closure)==26 and sum(fixed.goal(q) for q in closure)==2
    assert sum(bool(ts) for buckets in edges.values() for ts in buckets.values())==139
    return {'fixed_python_physical_and_monitor_primitives':'PASS','fixed_python_full_closure_states':len(closure),'fixed_python_nonempty_buckets':139}

if __name__=='__main__':
    reports=[]
    for n in range(2,11):
        a=json.loads((HERE/'inputs'/f'cell_n{n:02d}.json').read_text()); reports.append(check(a))
        if n==2: n2=check_n2(a)
    print(json.dumps({'status':'PASS','checks':reports,'n2_reference':n2},indent=2))

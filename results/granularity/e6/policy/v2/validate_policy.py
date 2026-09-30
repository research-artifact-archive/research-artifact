#!/usr/bin/env python3
"""Independent explicit endpoint/product and boundary-sequence validation."""
import argparse
import collections
import itertools
import json
from pathlib import Path


def fail(message): raise AssertionError(message)


def transition_index(lts):
    index = collections.defaultdict(set)
    for source, action, target in lts['edges']: index[source, action].add(target)
    return index


def tester_step(tester, state, action):
    changes = {(u, a): v for u, a, v in tester['changes']}
    return changes.get((state, action), state)


def endpoint_check(model, version):
    endpoint = model['endpoints'][version]
    requirements = [r for r in model['requirements'] if r['role'] == version]
    components = [c[version] for c in model['components']]
    indexes = [transition_index(c) for c in components]
    alphabets = [{a for _, a, _ in c['edges']} for c in components]
    controller = endpoint['controller']; ci = transition_index(controller)
    controller_alphabet = {a for _, a, _ in controller['edges']}
    root = (controller['initial'], tuple(c['initial'] for c in components),
            tuple(r['tester']['initial'] for r in requirements))
    queue = collections.deque([root]); reachable = {root}; edges = set()
    while queue:
        source = queue.popleft(); control, physical, states = source
        for r, q in zip(requirements, states):
            assert q not in r['tester']['errors'], (version, source, r['id'])
        enabled = 0
        for action in model['ordinary']:
            if not any(action in alphabet for alphabet in alphabets): continue
            local = [indexes[i][q, action] if action in alphabets[i] else {q}
                     for i, q in enumerate(physical)]
            if not all(local): continue
            choices = ci[control, action] if action in controller_alphabet else {control}
            if not choices:
                assert action in model['controllable'], ('disabled UC', version, action)
                continue
            enabled += 1
            next_testers = tuple(tester_step(r['tester'], q, action) for r, q in zip(requirements, states))
            for target_c, target_p in itertools.product(choices, itertools.product(*local)):
                target = (target_c, target_p, next_testers)
                edges.add((source, action, target))
                if target not in reachable: reachable.add(target); queue.append(target)
        assert enabled, ('deadlocked endpoint', version, source)
    # A declared closed loop uses its controller state as its state identifier.
    declared = {}
    for q, projection in endpoint['projection'].items():
        assert all(tag == version.upper() for tag, _ in projection['physical'])
        declared[q] = (q, tuple(local for _, local in projection['physical']),
                       tuple(projection['testers'][r['id']] for r in requirements))
    expected_edges = {(declared[u], a, declared[v]) for u, a, v in endpoint['lts']['edges']}
    assert set(declared.values()) == reachable, ('endpoint states differ', version)
    assert expected_edges == edges, ('endpoint edges differ', version)
    assert declared[endpoint['lts']['initial']] == root
    return dict(status='PASS', states=len(reachable), edges=len(edges), nonblocking=True,
                uncontrollable_closed=True, safety=True)


def boundary_check(fine, coarse):
    req = next(r for r in fine['requirements'] if r['role'] == 'interval')
    t = req['tester']; actions = ['stop_audit', 'start_audit', 'stop_role', 'start_role']
    commutations = 0
    for a, b in [('stop_audit', 'stop_role'), ('start_audit', 'start_role')]:
        for r in fine['requirements']:
            rt = r['tester']
            for q in rt['states']:
                assert tester_step(rt, tester_step(rt, q, a), b) == tester_step(rt, tester_step(rt, q, b), a)
                commutations += 1
    good, bad = [], []
    for permutation in itertools.permutations(actions):
        state = t['initial']; path = [state]
        for action in permutation:
            state = tester_step(t, state, action); path.append(state)
        (bad if state in t['errors'] else good).append(dict(actions=permutation, states=path))
    assert good and bad
    assert any(x['actions'] == ('start_audit','stop_audit','stop_role','start_role') for x in good)
    merged_t = next(r['tester'] for r in coarse['requirements'] if r['role'] == 'interval')
    all_orders = []
    for order in itertools.permutations(['ablation.merge.stops','ablation.merge.starts']):
        state = merged_t['initial']; path = [state]
        for action in order: state = tester_step(merged_t, state, action); path.append(state)
        assert state in merged_t['errors']
        all_orders.append(dict(actions=order, states=path))
    # Validate each generated simultaneous observation against both sequential orders.
    for q in t['states']:
        for merged, members in [('ablation.merge.stops',['stop_audit','stop_role']),
                                ('ablation.merge.starts',['start_audit','start_role'])]:
            values = {tester_step(t, tester_step(t,q,a),b) for a,b in itertools.permutations(members)}
            assert values == {tester_step(merged_t,q,merged)}
    return dict(status='PASS', commuting_checks=commutations, fine_safe_orders=good,
                fine_unsafe_orders=bad, merged_orders=all_orders)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=Path(__file__).parent)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    fine = json.loads((args.directory/'inputs/policy_2_fine.json').read_text())
    coarse = json.loads((args.directory/'inputs/policy_2_coarse.json').read_text())
    results = dict(status='PASS', endpoint_checks={version:endpoint_check(fine, version) for version in ('old','new')},
                   boundaries=boundary_check(fine,coarse),
                   method='Independent Python explicit synchronous product and all boundary permutations; does not import generator or Java solver.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f: json.dump(results,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in results.items() if k!='boundaries'}))


if __name__=='__main__': main()

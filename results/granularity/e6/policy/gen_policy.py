#!/usr/bin/env python3
"""Policy(2), preregistered v1. Generates without reading solver results."""
import argparse
import copy
import itertools
import json
from pathlib import Path

ACTIONS = ['log_old', 'log_new', 'service', 'access_old', 'access_new']
BOUNDARIES = ['stop_audit', 'start_audit', 'stop_role', 'start_role']
ALL = ACTIONS + ['rho_runtime'] + BOUNDARIES


def lts(initial, states, edges):
    return dict(initial=initial, states=states, edges=edges)


def tester(initial, states, alphabet, changes):
    return dict(initial=initial, states=states, errors=['ERROR'], alphabet=alphabet, changes=changes)


def step(t, q, a):
    for u, b, v in t['changes']:
        if (u, b) == (q, a):
            return v
    return q


def safe(bits):
    ao, an, ro, rn = bits
    return (ao or an) and not (ro and rn)


def bits_name(bits):
    return ''.join(map(str, bits))


def model(coarse=False):
    plant = lts('running', ['running'], [['running', a, 'running'] for a in ACTIONS])
    component = dict(id='runtime', old=plant, new=copy.deepcopy(plant),
                     transfer_action='rho_runtime', transfer={'running': ['running']})
    requirements = []
    for version in ('old', 'new'):
        other = 'new' if version == 'old' else 'old'
        audit = tester('unlogged', ['unlogged', 'logged', 'ERROR'], ALL,
                       [['unlogged', 'log_' + version, 'logged'],
                        ['logged', 'service', 'unlogged'],
                        ['unlogged', 'service', 'ERROR']])
        role = tester('valid', ['valid', 'ERROR'], ALL,
                      [['valid', 'access_' + other, 'ERROR']])
        for kind, t in [('audit', audit), ('role', role)]:
            r = dict(id=version + '_' + kind, role=version, tester=t,
                     update_action=('stop_' if version == 'old' else 'start_') + kind)
            if version == 'new':
                r['activation'] = dict(entries=[dict(physical=[[v, 'running']], tester_state=t['initial'],
                                                     residual_state=t['initial']) for v in ('OLD', 'NEW')])
            requirements.append(r)
    tuples = [q for q in itertools.product((0, 1), repeat=4) if safe(q)]
    changes = []
    index_value = dict(stop_audit=(0, 0), start_audit=(1, 1), stop_role=(2, 0), start_role=(3, 1))
    for q in tuples:
        for action, (i, value) in index_value.items():
            target = list(q); target[i] = value
            changes.append([bits_name(q), action, bits_name(target) if safe(target) else 'ERROR'])
    interval = tester('1010', [bits_name(q) for q in tuples] + ['ERROR'], ALL, changes)
    requirements.append(dict(id='coverage_and_exclusion', role='interval', tester=interval,
                             activation=dict(entries=[dict(physical=[['OLD', 'running']],
                                                           tester_state='1010', residual_state='1010')])))
    endpoints = {}
    for version in ('old', 'new'):
        graph = lts('unlogged', ['unlogged', 'logged'],
                    [['unlogged', 'log_' + version, 'logged'], ['logged', 'service', 'unlogged']] +
                    [[q, 'access_' + version, q] for q in ('unlogged', 'logged')])
        projection = {q: dict(physical=[[version.upper(), 'running']],
                              testers={version + '_audit': q, version + '_role': 'valid'})
                      for q in graph['states']}
        if version == 'new':
            for q in projection: projection[q]['goal_id'] = 'new_' + q
        endpoints[version] = dict(lts=graph, controller=copy.deepcopy(graph), projection=projection)
        if version == 'new': endpoints[version]['loadable'] = graph['states']
    result = dict(schema='fg-ducs-witness-v1', id='policy_2_' + ('coarse' if coarse else 'fine'),
                  family='Policy', parameters=dict(requirement_pairs=2, boundary_grouping='all' if coarse else 'individual'),
                  ordinary=ACTIONS, controllable=ACTIONS, components=[component], requirements=requirements,
                  precedence=[], endpoints=endpoints,
                  metadata=dict(mechanism='M4', contribution='boundary',
                                scope='constructed operationally motivated contract; not a product reproduction',
                                expected_decision='LOSS' if coarse else 'WIN'))
    if coarse:
        mapping = {a: ('ablation.merge.stops' if a.startswith('stop_') else 'ablation.merge.starts')
                   for a in BOUNDARIES}
        groups = {}
        for a in ALL: groups.setdefault(mapping.get(a, a), []).append(a)
        for r in requirements:
            if 'update_action' in r: r['update_action'] = mapping[r['update_action']]
            old = copy.deepcopy(r['tester'])
            r['tester']['alphabet'] = list(groups)
            r['tester']['changes'] = []
            for q in old['states']:
                for a, members in groups.items():
                    target = q
                    for member in members: target = step(old, target, member)
                    if target != q: r['tester']['changes'].append([q, a, target])
        result['generated_contract_mode'] = 'boundaries'
    return result


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, default=Path(__file__).parent / 'inputs')
    args = p.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    for coarse in (False, True):
        data = model(coarse); path = args.output / (data['id'] + '.json')
        contents = json.dumps(data, indent=2) + '\n'
        if path.exists():
            if path.read_text() != contents: raise SystemExit('Refusing to change existing model: ' + str(path))
        else:
            with path.open('x') as f: f.write(contents)
        print(path)


if __name__ == '__main__': main()

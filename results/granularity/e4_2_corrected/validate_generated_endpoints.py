#!/usr/bin/env python3
"""Independent synchronous-product check of the generated endpoint closed loops.

Reads finite input primitives only; never calls the synthesis solver or generator.
"""
from collections import deque
from itertools import product
from pathlib import Path
import argparse
import hashlib
import json


def indexed_lts(lts):
    transitions = {}
    alphabet = set()
    for source, action, target in lts['edges']:
        transitions.setdefault((source, action), set()).add(target)
        alphabet.add(action)
    return transitions, alphabet


def verify(data, version):
    local = [c[version] for c in data['components']]
    plants = [indexed_lts(p) for p in local]
    controller = data['controllers'][version]
    ct, ca = indexed_lts(controller)
    monitor = data['requirements']['old' if version == 'old' else 'inspect']
    updates = {(q, a): t for q, a, t in monitor['changes']}
    actions = set(ca).union(*(alpha for _, alpha in plants))
    initial = (tuple(p['initial'] for p in local), controller['initial'], monitor['initial'])
    seen = {initial}
    todo = deque([initial])
    edges = set()
    while todo:
        state = todo.popleft()
        physical, control, observed = state
        assert physical.count('h') == 1, state
        for action in sorted(actions):
            targets = [trans.get((q, action), set()) if action in alpha else {q}
                       for (trans, alpha), q in zip(plants, physical)]
            controls = ct.get((control, action), set()) if action in ca else {control}
            after = updates.get((observed, action), observed)
            if observed == monitor['error'] or after == monitor['error']:
                continue
            for loc in product(*targets):
                for ctrl in controls:
                    target = (tuple(loc), ctrl, after)
                    edges.add((state, action, target))
                    if target not in seen:
                        seen.add(target)
                        todo.append(target)
    endpoint = data['endpoints'][version]
    names = {}
    for entry in endpoint['states']:
        loc = tuple('h' if i == entry['holder'] else 'e' for i in range(data['n']))
        key = (loc, entry['controller'], entry['old' if version == 'old' else 'inspect'])
        assert key not in names, key
        names[key] = entry['id']
    assert seen == set(names), (data['n'], version, 'endpoint state mismatch', seen ^ set(names))
    actual = {(names[q], a, names[t]) for q, a, t in edges}
    expected = {tuple(e) for e in endpoint['edges']}
    assert actual == expected, (data['n'], version, 'endpoint edge mismatch', actual ^ expected)
    assert names[initial] == endpoint['initial']
    assert all(any(q == state for q, _, _ in edges) for state in seen), 'endpoint deadlock'
    return {'states': len(seen), 'edges': len(edges), 'closed_loop_equality': True,
            'single_product_invariant': True, 'safe_and_nonblocking': True}


def main():
    parser = argparse.ArgumentParser()
    base = Path(__file__).resolve().parent
    parser.add_argument('--inputs', type=Path, default=base / 'inputs')
    parser.add_argument('--output', type=Path, default=base / 'validation/endpoint_products.json')
    args = parser.parse_args()
    rows = []
    for n in range(2, 11):
        path = args.inputs / ('cell_n%02d.json' % n)
        payload = path.read_bytes()
        data = json.loads(payload)
        assert data['n'] == n
        assert all(c['transfer'] == {'e': ['e']} for c in data['components'])
        old = verify(data, 'old')
        new = verify(data, 'new')
        assert old['states'] == n and new['states'] == 2 * n - 1
        rows.append({'n': n, 'input_sha256': hashlib.sha256(payload).hexdigest(),
                     'old': old, 'new': new, 'empty_only_transfer': True})
    result = {'status': 'PASS', 'kind': 'independent_endpoint_product_check_not_synthesis', 'rows': rows}
    text = json.dumps(result, indent=2) + '\n'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and args.output.read_text() != text:
        raise RuntimeError('Refusing to overwrite different validation output')
    args.output.write_text(text)
    print('PASS: all nine old/new endpoint graphs equal their explicit closed-loop products')


if __name__ == '__main__':
    main()

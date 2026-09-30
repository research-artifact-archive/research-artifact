#!/usr/bin/env python3
"""Independent Python reconstruction of endpoint plant/controller/tester products."""
from collections import deque
import hashlib
import itertools
import json
from pathlib import Path
import sys


def edges(lts):
    out = {}
    assert len(lts['states']) == len(set(lts['states'])) and lts['initial'] in lts['states']
    assert len(lts['edges']) == len(set(map(tuple, lts['edges'])))
    for q, action, t in lts['edges']:
        assert q in lts['states'] and t in lts['states']
        out.setdefault((q, action), set()).add(t)
    return out, {a for _, a, _ in lts['edges']}


def monitor(test, q, action):
    target = q
    for before, a, after in test['changes']:
        if (before, a) == (q, action): target = after
    return target


def projection_key(value):
    return tuple((v, q) for v, q in value['physical']), tuple(sorted(value['testers'].items()))


def validate(data, version):
    endpoint = data['endpoints'][version]
    local = [c[version] for c in data['components']]
    transition = [edges(lts) for lts in local]
    controller = endpoint['controller'];control, calphabet = edges(controller)
    requirements = [r for r in data['requirements'] if r['role'] == version]
    req_ids = [r['id'] for r in requirements]
    initial = (tuple(lts['initial'] for lts in local), controller['initial'], tuple(r['tester']['initial'] for r in requirements))
    todo = deque([initial]);seen = {initial};product_edges = set();projected = set()
    tag = version.upper()
    def proj(state): return tuple((tag, q) for q in state[0]), tuple(sorted(zip(req_ids, state[2])))
    while todo:
        state = todo.popleft();projected.add(proj(state));enabled = 0
        for r, q in zip(requirements, state[2]): assert q not in r['tester']['errors'], 'unsafe endpoint'
        for action in data['ordinary']:
            if not any(action in alphabet for _, alphabet in transition): continue
            targets = [t.get((q, action), set()) if action in alphabet else {q}
                       for q, (t, alphabet) in zip(state[0], transition)]
            if not all(targets): continue
            controller_targets = control.get((state[1], action), set()) if action in calphabet else {state[1]}
            if not controller_targets:
                assert action in data['controllable'], 'endpoint disables UC'
                continue
            enabled += 1
            monitors = tuple(monitor(r['tester'], q, action) for r, q in zip(requirements, state[2]))
            for physical in itertools.product(*targets):
                for c in controller_targets:
                    nxt = (physical, c, monitors);product_edges.add((proj(state), action, proj(nxt)))
                    if nxt not in seen: seen.add(nxt);todo.append(nxt)
        assert enabled, 'deadlocked endpoint'
    declared, alphabet = edges(endpoint['lts']);reachable = {endpoint['lts']['initial']};todo = deque(reachable)
    while todo:
        q = todo.popleft()
        for action in alphabet:
            for t in declared.get((q, action), set()):
                if t not in reachable:reachable.add(t);todo.append(t)
    keys = {q:projection_key(endpoint['projection'][q]) for q in reachable}
    assert len(set(keys.values())) == len(keys), 'noninjective endpoint projection'
    assert keys[endpoint['lts']['initial']] == proj(initial), 'initial projection differs'
    assert set(keys.values()) == projected, 'reachable product states differ'
    actual_edges = {(keys[q], a, keys[t]) for q, a, t in endpoint['lts']['edges'] if q in reachable}
    assert actual_edges == product_edges, 'closed-loop transition relation differs'
    if version == 'new': assert set(endpoint['loadable']) <= reachable
    return dict(product_states=len(seen), projected_states=len(projected), edges=len(product_edges), safe=True, nonblocking=True)


def main():
    family = Path(sys.argv[1]).resolve();records = []
    try: import jsonschema
    except ImportError: jsonschema = None
    schema = json.loads((Path(__file__).resolve().parents[1] / 'common/witness.schema.json').read_text())
    for path in sorted((family / 'inputs').glob('*.json')):
        data = json.loads(path.read_text())
        if jsonschema: jsonschema.Draft202012Validator(schema).validate(data)
        for r in data['requirements']:
            test = r['tester'];assert len(test['states']) == len(set(test['states']))
            assert set(test['errors']) <= set(test['states']) and test['initial'] not in test['errors']
            assert len({(q,a) for q,a,t in test['changes']}) == len(test['changes'])
            for q,a,t in test['changes']:
                assert q in test['states'] and t in test['states'] and a in test['alphabet']
                assert q not in test['errors'] or t in test['errors']
            for entry in r.get('activation', {}).get('entries', []):
                assert entry['tester_state'] in test['states'] and entry['tester_state'] not in test['errors']
                assert len(entry['physical']) == len(data['components'])
                for (version,q), component in zip(entry['physical'], data['components']): assert q in component[version.lower()]['states']
        n,m,k = (data['parameters'][key] for key in ('n','m','k'))
        assert len(data['components']) == n and len(data['requirements']) == 1
        assert data['metadata']['group_sizes'] == [min(k,n-i) for i in range(0,n,k)]
        assert all(len(c['old']['states']) == 1 and len(c['new']['states']) == 2 for c in data['components'])
        assert all(q != t for c in data['components'] for q,a,t in c['new']['edges'] if a.startswith('ready_'))
        records.append(dict(input=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            old=validate(data,'old'), new=validate(data,'new')))
    out = family / 'validation/endpoint_products.json';out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(dict(status='PASS', inputs=len(records), json_schema_checked=jsonschema is not None, records=records),f,indent=2);f.write('\n')
    print(json.dumps({'status':'PASS','inputs':len(records),'endpoint_products':len(records)*2,'json_schema_checked':jsonschema is not None}))


if __name__ == '__main__': main()

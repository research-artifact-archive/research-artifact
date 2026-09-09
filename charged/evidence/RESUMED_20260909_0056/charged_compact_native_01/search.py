"""Two-PC feasibility search; all mutable observable state is a prefix function."""
import time
from model import digest


def solve(model, max_states=100000, seconds=2):
    programs = model['programs']
    n = model['n']
    prefixes = []
    for program in programs:
        rows = [dict(alloc=0, logs=0, held=-1, published=[0] * n)]
        for step in program:
            row = dict(rows[-1])
            row['published'] = list(row['published'])
            op = step['op']
            if op == 'alloc':
                row['alloc'] += 1
            elif op == 'log':
                row['logs'] += 1
            elif op == 'lock':
                assert row['held'] == -1
                row['held'] = step['bin']
            elif op == 'unlock':
                assert row['held'] == step['bin']
                row['held'] = -1
            elif op == 'publish':
                row['published'][step['job']] = model['positions'][step['id']]
            rows.append(row)
        prefixes.append(rows)

    def allowed(pcs, actor):
        pc = pcs[actor]
        if pc == len(programs[actor]):
            return False
        step = programs[actor][pc]
        own, other = prefixes[actor][pc], prefixes[1 - actor][pcs[1 - actor]]
        op = step['op']

        def current(job):
            return model['chains'][job][max(own['published'][job], other['published'][job])]

        if op == 'read':
            return current(step['job']) == step['source']
        if op == 'compare':
            return (current(step['job']) == step['before']) == step['match']
        if op == 'publish':
            return current(step['job']) == step['source']
        if op == 'lock':
            return other['held'] != step['bin']
        if op == 'log':
            return step['index'] == n + own['logs'] + other['logs']
        if op == 'alloc':
            return step['id'] == n + own['alloc'] + other['alloc'] + 1
        if op == 'wait':
            return pcs[1 - actor] >= step['other_pc']
        assert op in ('unlock', 'identity_store', 'return', 'submit')
        return True

    start = time.monotonic()
    parents = {(0, 0): None}
    pending = [(0, 0)]
    target = tuple(map(len, programs))
    while pending:
        pcs = pending.pop()
        if pcs == target:
            order = []
            while parents[pcs] is not None:
                previous, actor = parents[pcs]
                order.append(actor)
                pcs = previous
            order.reverse()
            return dict(status='FEASIBLE', visited_states=len(parents), seconds=time.monotonic() - start,
                        certificate=dict(schema='charged-microprogram-path-v1', model_sha256=digest(model),
                                         raw_sha256=model['raw_sha256'], input_sha256=model['input_sha256'],
                                         order=order))
        if len(parents) >= max_states or time.monotonic() - start >= seconds:
            return dict(status='UNKNOWN', reason='state/time resource cap', visited_states=len(parents),
                        seconds=time.monotonic() - start)
        for actor in (0, 1):
            if allowed(pcs, actor):
                successor = list(pcs)
                successor[actor] += 1
                successor = tuple(successor)
                if successor not in parents:
                    parents[successor] = (pcs, actor)
                    pending.append(successor)
    return dict(status='INFEASIBLE', visited_states=len(parents), seconds=time.monotonic() - start,
                reason='exhausted full reachable two-PC product')

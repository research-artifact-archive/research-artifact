"""Explicit state replay of a canonical model path; no search/prefix-state import."""
import hashlib
import json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


def check(model, certificate):
    assert certificate['schema'] == 'charged-microprogram-path-v1'
    assert certificate['model_sha256'] == fingerprint(model)
    assert certificate['raw_sha256'] == model['raw_sha256']
    assert certificate['input_sha256'] == model['input_sha256']
    programs = model['programs']
    pcs = [0, 0]
    current = list(model['initial'])
    next_id = len(current) + 1
    next_log = model['initial_logs']
    locks = {}
    held = [None, None]
    allocated = set(current)
    for actor in certificate['order']:
        assert type(actor) == int and actor in (0, 1)
        assert pcs[actor] < len(programs[actor]), 'step after thread return'
        step = programs[actor][pcs[actor]]
        op = step['op']
        if op == 'wait':
            assert pcs[1 - actor] >= step['other_pc'], 'unfulfilled submit/join ordering'
        elif op == 'lock':
            assert held[actor] is None and step['bin'] not in locks, 'overlapping bin critical sections'
            locks[step['bin']] = actor
            held[actor] = step['bin']
        elif op == 'unlock':
            assert held[actor] == step['bin'] and locks[step['bin']] == actor
            del locks[step['bin']]
            held[actor] = None
        elif op == 'read':
            assert current[step['job']] == step['source'], 'fresh input source differs'
        elif op == 'compare':
            assert held[actor] is not None
            assert (current[step['job']] == step['before']) == step['match'], 'incorrect identity comparison'
        elif op == 'alloc':
            assert step['id'] == next_id and next_id not in allocated, 'AtomicLong allocation order'
            allocated.add(next_id)
            next_id += 1
        elif op == 'log':
            assert step['index'] == next_log, 'observable log order differs'
            assert model['events'][next_log]['id'] in allocated, 'logged unallocated identity'
            next_log += 1
        elif op == 'publish':
            assert held[actor] is not None
            assert current[step['job']] == step['source'] and step['id'] in allocated
            current[step['job']] = step['id']
        elif op == 'identity_store':
            assert held[actor] is not None
        elif op == 'return':
            assert held[actor] is None
        else:
            assert op == 'submit'
        pcs[actor] += 1
    assert pcs == list(map(len, programs)), 'missing micro-operations'
    assert next_log == len(model['events']) and current == model['final'] and not locks
    assert next_id == len({e['id'] for e in model['events']}) + 1
    return dict(micro_steps=len(certificate['order']), all_logs=len(model['events']), allocations=next_id - 1,
                scope='existential finite producer/API-model sequentialization; shared canonical model translation')

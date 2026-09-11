"""Materialize fixed synthetic inputs and source snapshots; NEVER import the target."""
import datetime
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent.parent / 'charged_general_01'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (HERE / 'FREEZE.json').exists(), 'freeze already exists'
    counts = {}
    totals = {'initial_queries': 0, 'initial_actions': 0}
    with (HERE / 'inputs.jsonl').open('x') as out:
        def emit(family, case):
            idx = counts.get(family, 0)
            counts[family] = idx + 1
            case = {'family': family, 'id': f'{family}-{idx:06d}', **case}
            out.write(json.dumps(case, sort_keys=True, separators=(',', ':')) + '\n')

        choices = [('h', h) for h in (0, 1, 3)] + [('q', q) for q in (1, 2, 4)]
        for n in range(5):
            for entries in itertools.product(choices, repeat=n):
                future = [(i, v) for i, (tag, v) in enumerate(entries) if tag == 'h']
                completed = [(i, v) for i, (tag, v) in enumerate(entries) if tag == 'q']
                for k in range(len(completed) + 1):
                    for incurred in range(sum(v for _, v in entries) + 2):
                        emit('initial', dict(future=future, completed=completed, k=k,
                                             incurred=incurred, bodies=[1, 2, 5]))
                        totals['initial_queries'] += len(future) * 3
                        totals['initial_actions'] += len(future) * 9

        for n in range(4):
            for pairs in itertools.product(list(itertools.product((0, 1, 3), (1, 2))), repeat=n):
                emit('policies', dict(future=[(i, h) for i, (h, p) in enumerate(pairs)],
                                     completed=[], k=0, incurred=0,
                                     bodies=[p for h, p in pairs]))

        def fixture(name, f, d, k, ell, bodies=(1, 2, 5), replay=None):
            emit('named', dict(name=name, future=f, completed=d, k=k, incurred=ell,
                               bodies=list(bodies), replay=replay))
        fixture('empty', [], [], 0, 0)
        fixture('empty-unsafe', [], [], 0, 1)
        fixture('empty-future-k-n', [], [(0, 1), (1, 2), (2, 4)], 3, 7)
        fixture('empty-future-k-n-unsafe', [], [(0, 1), (1, 2), (2, 4)], 3, 8)
        fixture('zero-ties-k0', [(0, 0), (1, 0), (2, 0)], [], 0, 0)
        fixture('boundary-ties', [(0, 2), (2, 2)], [(1, 2), (3, 2)], 2, 4)
        fixture('single-completed-unsafe-cache', [(1, 3)], [(0, 2)], 1, 3, (1,))
        fixture('A-two-completed-unsafe-cache', [(2, 3)], [(0, 2), (1, 2)], 1, 3, (1,))
        fixture('A-reachable', [(0, 1), (1, 1), (2, 3)], [], 0, 0, (1,),
                [[0, 1, 'cached', True], [1, 1, 'fresh', None], [2, 1, 'fresh', None]])
        fixture('A-unsafe-initial', [(2, 3)], [(0, 2), (1, 2)], 1, 4, (1,))
        fixture('large-1024-bit', [(0, 2**1024), (3, 2**256)],
                [(1, 2**1024), (2, 2**512 + 1)], 2, 2**1024,
                (1, 2**64, 2**1024 + 7))
        fixture('large-ties-boundary', [(1, 2**256), (3, 0)],
                [(0, 2**256), (2, 2**256)], 2, 2**257,
                (1, 2**256, 2**512))

        valid = dict(future=[[1, 3]], completed=[[0, 2]], k=1, incurred=0)
        def invalid_init(name, **changes):
            emit('invalid', dict(kind='constructor', name=name, **(valid | changes)))
        invalid_init('overlap', future=[[0, 3]])
        invalid_init('gap', future=[[2, 3]])
        invalid_init('negative-id', future=[[-1, 3]])
        invalid_init('string-id', future=[['1', 3]])
        invalid_init('float-id', future=[[1.0, 3]])
        invalid_init('bool-id', future=[[True, 3]])
        invalid_init('completed-bool-id', completed=[[False, 2]])
        invalid_init('completed-float-id', completed=[[0.0, 2]])
        invalid_init('none-id', future=[[None, 3]])
        for field, values in [('fee', [-1, 1.5, True, '3', None]),
                              ('q', [0, -1, 1.5, True, '2', None]),
                              ('k', [-1, 2, 1.0, True, '1', None]),
                              ('incurred', [-1, 1.0, True, '0', None])]:
            for j, value in enumerate(values):
                change = {'future': [[1, value]]} if field == 'fee' else (
                    {'completed': [[0, value]]} if field == 'q' else {field: value})
                invalid_init(f'{field}-{j}', **change)
        for job in [-1, 0, 2, 1.0, True, None, '1']:
            for call in ('limits', 'permissions', 'complete'):
                emit('invalid', dict(kind='action', name=f'{call}-job-{job!r}', **valid,
                     call=call, args=[job, 1] + (['cached', False] if call == 'complete' else [])))
        for body in [0, -1, 1.0, True, None, '1']:
            for call in ('limits', 'permissions', 'complete'):
                emit('invalid', dict(kind='action', name=f'{call}-body-{body!r}', **valid,
                     call=call, args=[1, body] + (['cached', False] if call == 'complete' else [])))
        for mode, outcome in [('other', None), (None, None), ([], None),
                               ('fresh', False), ('fresh', True), ('fresh', 0),
                               ('cached', None), ('cached', 0), ('cached', 1), ('cached', 'bad')]:
            emit('invalid', dict(kind='action', name=f'mode-outcome-{mode!r}-{outcome!r}', **valid,
                                call='complete', args=[1, 1, mode, outcome]))
        for mode, outcome in [('fresh', None), ('cached', False), ('cached', True)]:
            emit('invalid', dict(kind='action', name=f'unsafe-{mode}-{outcome}',
                 **(valid | {'incurred': 4}), call='complete', args=[1, 1, mode, outcome]))

        for n in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
            for profile in ('all_mismatch', 'alternating', 'half_completed_fresh'):
                seed = 11092026 + n
                def nextint():
                    nonlocal seed
                    seed = (1664525 * seed + 1013904223) % 2**32
                    return seed
                fees = [nextint() % 17 for _ in range(n)]
                bodies = [1 + nextint() % 31 for _ in range(n)]
                order = list(range(n))
                for i in range(n - 1, 0, -1):
                    j = nextint() % (i + 1)
                    order[i], order[j] = order[j], order[i]
                d = n // 2 if profile == 'half_completed_fresh' else 0
                completed = [(i, fees[i] + bodies[i]) for i in order[:d]]
                future = [(i, fees[i]) for i in order[d:]]
                k = d // 2
                # Boundary incidence is fixed using literal sorting of input entries only.
                ell = sum(sorted([v for _, v in completed + future], reverse=True)[:k])
                emit('streams', dict(name=f'n{n}-{profile}', profile=profile,
                     future=future, completed=completed, k=k, incurred=ell,
                     bodies=bodies, order=order[d:], outcomes=[True if profile == 'all_mismatch'
                     else (j % 3 != 1) for j in range(n - d)]))

    for name in ['PROOF01.md', 'FILTER_DERIVATION01.md', 'filter01.py']:
        target = HERE / ('target_' + name)
        assert not target.exists()
        shutil.copyfile(SOURCE / name, target)
        assert sha(target) == sha(SOURCE / name), 'source changed while snapshotting'
    names = ['PROTOCOL.md', 'reference.py', 'checker.py', 'run_family.py',
             'generate_and_freeze.py', 'inputs.jsonl', 'target_PROOF01.md',
             'target_FILTER_DERIVATION01.md', 'target_filter01.py']
    manifest = dict(attempt='attempt01', frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    monotonic_ns=time.monotonic_ns(), family_input_counts=counts,
                    planned_initial_totals=totals, files={name: sha(HERE / name) for name in names},
                    sources={name: sha(SOURCE / name) for name in ['PROOF01.md', 'FILTER_DERIVATION01.md', 'filter01.py']},
                    target_executed_before_freeze=False,
                    output_scope=str(HERE.parent), timeout_seconds=270)
    with (HERE / 'FREEZE.json').open('x') as out:
        json.dump(manifest, out, sort_keys=True, indent=2)
    print(json.dumps(manifest, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()

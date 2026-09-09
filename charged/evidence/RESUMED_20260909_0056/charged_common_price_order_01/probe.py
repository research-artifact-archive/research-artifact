from pathlib import Path
from functools import lru_cache
import argparse
import datetime
import hashlib
import itertools
import json
import os
import signal
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
CURVES = HERE.parent / 'charged_curves_02'
sys.path.insert(0, str(CURVES))
import basis
import checker

DEST = HERE / 'attempt01'
STOP = datetime.datetime(2026, 9, 9, 4, 50, tzinfo=datetime.timezone.utc).timestamp()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def scalar(jobs, order=None, cached=True):
    n = len(jobs)

    @lru_cache(None)
    def value(mask, b):
        if not mask or b == 0:
            return 0
        ready = [i for i in range(n) if mask & (1 << i)] if order is None else [next(i for i in order if mask & (1 << i))]
        candidates = []
        for i in ready:
            w, p, g, v, r = jobs[i]
            minimum = min(v, g + r)
            delta = g + r - minimum
            child = mask ^ (1 << i)
            same = value(child, b)
            candidates.append(p + delta + same)
            candidates.append(max(same, w + minimum + value(mask, b - 1)))
            if cached:
                candidates.append(delta + max(same, w + p + value(child, b - 1)))
        return min(candidates)

    return value


def prepare():
    DEST.mkdir(exist_ok=False)
    inputs = []
    for n in (2, 3, 4, 5):
        for weights in itertools.combinations_with_replacement((1, 2, 4, 7), n):
            for numerator in (0, 1, 2, 3, 4, 6, 8, 12, 16):
                for v, k in itertools.product((0, 1, 3, 7), repeat=2):
                    index = len(inputs)
                    jobs = [None] * n
                    for i, work in enumerate(weights):
                        jobs[(i + index) % n] = [4 * work, numerator * work, 0, 4 * v, 4 * k]
                    inputs.append(dict(id=f'common-{index:05d}', n=n, work_multiset=weights,
                                       lambda_numerator=numerator, lambda_denominator=4, unscaled_v=v, unscaled_k=k,
                                       case=dict(jobs=jobs, edges=[])))
    assert len(inputs) == 17424
    save(DEST / 'INPUTS.json', inputs)
    files = [HERE / 'PLAN.md', Path(__file__).resolve(), DEST / 'INPUTS.json']
    files += [CURVES / n for n in ('basis.py', 'compiler.py', 'checker.py')]
    files += [basis.compiler.SOURCE, Path(sys.executable).resolve()]
    save(DEST / 'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), cases=17424,
         scalar_budgets=list(range(9)), scalar_roots_per_solver=156816,
         full_profile_comparisons=17424, controls=['ascending', 'descending', 'omit_cached'],
         expected_control_excess=dict(ascending=8, descending=12, omit_cached=12),
         per_case_seconds=1, total_seconds=240, parent_seconds=270, new_native_executions=0,
         inputs_status='authored exploration, may overlap previous grids, not independent population',
         files={str(p): sha(p) for p in files}))
    print('Fixed17424common-price inputs; no probe outcomes.')


class CaseTimeout(Exception):
    pass


def timeout(*args):
    raise CaseTimeout('fixed one-second case limit')


def worker():
    m = json.loads((DEST / 'MANIFEST.json').read_text())
    for path, digest in m['files'].items():
        assert sha(path) == digest
    save(DEST / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                       manifest_sha256=sha(DEST / 'MANIFEST.json')))
    inputs = json.loads((DEST / 'INPUTS.json').read_text())
    signal.signal(signal.SIGALRM, timeout)
    started = time.monotonic()
    records = []
    with (DEST / 'RAW.jsonl').open('x') as raw, (DEST / 'COUNTEREXAMPLES.jsonl').open('x') as counter:
        for index, item in enumerate(inputs):
            record = dict(id=item['id'])
            if time.monotonic() - started >= 240 or time.time() >= STOP:
                record.update(status='NOT_RUN', reason='campaign cutoff')
            else:
                begin = time.monotonic()
                signal.setitimer(signal.ITIMER_REAL, 1)
                try:
                    case = item['case']
                    jobs = case['jobs']
                    n = len(jobs)
                    full = (1 << n) - 1
                    order = sorted(range(n), key=lambda i: (jobs[i][0], i))
                    chain = dict(jobs=jobs, edges=[list(edge) for edge in zip(order, order[1:])])
                    unrestricted = json.loads(json.dumps(basis.compile_case(case)))
                    fixed = json.loads(json.dumps(basis.compile_case(chain)))
                    checker.check(unrestricted)
                    checker.check(fixed)
                    f = unrestricted['curves'][str(full)]
                    g = fixed['curves'][str(full)]
                    direct = scalar(jobs)
                    prescribed = scalar(jobs, order)
                    f_values = [checker.value(f, b) for b in range(9)]
                    g_values = [checker.value(g, b) for b in range(9)]
                    assert f_values == [direct(full, b) for b in range(9)]
                    assert g_values == [prescribed(full, b) for b in range(9)]
                    probes = sorted({0} | {x + d for x, y, slope in f + g for d in (0, 1)})
                    gaps = [dict(budget=b, adaptive=checker.value(f, b), ordered=checker.value(g, b))
                            for b in probes if checker.value(f, b) != checker.value(g, b)]
                    assert all(gap['adaptive'] < gap['ordered'] for gap in gaps), 'restricted order beats full game'
                    assert bool(gaps) == (f != g), 'canonical profile comparison mismatch'
                    record.update(status='SUCCESS', profiles_equal=not gaps, full_profile=f, ordered_profile=g,
                                  scalar_adaptive=f_values, scalar_ordered=g_values, order=order, gaps=gaps,
                                  seconds=time.monotonic() - begin)
                    if gaps:
                        payload = dict(input=item, result=record, full_certificate=unrestricted, ordered_certificate=fixed)
                        counter.write(json.dumps(payload, separators=(',', ':')) + '\n')
                        counter.flush()
                        if not (DEST / 'FIRST_COUNTEREXAMPLE.json').exists():
                            save(DEST / 'FIRST_COUNTEREXAMPLE.json', payload)
                except CaseTimeout:
                    record.update(status='TIMEOUT', error=traceback.format_exc())
                except Exception:
                    record.update(status='FAILURE', error=traceback.format_exc())
                    if not (DEST / 'FIRST_FAILURE.json').exists():
                        save(DEST / 'FIRST_FAILURE.json', dict(input=item, result=record))
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
            records.append(record)
            raw.write(json.dumps(record, separators=(',', ':')) + '\n')
            raw.flush()
            if (index + 1) % 2000 == 0:
                print(json.dumps(dict(done=index + 1, seconds=time.monotonic() - started,
                                      counterexamples=sum(r.get('profiles_equal') is False for r in records))), flush=True)
    jobs = [[4, 4, 0, 8, 8], [8, 8, 0, 8, 8]]
    controls = []
    for name in m['controls']:
        order = [1, 0] if name == 'descending' else [0, 1]
        value = scalar(jobs, order, cached=name != 'omit_cached')(3, 1)
        controls.append(dict(id=name, excess=value, expected=m['expected_control_excess'][name],
                             expected_result_met=value == m['expected_control_excess'][name]))
    save(DEST / 'CONTROLS.json', controls)
    from collections import Counter
    summary = dict(inputs=17424, statuses=dict(Counter(r['status'] for r in records)),
                   complete_profile_agreements=sum(r.get('profiles_equal') is True for r in records),
                   counterexample_inputs=sum(r.get('profiles_equal') is False for r in records),
                   controls_expected=sum(r['expected_result_met'] for r in controls), controls=3,
                   seconds=time.monotonic() - started, raw_sha256=sha(DEST / 'RAW.jsonl'),
                   inference='Finite observed agreement cannot establish a universal order theorem; verified gap refutes it.')
    save(DEST / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


def run():
    limit = min(270, STOP - time.time())
    assert limit > 0
    argv = [sys.executable, '-B', str(Path(__file__).resolve()), 'worker']
    with (DEST / 'stdout.txt').open('x') as out, (DEST / 'stderr.txt').open('x') as err:
        proc = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
        try:
            code = proc.wait(timeout=limit)
            status = 'COMPLETED' if code == 0 else 'FAILURE'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait()
            status = 'TIMEOUT'
    save(DEST / 'PROCESS.json', dict(status=status, exit_code=code, argv=argv))
    print((DEST / 'stdout.txt').read_text())
    if status != 'COMPLETED':
        print((DEST / 'stderr.txt').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run', 'worker'))
    args = parser.parse_args()
    {'prepare': prepare, 'run': run, 'worker': worker}[args.command]()

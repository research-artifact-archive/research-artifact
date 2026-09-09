"""Fixed charged construction experiment: serial cold processes, full denominator."""
from pathlib import Path
import argparse
import collections
import copy
import datetime
import hashlib
import json
import os
import platform
import signal
import statistics
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
DEST = HERE / 'attempt01'
Q = [1, 2, 4, 8, 16, 32, 64, 256, 4096, 65536, 1 << 32, 1 << 64]
STOP = datetime.datetime(2026, 9, 9, 4, 50, tzinfo=datetime.timezone.utc).timestamp()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def prepare():
    if not __debug__:
        raise RuntimeError('assertions must be enabled')
    cases = []
    for topology in ('chain', 'four_chains', 'fence', 'independent'):
        for n in (8, 12):
            if topology == 'chain':
                edges = [[i, i + 1] for i in range(n - 1)]
            elif topology == 'four_chains':
                edges = [[i, i + 4] for i in range(n - 4)]
            elif topology == 'fence':
                edges = [[i, j] for i in range(0, n, 2) for j in (i - 1, i + 1) if 0 <= j < n]
            else:
                edges = []
            for condition in ('MIXED', 'LONG_PREMIUM', 'WIDE_ALL'):
                jobs = [None] * n
                for i in range(n):
                    w, p, g, r = 2 + i % 5, 3 + (3 * i) % 7, 8 + i % 3, 7 + (2 * i) % 4
                    k = g + r
                    v = k + 1 if i % 3 == 0 else k - 1 if i % 3 == 1 else 1
                    if condition == 'LONG_PREMIUM':
                        p = (1 << 32) * p + i % 7
                    prices = [w, p, g, v, r]
                    if condition == 'WIDE_ALL':
                        prices = [x * (1 << 96) for x in prices]
                    jobs[(5 * i + 3) % n] = prices
                renamed = sorted([[(5 * i + 3) % n, (5 * j + 3) % n] for i, j in edges])
                cases.append(dict(id=f'{topology}-{n}-{condition}', topology=topology, n=n,
                                  condition=condition, case=dict(jobs=jobs, edges=renamed)))
    assert len(cases) == 24
    units = []
    for index, item in enumerate(cases):
        for workload, size in enumerate((1, 4, 12)):
            methods = ['ALL', 'PEAK', 'DP']
            rotate = (index + workload) % 3
            methods = methods[rotate:] + methods[:rotate]
            for method in methods:
                units.append(dict(id=f'{item["id"]}-q{size}-{method}', case_id=item['id'],
                                  method=method, budgets=Q[:size], case=item['case'], seconds_cap=4))
    for item in cases:
        if item['condition'] == 'MIXED':
            units.append(dict(id=f'{item["id"]}-generic', case_id=item['id'], method='GENERIC',
                              budgets=[0, 1, 2, 4], case=item['case'], seconds_cap=10))
    assert len(units) == 224 and sum(len(u['budgets']) for u in units) == 1256
    DEST.mkdir(exist_ok=False)
    (DEST / 'inputs').mkdir()
    save(DEST / 'CASES.json', cases)
    save(DEST / 'UNITS.json', units)
    for unit in units:
        save(DEST / 'inputs' / (unit['id'] + '.json'), unit)
    sources = [HERE / name for name in ('PLAN.md', 'benchmark.py', 'worker.py', 'oracle.py',
                                      'point_checker.py', 'direct.py', 'generic.py')]
    sources += [HERE.parent / 'charged_curves_02' / name for name in ('basis.py', 'compiler.py', 'checker.py')]
    sources += [HERE.parent.parent / 'RESUMED_20260907_1942/dependency_curves_01/curves.py',
                HERE.parent / 'charged_guaranteed_02/explore.py']
    sources += [HERE / 'conformance01' / name for name in ('MANIFEST.json', 'INPUTS.json', 'RAW.jsonl', 'CONTROLS.json', 'SUMMARY.json')]
    sources += [HERE.parent / 'CHARGED_COMPILER_AUTHOR_REPORT_22.md', Path(sys.executable).resolve()]
    sources += list((DEST / 'inputs').glob('*.json')) + [DEST / 'CASES.json', DEST / 'UNITS.json']
    save(DEST / 'MANIFEST.json', dict(schema='charged-compiler-comparison-v1', utc=utc(),
         cases=24, process_units=224, root_requests=1256, main_units=216, generic_units=8,
         main_seconds_cap=4, generic_seconds_cap=10, rss_cap_bytes=1 << 30,
         campaign_seconds_cap=1080, absolute_stop_utc='2026-09-09T04:50:00Z',
         poll_seconds=.005, rss_sample_seconds=.05, measurement='parent cold elapsed including startup and final process termination',
         order='main24 ordered cases; q1,q4,q12; rotatedALL,PEAK,DP; then8MIXEDgeneric',
         python=sys.version, executable=str(Path(sys.executable).resolve()), platform=platform.platform(),
         argv_template=[sys.executable, '-B', str(HERE / 'worker.py'), 'METHOD', 'INPUT', 'OUTPUTDIR'],
         environment_overrides=dict(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1'),
         request_controls=['unchanged_peak', 'reversed_budget', 'wrong_peak_input', 'wrong_all_input'],
         inherited_conformance_cap_defect='The old120sSIGALRM exception was catchable by per-case code; actual.742s run did not trigger it. Main run uses parent hard kills.',
         files={str(path): sha(path) for path in sources}))
    print('Fixed24 cases/224 processes/1256 roots; no main timing observed.')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def controls():
    from worker import bind_certificate
    import oracle
    case = dict(jobs=[[2, 5, 0, 0, 0]], edges=[])
    budgets = [1, 2]
    original = json.loads(json.dumps(oracle.solve_many(case, budgets)['artifact']))
    result = []
    for name in ('unchanged_peak', 'reversed_budget', 'wrong_peak_input', 'wrong_all_input'):
        item = copy.deepcopy(original)
        method = 'ALL' if name == 'wrong_all_input' else 'PEAK'
        if name == 'reversed_budget':
            item['budgets'].reverse()
            item['values'].reverse()
        if name in ('wrong_peak_input', 'wrong_all_input'):
            item['input']['jobs'][0][0] += 1
        try:
            bind_certificate(method, item, case, budgets)
            accepted, error = True, None
        except Exception as exc:
            accepted, error = False, str(exc)
        result.append(dict(id=name, accepted=accepted, expected_accept=name == 'unchanged_peak',
                           passed=accepted == (name == 'unchanged_peak'), error=error))
    save(DEST / 'REQUEST_BINDING_CONTROLS.json', result)
    assert all(r['passed'] for r in result)


def kill(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def run():
    manifest = json.loads((DEST / 'MANIFEST.json').read_text())
    for path, digest in manifest['files'].items():
        assert sha(path) == digest, path
    assert __debug__
    save(DEST / 'RUN_STARTED.json', dict(utc=utc(), manifest_sha256=sha(DEST / 'MANIFEST.json')))
    controls()
    begin = time.monotonic()
    records = []
    units = json.loads((DEST / 'UNITS.json').read_text())
    with (DEST / 'RAW.jsonl').open('x') as raw:
        for index, unit in enumerate(units):
            out = DEST / 'runs' / unit['id']
            out.mkdir(parents=True, exist_ok=False)
            argv = [sys.executable, '-B', str(HERE / 'worker.py'), unit['method'],
                    str(DEST / 'inputs' / (unit['id'] + '.json')), str(out)]
            record = {k: unit[k] for k in ('id', 'case_id', 'method', 'budgets', 'seconds_cap')}
            record.update(argv=argv, utc=utc(), sampled_peak_rss_bytes=0, samples=0)
            if time.monotonic() - begin >= 1080 or time.time() >= STOP:
                record.update(status='NOT_RUN', reason='campaign or absolute cutoff')
            else:
                env = os.environ.copy()
                env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
                started = time.monotonic()
                proc = None
                try:
                    with (out / 'stdout.txt').open('x') as stdout, (out / 'stderr.txt').open('x') as stderr:
                        proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, env=env,
                                                cwd=HERE, start_new_session=True)
                        reason = None
                        next_sample = started + .05
                        while proc.poll() is None:
                            now = time.monotonic()
                            if now - started >= unit['seconds_cap'] or now - begin >= 1080 or time.time() >= STOP:
                                reason = 'TIMEOUT'
                                kill(proc)
                                break
                            if now >= next_sample:
                                sample = subprocess.run(['/bin/ps', '-o', 'rss=', '-p', str(proc.pid)],
                                                        capture_output=True, text=True, timeout=.5)
                                rows = sample.stdout.split()
                                rss = int(rows[0]) * 1024 if rows else 0
                                record['samples'] += 1
                                record['sampled_peak_rss_bytes'] = max(record['sampled_peak_rss_bytes'], rss)
                                next_sample = now + .05
                                if rss > 1 << 30:
                                    reason = 'MEMORY_LIMIT'
                                    kill(proc)
                                    break
                            time.sleep(.005)
                        record.update(cold_seconds=time.monotonic() - started, exit_code=proc.returncode)
                    if reason is None and (record['cold_seconds'] > unit['seconds_cap'] or time.monotonic() - begin > 1080 or time.time() >= STOP):
                        reason = 'TIMEOUT'
                    if reason:
                        record.update(status='TIMEOUT' if reason == 'TIMEOUT' else 'FAILURE', reason=reason)
                    elif proc.returncode != 0:
                        record.update(status='FAILURE', reason='worker_nonzero')
                    elif not (out / 'RESULT.json').is_file():
                        record.update(status='INVALID', reason='missing_worker_result')
                    else:
                        result = json.loads((out / 'RESULT.json').read_text())
                        record['worker_result'] = result
                        assert result['method'] == unit['method'] and result['budgets'] == unit['budgets']
                        assert len(result['values']) == len(unit['budgets'])
                        assert all(type(v) == int and v >= 0 for v in result['values'])
                        if result['process_peak_rss_bytes'] > 1 << 30:
                            record.update(status='FAILURE', reason='MEMORY_LIMIT_IN_FINAL_RUSAGE')
                        else:
                            record['status'] = result['status']
                except Exception:
                    if proc is not None:
                        kill(proc)
                    record.update(status='INVALID', reason=traceback.format_exc(), cold_seconds=time.monotonic() - started)
            save(out / 'PROCESS.json', record)
            records.append(record)
            raw.write(json.dumps(record, separators=(',', ':')) + '\n')
            raw.flush()
            if (index + 1) % 12 == 0 or record['status'] != 'SUCCESS':
                print(json.dumps(dict(done=index + 1, total=len(units), id=unit['id'], status=record['status'],
                                      seconds=time.monotonic() - begin)), flush=True)
    expected = {u['id'] for u in units}
    assert len(records) == len(expected) == 224 and {r['id'] for r in records} == expected
    values = collections.defaultdict(list)
    for record in records:
        if record['status'] == 'SUCCESS':
            for b, v in zip(record['budgets'], record['worker_result']['values']):
                values[record['case_id'], b].append((record['id'], v))
    disagreements = [dict(case_id=key[0], budget=key[1], observed=rows) for key, rows in values.items()
                     if len({v for _, v in rows}) > 1]
    by_method = {}
    for method in ('ALL', 'PEAK', 'DP', 'GENERIC'):
        rows = [r for r in records if r['method'] == method]
        success = [r for r in rows if r['status'] == 'SUCCESS']
        by_method[method] = dict(units=len(rows), statuses=dict(collections.Counter(r['status'] for r in rows)),
            successful_cold_seconds=[r['cold_seconds'] for r in success],
            completed_requested_roots=sum(len(r['budgets']) for r in success),
            maximum_success_rss_bytes=max([r['worker_result']['process_peak_rss_bytes'] for r in success], default=0))
    pairs = []
    lookup = {(r['case_id'], len(r['budgets']), r['method']): r for r in records if r['method'] != 'GENERIC'}
    for case in json.loads((DEST / 'CASES.json').read_text()):
        for size in (1, 4, 12):
            a = lookup[case['id'], size, 'ALL']
            for method in ('PEAK', 'DP'):
                b = lookup[case['id'], size, method]
                row = dict(case_id=case['id'], workload=size, comparator=method,
                           ALL_status=a['status'], comparator_status=b['status'])
                if a['status'] == b['status'] == 'SUCCESS':
                    row.update(ratio_comparator_over_ALL=b['cold_seconds'] / a['cold_seconds'],
                               ALL_seconds=a['cold_seconds'], comparator_seconds=b['cold_seconds'])
                pairs.append(row)
    save(DEST / 'SUMMARY.json', dict(units=224, requested_roots=1256, statuses=dict(collections.Counter(r['status'] for r in records)),
        by_method=by_method, paired_comparisons=pairs, disagreements=disagreements,
        seconds=time.monotonic() - begin, raw_sha256=sha(DEST / 'RAW.jsonl'),
        result_scope='Single cold run per fixed authored workload; methods supply different certificate services.',
        missing_ids=sorted(expected - {r['id'] for r in records})))
    print(json.dumps(dict(units=224, statuses=dict(collections.Counter(r['status'] for r in records)),
                          disagreements=len(disagreements), seconds=time.monotonic() - begin)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run'))
    args = parser.parse_args()
    {'prepare': prepare, 'run': run}[args.command]()

"""Separate pre-timing conformance for new requested-value and scalar adapters."""
from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import json
import random
import signal
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
DEST = HERE / 'conformance01'
CURVES = HERE.parent / 'charged_curves_02'
sys.path.insert(0, str(CURVES))
import basis
import checker
import direct
import generic
import oracle
import point_checker

BUDGETS = [0, 1, 2, 3, 8, 31, 1 << 32]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def prepare():
    DEST.mkdir(exist_ok=False)
    old = HERE.parent / 'charged_callback_native_01/CASES.json'
    observed = json.loads(old.read_text())
    inputs = [dict(id='observed-' + item['id'], provenance='previously observed native input, abstract values only',
                   case={key: item[key] for key in ('jobs', 'edges')}) for item in observed]
    assert len(inputs) == 36
    rng = random.Random(202609090620)
    for n in range(1, 6):
        for repeat in range(8):
            jobs = [[rng.randint(1, 9), rng.randint(0, 15), rng.randint(0, 9),
                     rng.randint(0, 12), rng.randint(0, 9)] for _ in range(n)]
            edges = [[i, j] for i in range(n) for j in range(i + 1, n) if rng.randrange(4) == 0]
            order = list(range(n))
            rng.shuffle(order)
            renamed = [None] * n
            for i, job in enumerate(jobs):
                renamed[order[i]] = job
            inputs.append(dict(id=f'fresh-{n}-{repeat}', provenance='fixed seeded author conformance',
                               case=dict(jobs=renamed, edges=sorted([[order[i], order[j]] for i, j in edges]))))
    assert len(inputs) == 76
    save(DEST / 'INPUTS.json', inputs)
    files = [HERE / name for name in ('oracle.py', 'point_checker.py', 'direct.py', 'generic.py', 'conformance.py')]
    files += [CURVES / name for name in ('basis.py', 'compiler.py', 'checker.py')]
    files += [basis.compiler.SOURCE, generic.SOURCE, old, DEST / 'INPUTS.json']
    save(DEST / 'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                    cases=76, budgets=BUDGETS, point_roots=532, generic_roots=304,
                                    generic_budgets=[0, 1, 2, 3], total_seconds=120,
                                    new_native_executions=0, timing_benchmark_cases=0,
                                    files={str(path): sha(path) for path in files},
                                    controls=['unchanged', 'altered_root', 'missing_cached_child_previous',
                                              'wrong_peak', 'wrong_fast_job', 'negative_input', 'extraneous_node']))
    print('Fixed76 separate conformance inputs and7 certificate controls; no outcomes yet.')


def expired(*args):
    raise TimeoutError('fixed120s conformance cap')


def run():
    manifest = json.loads((DEST / 'MANIFEST.json').read_text())
    for path, digest in manifest['files'].items():
        assert sha(path) == digest
    inputs = json.loads((DEST / 'INPUTS.json').read_text())
    start = time.monotonic()
    save(DEST / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                       manifest_sha256=sha(DEST / 'MANIFEST.json')))
    results = []
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 120)
    try:
        with (DEST / 'RAW.jsonl').open('x') as raw:
            for item in inputs:
                row = dict(id=item['id'])
                try:
                    case = item['case']
                    compiled = json.loads(json.dumps(basis.compile_case(case)))
                    all_check = checker.check(compiled)
                    all_values = [checker.value(compiled['curves'][str(compiled['full'])], b) for b in BUDGETS]
                    points = oracle.solve_many(case, BUDGETS)
                    certificate = json.loads(json.dumps(points['artifact']))
                    point_check = point_checker.check(certificate)
                    scalar = direct.solve_many(case, BUDGETS)
                    general = generic.solve_many(case, [0, 1, 2, 3])
                    assert all_values == point_check['values'] == scalar['values'] == points['values']
                    assert general['values'] == all_values[:4]
                    row.update(status='SUCCESS', values=all_values, all_check=all_check,
                               point_check=point_check, direct_stats=scalar['stats'], generic_stats=general['stats'])
                except Exception:
                    row.update(status='FAILURE', error=traceback.format_exc(), input=item)
                results.append(row)
                raw.write(json.dumps(row, separators=(',', ':')) + '\n')
                raw.flush()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    # Concrete two-job mode-gap certificate, fixed independently of result selection.
    case = dict(jobs=[[3, 2, 0, 0, 0], [1, 1, 1, 3, 1]], edges=[])
    original = json.loads(json.dumps(oracle.solve_many(case, [1])['artifact']))
    assert original['values'] == [2]
    controls = []
    for name in manifest['controls']:
        artifact = copy.deepcopy(original)
        if name == 'altered_root':
            artifact['values'][0] += 1
            artifact['nodes']['3:1']['value'] += 1
        elif name == 'missing_cached_child_previous':
            del artifact['nodes']['1:0']
        elif name == 'wrong_peak':
            assert artifact['nodes']['3:1']['peak'] == 0
            artifact['nodes']['3:1']['peak'] = 1
        elif name == 'wrong_fast_job':
            assert artifact['nodes']['3:1']['job'] == 0
            artifact['nodes']['3:1']['job'] = 1
        elif name == 'negative_input':
            artifact['input']['jobs'][0][0] = -1
        elif name == 'extraneous_node':
            artifact['nodes']['0:99'] = dict(mask=0, budget=99, kind='zero', value=0)
        try:
            point_checker.check(artifact)
            accepted, error = True, None
        except Exception:
            accepted, error = False, traceback.format_exc()
        controls.append(dict(id=name, expected_accept=name == 'unchanged', accepted=accepted,
                             status='SUCCESS' if accepted == (name == 'unchanged') else 'FAILURE',
                             error=error, artifact=artifact))
    save(DEST / 'CONTROLS.json', controls)
    summary = dict(cases=76, success=sum(row['status'] == 'SUCCESS' for row in results),
                   failures=[row['id'] for row in results if row['status'] != 'SUCCESS'],
                   controls=7, controls_success=sum(row['status'] == 'SUCCESS' for row in controls),
                   seconds=time.monotonic() - start, raw_sha256=sha(DEST / 'RAW.jsonl'))
    save(DEST / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))
    if summary['success'] != 76 or summary['controls_success'] != 7:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run'))
    arguments = parser.parse_args()
    {'prepare': prepare, 'run': run}[arguments.command]()

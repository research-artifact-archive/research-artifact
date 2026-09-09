from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import json
import signal
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'charged_compiler_scale_01'
CURVES = HERE.parent / 'charged_curves_02'
sys.path.insert(0, str(CURVES))
import basis
import checker
import oracle
import point_checker
import direct
sys.path.append(str(OLD))
import generic

DEST = HERE / 'conformance01'
BUDGETS = [0, 1, 2, 3, 8, 31, 1 << 32]
CONTROLS = ['unchanged_saturation', 'premature_saturation', 'wrong_saturation_value',
            'zero_premium_saturation', 'wrong_zero_premium', 'cyclic_saturated_input',
            'missing_unsaturated_node', 'wrong_peak', 'extraneous_node', 'nonmeeting_bounds', 'raw_zero_but_effective_positive']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def prepare():
    DEST.mkdir(exist_ok=False)
    sources = [HERE / n for n in ('PLAN.md', 'BOUND_PROOF.md', 'bounds.py', 'oracle.py', 'point_checker.py', 'direct.py', 'conformance.py')]
    sources += [CURVES / n for n in ('basis.py', 'compiler.py', 'checker.py')]
    sources += [OLD / 'generic.py', generic.SOURCE, basis.compiler.SOURCE, OLD / 'conformance01/INPUTS.json']
    sources += [Path(sys.executable).resolve()]
    save(DEST / 'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        cases=76, budgets=BUDGETS, requested_roots=532, generic_roots=304, controls=CONTROLS,
        seconds_cap=30, inputs_previously_observed=True, native_runs=0, main_timings=0,
        files={str(p): sha(p) for p in sources}))


class HardStop(BaseException):
    pass


def stop(*args):
    raise HardStop('registered30s conformance cap')


def run():
    m = json.loads((DEST / 'MANIFEST.json').read_text())
    for path, digest in m['files'].items():
        assert sha(path) == digest
    save(DEST / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                       manifest_sha256=sha(DEST / 'MANIFEST.json')))
    cases = json.loads((OLD / 'conformance01/INPUTS.json').read_text())
    results = []
    start = time.monotonic()
    signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, 30)
    try:
        with (DEST / 'RAW.jsonl').open('x') as raw:
            for item in cases:
                row = dict(id=item['id'])
                try:
                    case = item['case']
                    allbudgets = json.loads(json.dumps(basis.compile_case(case)))
                    checker.check(allbudgets)
                    values = [checker.value(allbudgets['curves'][str(allbudgets['full'])], b) for b in BUDGETS]
                    points = oracle.solve_many(case, BUDGETS)
                    certificate = json.loads(json.dumps(points['artifact']))
                    checked = point_checker.check(certificate)
                    scalar = direct.solve_many(case, BUDGETS)
                    general = generic.solve_many(case, [0, 1, 2, 3])
                    assert values == points['values'] == checked['values'] == scalar['values']
                    assert general['values'] == values[:4]
                    row.update(status='SUCCESS', values=values, point_check=checked, point_stats=points['stats'], dp_stats=scalar['stats'])
                except Exception:
                    row.update(status='FAILURE', error=traceback.format_exc())
                raw.write(json.dumps(row, separators=(',', ':')) + '\n')
                raw.flush()
                results.append(row)
        controls = []
        for name in CONTROLS:
            if name in ('zero_premium_saturation', 'wrong_zero_premium'):
                case, b = dict(jobs=[[2, 0, 0, 0, 0]], edges=[]), 1
            elif name == 'raw_zero_but_effective_positive':
                case, b = dict(jobs=[[2, 0, 3, 0, 2]], edges=[]), 2
            elif name == 'cyclic_saturated_input':
                case, b = dict(jobs=[[2, 5, 0, 0, 0], [2, 5, 0, 0, 0]], edges=[]), 100
            elif name in ('missing_unsaturated_node', 'wrong_peak', 'extraneous_node', 'nonmeeting_bounds'):
                case, b = dict(jobs=[[3, 2, 0, 0, 0], [1, 1, 1, 3, 1]], edges=[]), 1
            else:
                case, b = dict(jobs=[[2, 5, 0, 0, 0]], edges=[]), 3
            artifact = json.loads(json.dumps(oracle.solve_many(case, [b])['artifact']))
            root = f'{(1 << len(case["jobs"])) - 1}:{b}'
            if name == 'nonmeeting_bounds':
                artifact['nodes'] = {root: dict(mask=3, budget=1, kind='bounds', value=artifact['values'][0])}
            elif name == 'raw_zero_but_effective_positive':
                artifact['values'][0] = artifact['nodes'][root]['value'] = 0
            elif name == 'premature_saturation':
                artifact['budgets'] = [2]
                artifact['nodes']['1:2'] = artifact['nodes'].pop('1:3')
                artifact['nodes']['1:2']['budget'] = 2
            elif name in ('wrong_saturation_value', 'wrong_zero_premium'):
                artifact['values'][0] += 1
                artifact['nodes'][root]['value'] += 1
            elif name == 'cyclic_saturated_input':
                artifact['input']['edges'] = [[0, 1], [1, 0]]
            elif name == 'missing_unsaturated_node':
                del artifact['nodes']['1:0']
            elif name == 'wrong_peak':
                assert artifact['nodes'][root]['peak'] == 0
                artifact['nodes'][root]['peak'] = 1
            elif name == 'extraneous_node':
                artifact['nodes']['0:99'] = dict(mask=0, budget=99, kind='zero', value=0)
            expected = name in ('unchanged_saturation', 'zero_premium_saturation')
            try:
                point_checker.check(artifact)
                accepted, error = True, None
            except Exception:
                accepted, error = False, traceback.format_exc()
            controls.append(dict(id=name, expected_accept=expected, accepted=accepted,
                                 expected_result_met=expected == accepted, artifact=artifact, error=error))
        save(DEST / 'CONTROLS.json', controls)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    summary = dict(cases=76, success=sum(r['status'] == 'SUCCESS' for r in results), controls=len(CONTROLS),
                   controls_expected=sum(r['expected_result_met'] for r in controls),
                   seconds=time.monotonic() - start, raw_sha256=sha(DEST / 'RAW.jsonl'))
    save(DEST / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))
    if summary['success'] != 76 or summary['controls_expected'] != len(CONTROLS):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run'))
    args = parser.parse_args()
    {'prepare': prepare, 'run': run}[args.command]()


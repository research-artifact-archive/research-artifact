#!/usr/bin/env python3
"""Replay known budget-value checks and inspect all retained benchmark outcomes."""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import importlib.util
import json
import signal
import subprocess
import sys
import time
import traceback

if not __debug__:
    raise RuntimeError('assertions-enabled Python is required')
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/extended/budget_oracle_01'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def load(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roundtrip(value):
    return json.loads(json.dumps(value, sort_keys=True, separators=(',', ':')))


def module(relative):
    path = ROOT / 'src' / relative
    name = 'portable_oracle_' + hashlib.sha256(relative.encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    assert Path(result.__file__).resolve().is_relative_to(ROOT)
    return result


def verify():
    listed = set()
    for row in load(ROOT / 'MANIFEST.json')['files']:
        relative = row['path']
        path = ROOT / relative
        assert relative not in listed and not Path(relative).is_absolute()
        assert path.resolve().is_relative_to(ROOT) and not path.is_symlink()
        assert path.is_file() and path.stat().st_size == row['bytes']
        assert sha(path) == row['sha256'], relative
        listed.add(relative)
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p != ROOT / 'MANIFEST.json'}
    assert actual == listed, dict(unlisted=sorted(actual-listed), missing=sorted(listed-actual))
    return dict(files=len(listed), manifest_sha256=sha(ROOT / 'MANIFEST.json'))


def alarm(signum, frame):
    raise TimeoutError('fixed reproduction limit')


def run_units(out, units, fn, quick=False, limit=3, metadata=None):
    if quick and len(units) > 32:
        units = units[:16] + units[-16:]
    assert len({u['id'] for u in units}) == len(units)
    meta = dict(metadata or {})
    save(out / 'START.json', dict(utc=now(), planned_ids=[u['id'] for u in units],
         quick_smoke=quick, unit_seconds=limit, stage_seconds=180,
         scientific_sample_increase=False, **meta))
    counts = collections.Counter()
    start = time.monotonic()
    signal.signal(signal.SIGALRM, alarm)
    with (out / 'RAW.jsonl').open('x') as stream:
        for unit in units:
            before = time.monotonic()
            remaining = 180 - (before-start)
            if remaining <= 0:
                row = dict(id=unit['id'], status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL, min(limit, remaining))
                try:
                    row = dict(id=unit['id'], status='SUCCESS', result=fn(unit))
                except TimeoutError:
                    row = dict(id=unit['id'], status='TIMEOUT', error=traceback.format_exc())
                except AssertionError:
                    row = dict(id=unit['id'], status='FAILURE', error=traceback.format_exc())
                except Exception:
                    row = dict(id=unit['id'], status='INVALID', error=traceback.format_exc())
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
            row['seconds'] = time.monotonic()-before
            counts[row['status']] += 1
            stream.write(json.dumps(row, separators=(',', ':')) + '\n')
            stream.flush()
    result = dict(success=counts['SUCCESS'] == len(units), planned=len(units),
                  counts=dict(counts), seconds=time.monotonic()-start,
                  quick_smoke=quick, scientific_sample_increase=False, **meta)
    save(out / 'SUMMARY.json', result)
    return result


def oracle(out, args):
    producer = module('budget_oracle_01/oracle_session_hardened.py')
    checker = module('budget_oracle_01/values_certificate_hardened.py')
    units = load(DATA / 'INPUTS.json')
    old = rows(DATA / 'SESSION_RAW.jsonl')
    assert len(units) == len(old) == 4337
    assert len({r['id'] for r in old}) == 4337
    expected = {r['id']: r for r in old}
    assert {u['id'] for u in units} == set(expected)
    assert sum(len(u['budgets']) for u in units) == 21685
    assert sum('expected' in u for u in units) == 4232

    def one(unit):
        prior = expected[unit['id']]
        assert prior['status'] == 'SUCCESS'
        result = producer.solve_many(unit['case'], unit['budgets'])
        artifact = roundtrip(result['artifact'])
        report = checker.check(artifact)
        assert artifact['input'] == unit['case'] and artifact['budgets'] == unit['budgets']
        assert result['status'] == 'SUCCESS'
        assert result['values'] == report['values'] == prior['values']
        if 'expected' in unit:
            assert report['values'] == [unit['expected'][str(b)] for b in unit['budgets']]
        return dict(values=report['values'], roots=len(unit['budgets']), certificate=report)

    return run_units(out, units, one, args.quick,
                     metadata=dict(known_input_units=4337, known_input_roots=21685,
                                   certificate_scope='REQUESTED_ROOT_VALUES'))


def controls(out, args):
    single = module('budget_oracle_01/oracle_hardened.py')
    batch = module('budget_oracle_01/oracle_session_hardened.py')
    check_single = module('budget_oracle_01/value_certificate_hardened.py')
    check_batch = module('budget_oracle_01/values_certificate_hardened.py')
    data = load(DATA / 'CONTROL_INPUTS.json')
    mutants = load(DATA / 'SESSION_CONTROL_INPUTS.json')
    assert len(data['mutants']) == 14 and len(mutants) == 5
    assert data['structurally_inapplicable'] == []
    units = [dict(id='valid-single', kind='valid', artifact=data['valid'])]
    units += [dict(id='single-'+u['id'], kind='single', artifact=u['artifact']) for u in data['mutants']]
    units += [dict(id='batch-'+u['id'], kind='batch', artifact=u['artifact']) for u in mutants]
    bad = [dict(cp=[[1, 1]], edges=[], extra=0),
           dict(cp=[(1, 1)], edges=[]), dict(cp=[[1, 1]], edges=())]
    units += [dict(id=f'shape-{kind}-{j}', kind='shape-'+kind, case=case)
              for j, case in enumerate(bad) for kind in ['single', 'batch']]
    names = ['oracle_hardened', 'oracle_session_hardened',
             'value_certificate_hardened', 'values_certificate_hardened']
    units += [dict(id='optimized-'+name, kind='optimized', name=name) for name in names]

    def one(unit):
        kind = unit['kind']
        if kind == 'valid':
            result = check_single.check(roundtrip(unit['artifact']))
            assert result['value'] == 8
            return dict(outcome='ACCEPTED', value=8)
        if kind == 'optimized':
            result = subprocess.run([sys.executable, '-B', '-O', '-c', 'import '+unit['name']],
                cwd=ROOT / 'src/budget_oracle_01', capture_output=True, text=True, timeout=2)
            assert result.returncode != 0 and 'assertions-enabled Python is required' in result.stderr
            return dict(outcome='REJECTED', exit_code=result.returncode)
        try:
            if kind == 'single': check_single.check(roundtrip(unit['artifact']))
            elif kind == 'batch': check_batch.check(roundtrip(unit['artifact']))
            elif kind == 'shape-single': single.solve(unit['case'], 1)
            elif kind == 'shape-batch': batch.solve_many(unit['case'], [1])
            else: raise RuntimeError(kind)
        except (AssertionError, TypeError, ValueError, KeyError):
            return dict(outcome='REJECTED')
        raise AssertionError('malformed input accepted: '+unit['id'])

    return run_units(out, units, one, metadata=dict(valid_controls=1, rejection_controls=29))


def bench(out, args):
    checker = module('budget_oracle_01/values_certificate_hardened.py')
    hybrid = module('dependency_hybrid_01/hybrid.py')
    packed = module('dependency_hybrid_check_02/check.py')
    shape = module('final_evaluation_dag_01/structure.py')
    bellman = module('dependency_curves_01/checker.py')
    inputs = load(DATA / 'benchmark01/INPUTS.json')
    raw = rows(DATA / 'benchmark01/RAW.jsonl')
    cases = {u['id']: u for u in inputs}
    methods = {'requested_values': {'SUCCESS': 32, 'TIMEOUT': 16},
               'all_budget': {'SUCCESS': 45, 'TIMEOUT': 3}}
    assert len(cases) == len(inputs) == 48 and len(raw) == 96
    assert {(r['id'], r['method']) for r in raw} == {(i, m) for i in cases for m in methods}
    counts = {m: dict(collections.Counter(r['status'] for r in raw if r['method'] == m)) for m in methods}
    assert counts == methods
    successful = {(r['id'], r['method']): r for r in raw if r['status'] == 'SUCCESS'}
    pairs = 0
    for name in cases:
        a, b = successful.get((name, 'requested_values')), successful.get((name, 'all_budget'))
        if a and b:
            assert a['values'] == b['values'] and len(a['values']) == 6
            pairs += 1
    assert pairs == 32
    save(out / 'HISTORICAL_COUNTS.json', dict(records=96, counts=counts,
         shared_inputs=32, shared_values=192, disagreements=0, timeout_units_rerun=0))
    units = [dict(id=r['id']+'/'+r['method'], record=r) for r in raw if r['status'] == 'SUCCESS']

    def one(unit):
        row = unit['record']
        source = cases[row['id']]
        assert row['budgets'] == source['budgets']
        path = DATA / 'benchmark01/units' / row['id'] / row['method'] / 'artifact.json'
        assert sha(path) == row['artifact_sha256'] and path.stat().st_size == row['artifact_bytes']
        artifact = load(path)
        assert artifact['input'] == source['case']
        if row['method'] == 'requested_values':
            assert artifact['budgets'] == source['budgets']
            report = checker.check(artifact)
            values = report['values']
        else:
            if artifact['route'] == 'ordered':
                report = packed.check(artifact)
            else:
                assert artifact['route'] == 'ideal'
                structural = shape.check(artifact)
                report = bellman.check(artifact)
                report['shape'] = structural
            assert not report['violations'], report
            loaded = hybrid.load(artifact)
            values = [hybrid.value(loaded, b) for b in source['budgets']]
        assert values == row['values']
        return dict(method=row['method'], values=values, report=report,
                    saved_artifact_sha256=row['artifact_sha256'])

    return run_units(out, units, one, limit=10, metadata=dict(
        saved_successful_certificates=77, historical_records=96, historical_counts=counts,
        shared_values=192, timeout_units_rerun=0, benchmark_constructors_called=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['verify', 'oracle', 'controls', 'bench', 'all'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    assert sys.version_info >= (3, 10)
    out = args.out.resolve()
    assert not out.is_relative_to(ROOT), 'output must be outside the package'
    if args.worker:
        assert out.is_dir() and not any(out.iterdir())
        try:
            result = {'oracle': oracle, 'controls': controls, 'bench': bench}[args.mode](out, args)
        except Exception:
            save(out / 'HARNESS_ERROR.json', dict(utc=now(), error=traceback.format_exc()))
            raise
        return 0 if result['success'] else 1
    verified = verify()
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'START.json', dict(utc=now(), mode=args.mode, quick_smoke=args.quick,
         verification=verified, python_version=sys.version, scientific_sample_increase=False))
    stages = ['oracle', 'controls', 'bench'] if args.mode == 'all' else ([] if args.mode == 'verify' else [args.mode])
    results = {}
    for stage in stages:
        sub = out / stage
        sub.mkdir()
        command = [sys.executable, '-B', str(Path(__file__).resolve()), stage, '--out', str(sub), '--worker']
        if args.quick: command.append('--quick')
        with (out / (stage+'-stdout.txt')).open('xb') as stdout, (out / (stage+'-stderr.txt')).open('xb') as stderr:
            try:
                code = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=210).returncode
            except subprocess.TimeoutExpired:
                code = None
        result = load(sub / 'SUMMARY.json') if (sub / 'SUMMARY.json').exists() else dict(success=False, reason='worker failed or timed out')
        result['process_exit'] = code
        result['success'] = result['success'] and code == 0
        results[stage] = result
        print(json.dumps(dict(stage=stage, **result)), flush=True)
    result = dict(success=all(r['success'] for r in results.values()), stages=results, scientific_sample_increase=False)
    save(out / 'SUMMARY.json', result)
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Materialize the development denominator; never invokes the new checker."""
from pathlib import Path
import datetime
import hashlib
import itertools
import json
import random
import sys

ROOT = Path(__file__).resolve().parent
S = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def save(path, data):
    with path.open('x') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')


def main():
    lines = list(itertools.product([-3, -1, 0, 1, 3], [-2, -1, 0, 1, 2]))
    units = []
    for k, (p, u, v) in enumerate(itertools.product(lines, repeat=3)):
        for span in [0, 1, 2, 5, 11]:
            units.append(dict(id=f'exhaustive-{k:05d}-{span}', protected=[p], fast=[[u, v]], span=span))
    assert len(units) == 78125
    rng = random.Random(202609080710)
    for k in range(5000):
        def line(): return (rng.randrange(-40, 41), rng.randrange(-9, 10))
        span = rng.randrange(61)
        p = [line(), line()]
        fast = [[line(), line()], [line(), line()]]
        if k % 4 == 1:
            p[0] = (0, 0)
        elif k % 4 == 2:
            at, gap = rng.randrange(span+1), rng.randrange(4)
            p = [(100, 0), (200, 0)]
            fast = [[(0, 0), (-at, 1)], [(0, 0), (at+gap, -1)]]
        elif k % 4 == 3:
            at = rng.randrange(span+1)
            p = [(100, 0), (200, 0)]
            fast = [[(-at-1, 1), (at-1, -1)], [(0, 0), (0, 0)]]
        units.append(dict(id=f'seeded-{k:04d}', protected=p, fast=fast, span=span))
    with (ROOT / 'ALGEBRA_INPUTS.jsonl').open('x') as f:
        for index, unit in enumerate(units):
            unit['selected_fast'] = index % len(unit['fast'])
            f.write(json.dumps(unit, separators=(',', ':'))+'\n')
    final = S / 'final_evaluation_dag_01'
    raw = rows(final / 'RAW.jsonl')
    assert len(raw) == 4232 and all(r['status'] == 'SUCCESS' for r in raw)
    certificates = []
    for row in raw:
        if row['route'] != 'ideal': continue
        path = final / 'artifacts' / (row['input_id']+'.json')
        assert sha(path) == row['artifact_sha256']
        certificates.append(dict(id=row['input_id'], path=str(path.relative_to(S)), sha256=sha(path), expected='ACCEPT'))
    assert len(certificates) == 1296
    save(ROOT / 'CERTIFICATE_INPUTS.json', certificates)
    controls = json.loads((final / 'CONTROL_INPUTS.json').read_text())
    assert len(controls) == 25
    (ROOT / 'CONTROL_INPUTS.json').write_bytes((final / 'CONTROL_INPUTS.json').read_bytes())
    benchmark = S / 'budget_oracle_01/benchmark01'
    old = rows(benchmark / 'RAW.jsonl')
    assert len(old) == 96
    bench = []
    for row in old:
        if row['method'] != 'all_budget' or row['status'] != 'SUCCESS': continue
        path = benchmark / 'units' / row['id'] / 'all_budget/artifact.json'
        assert sha(path) == row['artifact_sha256']
        artifact = json.loads(path.read_text())
        if artifact['route'] != 'ideal': continue
        bench.append(dict(id=row['id'], path=str(path.relative_to(S)), sha256=sha(path),
            expected='ACCEPT', historical_build_serialize_seconds=row['build_serialize_seconds'],
            historical_reload_check_query_seconds=row['reload_check_query_seconds']))
    assert len(bench) == 36
    save(ROOT / 'BENCH_INPUTS.json', bench)
    paths = [ROOT/name for name in ['PLAN_DRAFT.md', 'certificate.py', 'prepare.py', 'run.py',
             'ALGEBRA_INPUTS.jsonl', 'CERTIFICATE_INPUTS.json', 'CONTROL_INPUTS.json', 'BENCH_INPUTS.json']]
    paths += [final / 'structure.py', final / 'RAW.jsonl', benchmark / 'RAW.jsonl']
    save(ROOT / 'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        schema='sweep-policy-certificate-development-v2', python=sys.executable, python_version=sys.version,
        files=[dict(path=str(p.relative_to(S)), bytes=p.stat().st_size, sha256=sha(p)) for p in paths],
        denominator=dict(algebra=83125, ideal_certificates=1296, controls=25, saved_benchmark_ideal_certificates=36),
        structural_outside_scope=dict(final_ordered=2936, benchmark_ordered_success=9),
        preserved_benchmark_records=96, preserved_timeout_records=19, benchmark_constructor_calls=0,
        final_evaluation=False, known_certificates=True, timeout_unit_retry=False,
        hard_stop_utc='2026-09-08T02:00:00Z'))
    print(dict(algebra=len(units), certificates=len(certificates), controls=len(controls), benchmark=len(bench)))


if __name__ == '__main__':
    main()

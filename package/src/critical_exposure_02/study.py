from pathlib import Path
import collections
import datetime
import fractions
import hashlib
import importlib.util
import itertools
import json
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
S = ROOT.parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def encoded(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def case_key(case): return hashlib.sha256(encoded(case)).hexdigest()


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, sort_keys=True, indent=2)
        f.write('\n')


def prepare():
    import random
    known = collections.defaultdict(list)
    for unit in json.loads((S / 'final_evaluation_dag_01/INPUTS.json').read_text()):
        known[case_key(dict(cp=unit['cp'], edges=unit['edges']))].append(unit['id'])
    previous = collections.defaultdict(list)
    for line in (S / 'critical_exposure_01/INPUTS.jsonl').read_text().splitlines():
        unit = json.loads(line)
        previous[case_key(unit['case'])].append(unit['id'])
    units, seen = [], collections.defaultdict(list)
    def add(work, edges, group):
        for q in [3, 5, 6, 10]:
            case = dict(cp=[[2*w, q*w] for w in work], edges=edges)
            key = case_key(case)
            cap = max(4, sum((p+c-1)//c for c, p in case['cp']))
            uid = f'expanded-{len(units):05d}'
            units.append(dict(id=uid, n=len(work), work=list(work), group=group,
                lambda_fraction=[q,2], case=case, budgets=list(range(cap+1)),
                known_final_case_ids=known.get(key, []), prior_study_ids=previous.get(key, []),
                duplicate_previous_unit_ids=list(seen[key])))
            seen[key].append(uid)
    pairs = list(itertools.combinations(range(4), 2))
    for bits in range(1 << len(pairs)):
        edges = [list(edge) for i, edge in enumerate(pairs) if bits >> i & 1]
        for work in itertools.product([1,2,3,5], repeat=4):
            add(work, edges, 'exhaustive-n4')
    rng = random.Random(202609080730)
    for n in [5,6]:
        for index in range(128):
            work = [rng.randint(1,31) for _ in range(n)]
            density = 0 if index < 16 else [.1,.3,.6,.9][index % 4]
            edges = [[i,j] for i in range(n) for j in range(i+1,n) if rng.random() < density]
            add(work, edges, f'seeded-n{n}')
    assert len(units) == 66560
    assert not any(u['prior_study_ids'] for u in units)
    with (ROOT / 'INPUTS.jsonl').open('x') as f:
        for unit in units: f.write(encoded(unit).decode()+'\n')
    paths = [ROOT / 'PLAN.md', ROOT / 'study.py', ROOT / 'INPUTS.jsonl']
    paths += [S / path for path in ['dependency_hybrid_01/hybrid.py', 'dependency_curves_01/curves.py',
        'sweep_certificate_02/certificate.py', 'final_evaluation_dag_01/structure.py',
        'dependency_hybrid_check_02/check.py', 'final_evaluation_dag_01/INPUTS.json',
        'critical_exposure_01/INPUTS.jsonl', 'critical_exposure_01/MOTIVATION_CORRECTION.json']]
    save(ROOT / 'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        files=[dict(path=str(p.relative_to(S)), bytes=p.stat().st_size, sha256=sha(p)) for p in paths],
        units=len(units), budget_roots=sum(len(u['budgets']) for u in units),
        units_with_known_final_case=sum(bool(u['known_final_case_ids']) for u in units),
        units_with_prior_study_case=sum(bool(u['prior_study_ids']) for u in units),
        duplicate_units=sum(bool(u['duplicate_previous_unit_ids']) for u in units),
        python=sys.executable, python_version=sys.version, python_sha256=sha(Path(sys.executable)),
        unit_seconds=5, campaign_seconds=600, final_evaluation=False,
        objective='existing weighted work objective restricted to common p/c', physical_kernel_experiment=False))
    print(dict(units=len(units), roots=sum(len(u['budgets']) for u in units),
        duplicates=sum(bool(u['duplicate_previous_unit_ids']) for u in units),
        known=sum(bool(u['known_final_case_ids']) for u in units)))


def finite_reference(case, cap):
    cp = case['cp']
    n = len(cp)
    pred = [sum(1 << a for a, b in case['edges'] if b == j) for j in range(n)]
    full = (1 << n)-1
    values = {0: [0]*(cap+1)}
    ready = {}
    for mask in range(1, full+1):
        done = full ^ mask
        if any(pred[j] & mask for j in range(n) if done >> j & 1):
            continue
        available = [j for j in range(n) if mask >> j & 1 and not pred[j] & mask]
        ready[mask] = available
        own = [0]*(cap+1)
        for b in range(1, cap+1):
            own[b] = min(min(cp[j][1]+values[mask ^ (1 << j)][b],
                      max(values[mask ^ (1 << j)][b], cp[j][0]+own[b-1])) for j in available)
        values[mask] = own
    def visit(mask, prefix):
        if not mask:
            yield prefix
        else:
            for j in ready[mask]:
                yield from visit(mask ^ (1 << j), prefix+[j])
    best = [None]*(cap+1)
    best_orders = [None]*(cap+1)
    count = 0
    for order in visit(full, []):
        count += 1
        child = [0]*(cap+1)
        for j in reversed(order):
            c, p = cp[j]
            own = [0]*(cap+1)
            for b in range(1, cap+1):
                own[b] = min(p+child[b], max(child[b], c+own[b-1]))
            child = own
        for b, value in enumerate(child):
            if best[b] is None or value < best[b]:
                best[b], best_orders[b] = value, order
    assert count > 0
    return values[full], best, best_orders, count


def run():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
    for record in manifest['files']:
        assert sha(S / record['path']) == record['sha256']
    assert sha(Path(sys.executable)) == manifest['python_sha256'] and __debug__
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat('2026-09-08T01:50:00+00:00')
    hybrid = module('exposure_hybrid', S / 'dependency_hybrid_01/hybrid.py')
    sweep = module('exposure_sweep', S / 'sweep_certificate_02/certificate.py')
    packed = module('exposure_packed', S / 'dependency_hybrid_check_02/check.py')
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir()
    save(ROOT / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), manifest_sha256=sha(ROOT / 'MANIFEST.json')))
    units = [json.loads(line) for line in (ROOT / 'INPUTS.jsonl').read_text().splitlines()]
    def alarm(signum, frame): raise TimeoutError('fixed exposure-study cap')
    signal.signal(signal.SIGALRM, alarm)
    start = time.monotonic()
    counts = collections.Counter()
    groups = collections.defaultdict(collections.Counter)
    strongest = []
    totals = collections.Counter()
    with (ROOT / 'RAW.jsonl').open('x') as f:
        for unit in units:
            before = time.monotonic()
            left = 600-(before-start)
            row = dict(id=unit['id'], n=unit['n'], lambda_fraction=unit['lambda_fraction'])
            if left <= 0:
                row.update(status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL, min(5, left))
                try:
                    data = hybrid.compile_case(unit['case'])
                    path = artifacts / (unit['id']+'.json')
                    data_bytes = encoded(data)
                    with path.open('xb') as output: output.write(data_bytes)
                    data = json.loads(path.read_bytes())
                    report = (packed if data['route'] == 'ordered' else sweep).check(data)
                    assert not report['violations'], report
                    loaded = hybrid.load(data)
                    actual = [hybrid.value(loaded, b) for b in unit['budgets']]
                    scalar, fixed, orders, order_count = finite_reference(unit['case'], max(unit['budgets']))
                    assert actual == scalar
                    assert all(v <= w for v, w in zip(actual, fixed))
                    assert actual[-1] == sum(p for c, p in unit['case']['cp'])
                    gaps = [w-v for v, w in zip(actual, fixed)]
                    if unit['n'] <= 3 or unit['lambda_fraction'][0] == 0:
                        assert max(gaps) == 0
                    base = sum(c for c, p in unit['case']['cp'])
                    ratios = [fractions.Fraction(g, base+w) for g, w in zip(gaps, fixed)]
                    at = max(range(len(ratios)), key=lambda b: ratios[b])
                    row.update(status='SUCCESS', route=data['route'], values=actual, fixed_values=fixed,
                         best_fixed_orders=orders, topological_orders=order_count,
                         normal_scaled_work=base, gaps=gaps, maximum_gap=max(gaps),
                         maximum_relative_gap=[ratios[at].numerator, ratios[at].denominator],
                         witness_budget=at, artifact_sha256=hashlib.sha256(data_bytes).hexdigest(),
                         artifact_bytes=len(data_bytes), certificate_report=report)
                    totals['roots'] += len(actual)
                    totals['strict_roots'] += sum(g > 0 for g in gaps)
                    totals['topological_orders'] += order_count
                    if max(gaps):
                        totals['strict_units'] += 1
                        strongest.append(dict(id=unit['id'], relative=row['maximum_relative_gap'], budget=at))
                except TimeoutError:
                    row.update(status='TIMEOUT', error=traceback.format_exc())
                except AssertionError:
                    row.update(status='FAILURE', error=traceback.format_exc())
                except Exception:
                    row.update(status='INVALID', error=traceback.format_exc())
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
            row['seconds'] = time.monotonic()-before
            counts[row['status']] += 1
            group = (unit['n'], unit['lambda_fraction'][0])
            groups[group][row['status']] += 1
            if row['status'] == 'SUCCESS': groups[group]['strict_units'] += row['maximum_gap'] > 0
            f.write(encoded(row).decode()+'\n')
            f.flush()
            if sum(counts.values()) % 5000 == 0:
                print(dict(completed=sum(counts.values()), counts=dict(counts), strict=totals['strict_units']), flush=True)
    strongest.sort(key=lambda x: fractions.Fraction(*x['relative']), reverse=True)
    summary = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), units=len(units),
        counts=dict(counts), totals=dict(totals), strongest=strongest[:20],
        groups=[dict(n=n, lambda_fraction=[q, 2], counts=dict(value)) for (n, q), value in sorted(groups.items())],
        seconds=time.monotonic()-start, raw_sha256=sha(ROOT / 'RAW.jsonl'), final_evaluation=False,
        physical_kernel_experiment=False, application_fit_established=False)
    save(ROOT / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()

import copy
import datetime
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import traceback
import primitive

HERE = Path(__file__).resolve().parent


def save(name, data):
    with (HERE / name).open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    cases = json.loads((HERE / 'INPUTS.json').read_text())
    save('MANIFEST.json', {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'files': {n: sha(HERE / n) for n in ('PLAN.md', 'INPUTS.json', 'study.py', 'primitive.py')},
         'denominator': len(cases), 'budgets': list(range(13)), 'per_input_seconds': 5,
         'campaign_seconds': 240, 'python': sys.version, 'hard_stop_utc': '2026-09-09T05:00:00Z',
         'source_files': {str(p): sha(p) for p in (
             HERE.parent / 'charged_guaranteed_02/INPUTS.json',
             HERE.parent / 'charged_guaranteed_02/explore.py',
             HERE.parent / 'charged_guard_holding_01/RAW.jsonl',
             HERE.parent / 'CHARGED_EXPOSED_GUARD_AUTHOR_REPORT_07.md')}})
    print('Fixed', len(cases), 'new inputs')


def expired(*unused):
    raise TimeoutError('input/campaign/deadline cap')


def run():
    manifest = json.loads((HERE / 'MANIFEST.json').read_text())
    for name, digest in manifest['files'].items():
        assert sha(HERE / name) == digest
    for path, digest in manifest['source_files'].items():
        assert sha(Path(path)) == digest
    cases = json.loads((HERE / 'INPUTS.json').read_text())
    assert len(cases) == manifest['denominator']
    signal.signal(signal.SIGALRM, expired)
    start = time.monotonic()
    deadline = datetime.datetime.fromisoformat(manifest['hard_stop_utc'].replace('Z', '+00:00')).timestamp()
    save('RUN_STARTED.json', {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            'manifest_sha256': sha(HERE / 'MANIFEST.json')})
    rows, first_gap = [], False
    with (HERE / 'RAW.jsonl').open('x') as raw:
        for case in cases:
            before = time.monotonic()
            left = min(manifest['campaign_seconds'] - (before - start), deadline - time.time())
            row = {'id': case['id']}
            if left <= 0:
                row.update(status='NOT_RUN', reason='campaign/deadline cap')
            else:
                signal.setitimer(signal.ITIMER_REAL, min(manifest['per_input_seconds'], left))
                try:
                    graph = primitive.graph(case)
                    values, policy, rank = primitive.solve_validate(graph)
                    actual = [values[root] for root in graph[1]]
                    expected = primitive.macro(case)
                    clipped = copy.deepcopy(case)
                    mu, exposure = 0, 0
                    for job in clipped['jobs']:
                        w, p, g, v, r = job
                        m = min(v, g + r)
                        if m > 0 and p > m:
                            mu = max(mu, m)
                            exposure += p - m
                            job[1] = m
                    flat = primitive.macro(clipped)
                    gaps, bound_violations = [], []
                    for b, (v, h, hf) in enumerate(zip(actual, expected, flat)):
                        if v != h:
                            gaps.append({'budget': b, 'primitive': v, 'macro': h})
                        if not (max(hf, h - b * mu) <= v <= h and 0 <= h - hf <= exposure):
                            bound_violations.append({'budget': b, 'primitive': v, 'macro': h,
                                                     'flat': hf, 'mu': mu, 'exposure': exposure})
                        if (b <= 1 or mu == 0) and v != h:
                            bound_violations.append({'budget': b, 'reason': 'claimed equality domain failed'})
                    row.update(status='FAILURE' if bound_violations else 'SUCCESS',
                               primitive=actual, macro=expected, flat=flat, gaps=gaps,
                               bound_violations=bound_violations, mu=mu, exposure=exposure,
                               states=len(values), actions=len(graph[2]), max_policy_rank=rank)
                    if (gaps or bound_violations) and not first_gap:
                        save('FIRST_COUNTEREXAMPLE.json', {'input': case, 'row': row,
                             'states': [{'state': s, 'value': values[s], 'action': policy[s]}
                                        for s in sorted(values)], 'actions': graph[2]})
                        first_gap = True
                except TimeoutError as error:
                    row.update(status='TIMEOUT', error=str(error))
                except Exception:
                    row.update(status='INVALID', error=traceback.format_exc())
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
            row['elapsed_seconds'] = time.monotonic() - before
            rows.append(row)
            raw.write(json.dumps(row, separators=(',', ':')) + '\n')
            raw.flush()
    summary = {'denominator': len(cases), 'recorded': len(rows),
               'status_counts': {s: sum(r['status'] == s for r in rows) for s in
                                 ('SUCCESS', 'FAILURE', 'TIMEOUT', 'INVALID', 'NOT_RUN')},
               'gap_inputs': sum(bool(r.get('gaps')) for r in rows),
               'gap_roots': sum(len(r.get('gaps', [])) for r in rows),
               'bound_violations': sum(len(r.get('bound_violations', [])) for r in rows),
               'elapsed_seconds': time.monotonic() - start, 'raw_sha256': sha(HERE / 'RAW.jsonl'),
               'general_equality_proved': False}
    save('SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()

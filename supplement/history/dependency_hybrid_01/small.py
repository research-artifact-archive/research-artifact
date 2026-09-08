import collections
import datetime
import hashlib
import json
import pathlib
import signal
import time
import traceback
import check
import hybrid
from prepare import ROOT, SESSION, save, sha


def scalar(case, bmax=12):
    n = len(case['cp']); vals = [[0] * (bmax + 1) for _ in range(1 << n)]
    for s in range(1, 1 << n):
        ready = [j for j in range(n) if s >> j & 1 and not any(b == j and s >> a & 1 for a, b in case['edges'])]
        for budget in range(1, bmax + 1):
            vals[s][budget] = min(q for j in ready for q in [case['cp'][j][1] + vals[s ^ (1 << j)][budget],
                     max(vals[s ^ (1 << j)][budget], case['cp'][j][0] + vals[s][budget - 1])])
    return vals


def execute(case, old):
    begin = time.perf_counter(); result = hybrid.compile_case(case)
    encoded = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
    with (ROOT / 'small_controllers' / f"{case['id']}.json").open('xb') as f: f.write(encoded)
    construction = time.perf_counter() - begin
    loaded = json.loads(encoded); symbolic = check.check(loaded); loaded = hybrid.load(loaded)
    expected = old[case['id']]['values'] if case['id'] in old else scalar(case)
    n = len(case['cp']); full = (1 << n) - 1; cells = 0
    assert not symbolic.get('violations')
    for b in range(13): assert hybrid.value(loaded, b) == expected[full][b]
    if result['route'] == 'ordered':
        suffixes = [full]
        for j in result['order']: suffixes.append(suffixes[-1] ^ (1 << j))
        policy = [[0] * 13 for _ in range(n + 1)]
        for k in range(n - 1, -1, -1):
            s = suffixes[k]
            for b in range(13):
                j, mode = hybrid.choose(loaded, k, b)
                assert s >> j & 1 and not any(target == j and s >> source & 1 for source, target in case['edges'])
                child = policy[k + 1][b]
                policy[k][b] = case['cp'][j][1] + child if mode == 'protected' else max(child, case['cp'][j][0] + policy[k][b - 1]) if b else child
                assert policy[k][b] == expected[s][b], (k, b, mode, policy[k][b], expected[s][b])
                cells += 1
    else:
        for s in sorted(loaded['curves']):
            for b in range(13):
                assert hybrid.curves.at(loaded['curves'][s], b) == expected[s][b]
                if not s: continue
                j, mode = hybrid.choose(loaded, s, b)
                assert s >> j & 1 and not any(target == j and s >> source & 1 for source, target in case['edges'])
                child = expected[s ^ (1 << j)][b]
                q = case['cp'][j][1] + child if mode == 'protected' else max(child, case['cp'][j][0] + expected[s][b - 1]) if b else child
                assert q == expected[s][b]; cells += 1
    historical = None
    if case['id'] in old:
        previous = json.loads((SESSION / 'dependency_curves_01/controllers' / f"{case['id']}.json").read_text())
        oldroot = previous['curves'][str(full)]
        newroot = check.packed_profile(result['value_slopes']) if result['route'] == 'ordered' else result['curves'][full]
        points = check.all_equal_on(oldroot, newroot, 0, None)
        historical = dict(all_budget_root_agreement=True, compared_points=points)
    return dict(status='SUCCESS', route=result['route'], construction_serialization_seconds=construction,
                checking_and_scalar_seconds=time.perf_counter() - begin - construction, policy_cells=cells,
                controller_bytes=len(encoded), controller_sha256=hashlib.sha256(encoded).hexdigest(),
                symbolic=symbolic, historical_curves=historical)


def main():
    m = json.loads((ROOT / 'MANIFEST.json').read_text())
    for entry in m['files']: assert sha(pathlib.Path(entry['path'])) == entry['sha256']
    old = {r['id']: r for r in map(json.loads, (SESSION / 'dependency_retry_01/RAW.jsonl').open())}
    cases = json.loads((ROOT / 'SMALL_INPUTS.json').read_text())
    malformed = json.loads((ROOT / 'MALFORMED_INPUTS.json').read_text())
    save(ROOT / 'SMALL_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), manifest_sha256=sha(ROOT / 'MANIFEST.json')))
    (ROOT / 'small_controllers').mkdir(); rows = []; start = time.monotonic()
    def alarm(signum, frame): raise TimeoutError('fixed cap')
    signal.signal(signal.SIGALRM, alarm)
    with (ROOT / 'SMALL_RAW.jsonl').open('x') as raw:
        for case in cases + malformed:
            t = time.monotonic(); row = dict(id=case['id'])
            if t - start >= 300: row.update(status='NOT_RUN', reason='campaign cap')
            else:
                signal.setitimer(signal.ITIMER_REAL, min(3, 300 - (t - start)))
                try:
                    if case in malformed:
                        try: hybrid.compile_case(case)
                        except ValueError: row.update(status='SUCCESS', expected_rejection=True)
                        else: row.update(status='FAILURE', expected_rejection=False)
                    else: row.update(execute(case, old))
                except TimeoutError: row.update(status='TIMEOUT')
                except AssertionError: row.update(status='FAILURE', error=traceback.format_exc())
                except Exception: row.update(status='INVALID', error=traceback.format_exc())
                finally: signal.setitimer(signal.ITIMER_REAL, 0)
            row['elapsed_seconds'] = time.monotonic() - t; rows.append(row)
            raw.write(json.dumps(row, sort_keys=True) + '\n'); raw.flush()
    summary = dict(cases=len(rows), statuses=dict(collections.Counter(r['status'] for r in rows)),
                   routes=dict(collections.Counter(r.get('route', 'rejection_fixture') for r in rows)),
                   policy_cells=sum(r.get('policy_cells', 0) for r in rows),
                   elapsed_seconds=time.monotonic() - start, raw_sha256=sha(ROOT / 'SMALL_RAW.jsonl'), final_evaluation=False)
    save(ROOT / 'SMALL_SUMMARY.json', summary); print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()

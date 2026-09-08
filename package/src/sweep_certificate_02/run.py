"""One exploratory development execution, with complete frozen denominators."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import signal
import sys
import time
import traceback
import certificate

ROOT = Path(__file__).resolve().parent
S = ROOT.parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text())
def rows(path): return [json.loads(line) for line in path.read_text().splitlines()]


def save(path, data):
    with path.open('x') as f:
        json.dump(data, f, sort_keys=True, indent=2)
        f.write('\n')


def alarm(signum, frame): raise TimeoutError('fixed development cap')


def algebra(unit):
    result = certificate.interval_identity(unit['protected'], unit['fast'], unit['span'])
    selected = certificate.interval_identity(unit['protected'], unit['fast'], unit['span'], unit['selected_fast'])
    brute = []
    policy = []
    for t in range(unit['span']+1):
        values = [a+d*t for a, d in unit['protected']]
        values += [max(a+d*t, b+e*t) for (a, d), (b, e) in unit['fast']]
        brute.append(min(values))
        (a, d), (b, e) = unit['fast'][unit['selected_fast']]
        policy.append(min([x+y*t for x, y in unit['protected']] + [max(a+d*t, b+e*t)]))
    expected = all(v == 0 for v in brute)
    assert result['ok'] == expected, dict(unit=unit, result=result, brute=brute)
    if not result['ok']:
        assert 0 <= result['offset'] <= unit['span'] and brute[result['offset']] != 0
    selected_expected = all(v >= 0 for v in brute) and all(v == 0 for v in policy)
    assert selected['ok'] == selected_expected, dict(unit=unit, result=selected, brute=brute, policy=policy)
    if not selected['ok']:
        point = selected['offset']
        assert 0 <= point <= unit['span'] and (brute[point] < 0 or policy[point] != 0)
    return dict(accepted=result['ok'], selected_accepted=selected['ok'],
                negative_witness=result.get('offset'), selected_negative_witness=selected.get('offset'))


def scan(unit):
    path = S / unit['path']
    assert sha(path) == unit['sha256']
    data = load(path)
    t = time.perf_counter()
    result = certificate.check(data)
    elapsed = time.perf_counter()-t
    assert not result['violations'], result
    return dict(check_seconds=elapsed, report=result, artifact_sha256=unit['sha256'])


def control(unit):
    detail = None
    try:
        report = certificate.check(unit['data'])
        accepted = not report['violations']
        detail = report
    except (AssertionError, TypeError, ValueError, KeyError, IndexError) as e:
        accepted = False
        detail = repr(e)
    actual = 'ACCEPT' if accepted else 'REJECT'
    assert actual == unit['expected'], (actual, unit['expected'], detail)
    return dict(actual=actual, expected=unit['expected'], detail=detail)


def stage(name, units, fn, cap, output):
    out = output / name
    out.mkdir()
    save(out / 'START.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         planned_ids=[u['id'] for u in units], unit_seconds=cap, stage_seconds=180))
    start = time.monotonic()
    counts = collections.Counter()
    accepted = rejected = 0
    with (out / 'RAW.jsonl').open('x') as f:
        for unit in units:
            before = time.monotonic()
            left = 180-(before-start)
            if left <= 0:
                row = dict(id=unit['id'], status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL, min(left, cap))
                try:
                    result = fn(unit)
                    row = dict(id=unit['id'], status='SUCCESS', result=result)
                    if name == 'algebra':
                        accepted += result['accepted']
                        rejected += not result['accepted']
                except TimeoutError:
                    row = dict(id=unit['id'], status='TIMEOUT', error=traceback.format_exc())
                except AssertionError:
                    row = dict(id=unit['id'], status='FAILURE', error=traceback.format_exc())
                except Exception:
                    row = dict(id=unit['id'], status='INVALID', error=traceback.format_exc())
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
            row['seconds'] = time.monotonic()-before
            f.write(json.dumps(row, separators=(',', ':'))+'\n')
            f.flush()
            counts[row['status']] += 1
    result = dict(planned=len(units), counts=dict(counts), success=counts['SUCCESS'] == len(units),
                  seconds=time.monotonic()-start, raw_sha256=sha(out / 'RAW.jsonl'))
    if name == 'algebra': result.update(accepted_identities=accepted, rejected_identities=rejected)
    save(out / 'SUMMARY.json', result)
    print(json.dumps(dict(stage=name, **result)), flush=True)
    return result


def main():
    assert len(sys.argv) == 2 and __debug__
    out = Path(sys.argv[1]).resolve()
    manifest = load(ROOT / 'MANIFEST.json')
    for record in manifest['files']:
        path = S / record['path']
        assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256']
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat('2026-09-08T01:50:00+00:00')
    out.mkdir(exist_ok=False)
    save(out / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         manifest_sha256=sha(ROOT / 'MANIFEST.json'), python=sys.executable, python_version=sys.version))
    signal.signal(signal.SIGALRM, alarm)
    stages = {}
    stages['algebra'] = stage('algebra', rows(ROOT / 'ALGEBRA_INPUTS.jsonl'), algebra, 2, out)
    stages['certificates'] = stage('certificates', load(ROOT / 'CERTIFICATE_INPUTS.json'), scan, 2, out)
    stages['controls'] = stage('controls', load(ROOT / 'CONTROL_INPUTS.json'), control, 2, out)
    stages['bench'] = stage('bench', load(ROOT / 'BENCH_INPUTS.json'), scan, 10, out)
    summary = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), stages=stages,
       success=all(r['success'] for r in stages.values()), final_evaluation=False,
       historical_outcomes_changed=False, benchmark_constructors_called=0, historical_timeout_units_rerun=0)
    save(out / 'SUMMARY.json', summary)
    return 0 if summary['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

import collections
import datetime
import json
import pathlib
import signal
import time
import traceback
import check
from prepare import ROOT, save, sha


def unrestricted_scalar(cp):
    n = len(cp); total = sum(p for c, p in cp); values = [[0] * (total + 1) for _ in range(1 << n)]
    for s in range(1, 1 << n):
        for b in range(1, total + 1):
            options = []
            for j, (c, p) in enumerate(cp):
                if not s >> j & 1: continue
                child = values[s ^ (1 << j)][b]
                options.extend([p + child, max(child, c + values[s][b - 1])])
            values[s][b] = min(options)
    return values[-1]


def candidate_values(certificate):
    slopes = [h for h, count in certificate['value_slopes'] for _ in range(count)]
    P = sum(p for c, p in certificate['input']['cp']); values = [0]
    for b in range(1, P + 1): values.append(values[-1] + (slopes[b - 1] if b <= len(slopes) else 0))
    return values


def accepted(artifact):
    try: result = check.check(artifact)
    except (AssertionError, ValueError, TypeError, KeyError, IndexError): return False, None
    return True, result


def main():
    m = json.loads((ROOT / 'MANIFEST.json').read_text())
    for entry in m['files']: assert sha(pathlib.Path(entry['path'])) == entry['sha256'], entry['path']
    save(ROOT / 'SEMANTIC_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), manifest_sha256=sha(ROOT / 'MANIFEST.json')))
    small = json.loads((ROOT / 'SMALL_UNITS.json').read_text())
    malformed = json.loads((ROOT / 'MALFORMED.json').read_text())
    start = time.monotonic(); scalar_cache = {}; rows = []; timed_out = False
    def alarm(signum, frame): raise TimeoutError('semantic cap')
    signal.signal(signal.SIGALRM, alarm)
    def units():
        for unit in small: yield 'known_ordered', unit
        with (ROOT / 'CANDIDATES.jsonl').open() as f:
            for line in f: yield 'exhaustive_candidate', json.loads(line)
        for unit in malformed: yield 'malformed', unit
    with (ROOT / 'SEMANTIC_RAW.jsonl').open('x') as raw:
        for group, unit in units():
            row = dict(group=group, id=unit['id'])
            remaining = m['semantic_cap_seconds'] - (time.monotonic() - start)
            if timed_out or remaining <= 0: row.update(status='NOT_RUN', reason='total_cap')
            else:
                signal.setitimer(signal.ITIMER_REAL, remaining)
                try:
                    artifact = json.loads(pathlib.Path(unit['path']).read_text()) if group == 'known_ordered' else unit['certificate']
                    if group == 'exhaustive_candidate':
                        key = unit['vector_id']
                        if key not in scalar_cache: scalar_cache[key] = unrestricted_scalar(artifact['input']['cp'])
                        expected = candidate_values(artifact) == scalar_cache[key]
                    else: expected = group == 'known_ordered'
                    got, checked = accepted(artifact)
                    row.update(status='SUCCESS' if got == expected else 'FAILURE', expected_accept=expected, accepted=got)
                    if group == 'known_ordered': row['symbolic'] = checked
                except TimeoutError: timed_out = True; row.update(status='TIMEOUT')
                except Exception: row.update(status='INVALID', error=traceback.format_exc())
                finally: signal.setitimer(signal.ITIMER_REAL, 0)
            rows.append(row); raw.write(json.dumps(row, sort_keys=True) + '\n'); raw.flush()
    summary = dict(units=len(rows), groups={g: dict(collections.Counter(r['status'] for r in rows if r['group'] == g)) for g in sorted({r['group'] for r in rows})},
                   exhaustive_outcomes=dict(collections.Counter('ACCEPT' if r.get('accepted') else 'REJECT' for r in rows if r['group'] == 'exhaustive_candidate')),
                   elapsed_seconds=time.monotonic() - start, raw_sha256=sha(ROOT / 'SEMANTIC_RAW.jsonl'), final_evaluation=False)
    save(ROOT / 'SEMANTIC_SUMMARY.json', summary); print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()

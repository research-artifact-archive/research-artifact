from pathlib import Path
import collections
import datetime
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
S = ROOT.parent
DEST = ROOT / 'compare01'
METHODS = ['previous', 'sweep']


def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())


def save(p, data):
    with p.open('x') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')


def prepare():
    DEST.mkdir()
    (DEST / 'inputs').mkdir()
    inputs = load(ROOT / 'BENCH_INPUTS.json')
    assert len(inputs) == 36
    units = []
    for index, source in enumerate(inputs):
        assert sha(S / source['path']) == source['sha256']
        save(DEST / 'inputs' / (source['id']+'.json'), source)
        for method in METHODS[index % 2:] + METHODS[:index % 2]:
            units.append(dict(id=source['id'], method=method))
    save(DEST / 'UNITS.json', units)
    paths = [ROOT / n for n in ['COMPARE_PLAN.md', 'compare.py', 'compare_worker.py', 'certificate.py', 'BENCH_INPUTS.json']]
    paths += [S / 'final_evaluation_dag_01/structure.py', S / 'dependency_curves_01/checker.py', DEST / 'UNITS.json']
    paths += sorted((DEST / 'inputs').glob('*.json'))
    save(DEST / 'MANIFEST.json', dict(utc=now(), files=[dict(path=str(p.relative_to(S)), sha256=sha(p)) for p in paths],
        certificates=36, units=72, methods=METHODS, python=sys.executable,
        python_sha256=sha(sys.executable), python_version=sys.version, platform=platform.platform(),
        cold_cap_seconds=5, rss_cap_bytes=1073741824, rss_sample_seconds=0.05,
        campaign_seconds=420, hard_stop_utc='2026-09-08T02:00:00Z', known_successful_inputs=True,
        original_timeout_units_rerun=0, constructor_calls=0, final_evaluation=False))
    print('fixed 36 saved certificates / 72 cold checker units')


def run():
    manifest = load(DEST / 'MANIFEST.json')
    for record in manifest['files']:
        assert sha(S / record['path']) == record['sha256']
    assert sha(manifest['python']) == manifest['python_sha256']
    units = load(DEST / 'UNITS.json')
    save(DEST / 'RUN_STARTED.json', dict(utc=now(), pid=os.getpid(), manifest_sha256=sha(DEST / 'MANIFEST.json')))
    start = time.monotonic()
    counts = collections.defaultdict(collections.Counter)
    results = []
    with (DEST / 'RAW.jsonl').open('x') as raw:
        for index, unit in enumerate(units):
            row = dict(unit)
            out = DEST / 'units' / unit['id'] / unit['method']
            out.mkdir(parents=True)
            if time.monotonic()-start >= 420 or datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime.fromisoformat('2026-09-08T01:50:00+00:00'):
                row.update(status='NOT_RUN', reason='campaign_or_closeout_limit')
            else:
                argv = [manifest['python'], '-B', str(ROOT / 'compare_worker.py'), unit['method'],
                        str(DEST / 'inputs' / (unit['id']+'.json')), str(out)]
                save(out / 'COMMAND.json', dict(argv=argv, wall_seconds=5, rss_bytes=1073741824))
                before = time.monotonic()
                rss = 0
                reason = None
                with (out / 'stdout.txt').open('xb') as stdout, (out / 'stderr.txt').open('xb') as stderr:
                    process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
                    while process.poll() is None:
                        if time.monotonic()-before >= 5:
                            reason = 'wall_timeout'
                        elif time.monotonic()-start >= 420:
                            reason = 'campaign_cap'
                        else:
                            sampled = subprocess.run(['/bin/ps', '-o', 'rss=', '-p', str(process.pid)], capture_output=True, text=True, timeout=2)
                            try: rss = max(rss, int(sampled.stdout.strip())*1024)
                            except ValueError: pass
                            if rss > 1073741824: reason = 'memory_limit'
                        if reason:
                            try: os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError: pass
                            break
                        time.sleep(0.05)
                    code = process.wait(timeout=5)
                row.update(cold_seconds=time.monotonic()-before, exit_code=code, sampled_peak_rss_bytes=rss)
                result = load(out / 'RESULT.json') if (out / 'RESULT.json').exists() else None
                if reason:
                    row.update(status='FAILURE' if reason == 'memory_limit' else 'TIMEOUT', reason=reason, partial_result=result)
                elif code or result is None:
                    row.update(status='INVALID', reason='process_or_missing_result', partial_result=result)
                else:
                    row.update(result)
            counts[unit['method']][row['status']] += 1
            raw.write(json.dumps(row, sort_keys=True, separators=(',', ':'))+'\n')
            raw.flush()
            results.append(row)
            if (index+1) % 12 == 0:
                print(json.dumps(dict(completed=index+1, counts={k:dict(v) for k,v in counts.items()})), flush=True)
    paired = collections.defaultdict(dict)
    for row in results:
        if row['status'] == 'SUCCESS': paired[row['id']][row['method']] = row['report']['checked_states']
    disagreements = [dict(id=k, states=v) for k, v in paired.items() if len(v) == 2 and len(set(v.values())) != 1]
    times = {method: {field: sum(r[field] for r in results if r['method'] == method and r['status'] == 'SUCCESS')
             for field in ['cold_seconds', 'worker_seconds', 'import_seconds', 'read_hash_parse_seconds', 'check_seconds']}
             for method in METHODS}
    summary = dict(utc=now(), units=len(results), counts={k:dict(v) for k,v in counts.items()},
        times_successful_units=times, seconds=time.monotonic()-start, disagreements=disagreements,
        raw_sha256=sha(DEST / 'RAW.jsonl'), known_successful_certificates=True,
        original_timeout_units_rerun=0, constructor_calls=0, final_evaluation=False)
    save(DEST / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()

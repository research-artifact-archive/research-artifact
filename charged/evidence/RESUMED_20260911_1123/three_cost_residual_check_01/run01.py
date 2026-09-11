"""Single bounded attempt. Preserve all raw; refuse overwrite or hash drift."""
import gzip
import hashlib
import json
import os
import signal
import sys
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path
from actual_oracle01 import evaluate
from candidate_compare01 import compare

BASE = Path(__file__).resolve().parent

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as src:
        for block in iter(lambda:src.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def encode(value):
    return json.dumps(value,separators=(',',':'),sort_keys=True)+'\n'

def timeout(signum,frame):
    raise TimeoutError('fixed run bound reached; no retry')

def main():
    freeze = json.loads((BASE/'FREEZE01.json').read_text())
    for name,meta in freeze['files'].items():
        if digest(BASE/name) != meta['sha256']:
            raise RuntimeError('frozen input/code changed: '+name)
    run = BASE/'run01'
    run.mkdir(exist_ok=False)
    started = time.monotonic()
    summary = dict(attempt=1,status='STARTED',start_utc=now(),pid=os.getpid(),
        freeze_sha256=digest(BASE/'FREEZE01.json'),planned=freeze['expected']['games'],
        completed=0,passed=0,failed=0,timeout=0,invalid=0,not_run=0,
        policies=0,leaves=0,modes=0,benchmark_comparisons=0,prefix_probes=0,
        negative_ell_probes=0,failure_items=0,child_processes_spawned=0)
    (run/'START01.json').write_text(encode(summary))
    catalog = json.loads((BASE/'catalog01.json').read_text())
    deadline = datetime(2026,9,11,4,55,tzinfo=timezone.utc).timestamp()
    seconds = min(180,deadline-time.time())
    if seconds <= 0:
        summary.update(status='TIMEOUT_BEFORE_RUN',timeout=1,not_run=summary['planned']-1)
        (run/'RECEIPT01.json').write_text(encode(summary))
        return 2
    signal.signal(signal.SIGALRM,timeout)
    signal.setitimer(signal.ITIMER_REAL,seconds)
    current = None
    with (run/'EVENTS01.jsonl').open('x') as events:
        events.write(encode(dict(event='started',utc=now(),seconds_bound=seconds)))
        events.flush()
        try:
            with gzip.open(run/'RAW01.jsonl.gz','xt',compresslevel=1) as rawfile, \
                 gzip.open(run/'COMPARISONS01.jsonl.gz','xt',compresslevel=1) as cmpfile, \
                 (BASE/'population01.jsonl').open() as pop:
                for line in pop:
                    game = json.loads(line)
                    current = game['id']
                    assert current == summary['completed']
                    cat = catalog[game['catalog']]
                    raw = evaluate(game,cat)
                    rawfile.write(encode(raw))
                    rawfile.flush()
                    result = compare(game,cat,raw)
                    cmpfile.write(encode(result))
                    summary['completed'] += 1
                    summary['failed' if result['failures'] else 'passed'] += 1
                    summary['failure_items'] += len(result['failures'])
                    summary['policies'] += len(raw['policies'])
                    summary['leaves'] += sum(len(row[2]) for row in raw['policies'])
                    summary['modes'] += len(raw['mode_limits'])
                    summary['benchmark_comparisons'] += len(raw['benchmark_curve'])
                    summary['prefix_probes'] += len(result['actual_prefix_probes'])
                    summary['negative_ell_probes'] += result['negative_ell_probes']
                    if current % 5000 == 0:
                        events.write(encode(dict(event='progress',completed=summary['completed'],utc=now())))
                        events.flush()
                assert summary['completed'] == summary['planned']
                for key in ('policies','leaves','modes'):
                    assert summary[key] == freeze['expected'][key], key
            summary['status'] = 'DISAGREEMENT' if summary['failed'] else 'COMPLETE_NO_DISAGREEMENT'
        except BaseException as exc:
            key = 'timeout' if isinstance(exc,TimeoutError) else 'invalid'
            summary[key] = 1
            summary['not_run'] = max(0,summary['planned']-summary['completed']-1)
            summary.update(status=key.upper(),current_game=current,error=repr(exc))
            (run/'ERROR01.txt').write_text(traceback.format_exc())
            events.write(encode(dict(event='exception',category=key,current_game=current,error=repr(exc),utc=now())))
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            summary.update(end_utc=now(),elapsed_seconds=time.monotonic()-started)
            events.write(encode(dict(event='closed',utc=now(),status=summary['status'])))
    summary['raw_files'] = {p.name:dict(sha256=digest(p),bytes=p.stat().st_size)
                            for p in sorted(run.iterdir()) if p.name != 'RECEIPT01.json'}
    summary['frozen_files_unchanged'] = all(digest(BASE/name)==meta['sha256'] for name,meta in freeze['files'].items())
    (run/'RECEIPT01.json').write_text(encode(summary))
    print(json.dumps(summary,sort_keys=True))
    return 0 if summary['status']=='COMPLETE_NO_DISAGREEMENT' and summary['frozen_files_unchanged'] else 1

if __name__ == '__main__':
    sys.exit(main())

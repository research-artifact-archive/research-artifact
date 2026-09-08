import collections
import datetime
import json
import os
import pathlib
import signal
import subprocess
import time
from prepare import ROOT, save, sha


def now(): return datetime.datetime.now(datetime.timezone.utc)


def main():
    m = json.loads((ROOT / 'MANIFEST.json').read_text())
    for entry in m['files']: assert sha(pathlib.Path(entry['path'])) == entry['sha256'], entry['path']
    units = json.loads((ROOT / 'SCALE_UNITS.json').read_text())
    deadline = datetime.datetime.fromisoformat(m['session_deadline_utc'])
    save(ROOT / 'SCALE_STARTED.json', dict(start=now().isoformat(), manifest_sha256=sha(ROOT / 'MANIFEST.json'), parent_pid=os.getpid()))
    start = time.monotonic(); rows = []
    with (ROOT / 'SCALE_RAW.jsonl').open('x') as raw:
        for unit in units:
            directory = ROOT / 'units' / unit['id']; directory.mkdir(parents=True)
            row = dict(case=unit['id'], group=unit['group'], started=now().isoformat())
            if time.monotonic() - start >= m['scale_total_cap_seconds'] or now() >= deadline:
                row.update(status='NOT_RUN', reason='campaign_or_session_deadline')
            else:
                argv = [m['python'], str(ROOT / 'worker.py'), unit['path'], str(directory)]
                save(directory / 'COMMAND.json', dict(argv=argv, timeout_seconds=m['scale_unit_cap_seconds'], rss_cap_bytes=m['rss_cap_bytes']))
                t = time.monotonic(); rss = 0; reason = None
                with (directory / 'stdout.txt').open('xb') as out, (directory / 'stderr.txt').open('xb') as err:
                    proc = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
                    while proc.poll() is None:
                        if time.monotonic() - t >= m['scale_unit_cap_seconds']: reason = 'wall_timeout'
                        elif time.monotonic() - start >= m['scale_total_cap_seconds'] or now() >= deadline: reason = 'campaign_or_session_deadline'
                        else:
                            ps = subprocess.run(['/bin/ps', '-o', 'rss=', '-p', str(proc.pid)], capture_output=True, text=True, timeout=2)
                            try: rss = max(rss, int(ps.stdout.strip()) * 1024)
                            except ValueError: pass
                            if rss > m['rss_cap_bytes']: reason = 'memory_limit'
                        if reason:
                            try: os.killpg(proc.pid, signal.SIGKILL)
                            except ProcessLookupError: pass
                            break
                        time.sleep(m['rss_poll_seconds'])
                    code = proc.wait(timeout=5)
                row.update(cold_seconds=time.monotonic() - t, exit_code=code, sampled_peak_rss_bytes=rss)
                if reason: row.update(status='FAILURE' if reason == 'memory_limit' else 'TIMEOUT', reason=reason)
                elif code or not (directory / 'RESULT.json').exists(): row.update(status='INVALID', reason='process_or_missing_result')
                else:
                    try: row.update(json.loads((directory / 'RESULT.json').read_text()))
                    except Exception as e: row.update(status='INVALID', reason='result_parse', error=repr(e))
            rows.append(row); raw.write(json.dumps(row, separators=(',', ':')) + '\n'); raw.flush()
            if len(rows) % 12 == 0: print(json.dumps(dict(completed=len(rows), total=len(units), statuses=dict(collections.Counter(r['status'] for r in rows)))), flush=True)
    summary = dict(planned_units=len(units), recorded=len(rows),
                   by_group={g: dict(collections.Counter(r['status'] for r in rows if r['group'] == g)) for g in sorted({r['group'] for r in rows})},
                   elapsed_seconds=time.monotonic() - start, raw_sha256=sha(ROOT / 'SCALE_RAW.jsonl'), final_evaluation=False,
                   repeated_compilation=False)
    save(ROOT / 'SCALE_SUMMARY.json', summary); print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__': main()

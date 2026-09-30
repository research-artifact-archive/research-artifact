#!/usr/bin/env python3
"""Serial fresh-JVM E1/E2 runs. Existing attempt directories are never overwritten."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from ablation_common import (OLD_JAR, STATUSES, csv_write, planned_jobs, read_json,
                             read_trial, sha256, write_json)


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def remaining(deadline):
    return (dt.datetime.fromisoformat(deadline) - utc_now()).total_seconds() if deadline else float('inf')


@contextmanager
def execution_lock(path):
    """One lock shared by E1 and E2; no concurrent heavy synthesis from these runners."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError('Another ablation runner holds the shared execution lock')
    try:
        yield
    finally:
        if os.name == 'nt':
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()


def command_for(config, job, run_dir, root, jar_sha, commit):
    props = dict(job['jvm_properties'])
    props.update({'java.awt.headless': 'true', 'mtsa.build.commit': commit})
    return ([config['java']] + [f'-D{k}={v}' for k, v in sorted(props.items())]
            + ['-Xmx' + config['java_heap'], '-cp', config['classpath'], config['main_class'],
               '--lts', job['model_path'], '--target', job['target_name'],
               '--output', str((run_dir / 'output.txt').relative_to(root)),
               '--transitions', str((run_dir / 'transitions.txt').relative_to(root)),
               '--transition-output', 'summary'])


def run_trial(config, job, cap, attempt, campaign, root, provenance):
    run_dir = campaign / attempt / 'runs' / job['job_id']
    meta_path = run_dir / 'meta.json'
    if run_dir.exists():
        # Even an interrupted run is retained. Only E2's explicit TO retry is permitted.
        return read_trial(meta_path)
    run_dir.mkdir(parents=True)
    command = command_for(config, job, run_dir, root, provenance['jar_sha256'], provenance['source_commit'])
    meta = dict(completed=False, status='RUNNING', started_utc=utc_now().isoformat(),
                job=job, command=command, timeout_seconds=cap, java_heap=config['java_heap'],
                attempt=attempt, jar_sha256=provenance['jar_sha256'], source_commit=provenance['source_commit'],
                input_sha256=sha256(root / job['model_path']), platform=config['platform'])
    write_json(meta_path, meta)
    process = None
    start = time.monotonic_ns()
    interrupted = False
    try:
        with (run_dir / 'stdout.txt').open('wb') as out, (run_dir / 'stderr.txt').open('wb') as err:
            process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       **({'start_new_session': True} if os.name != 'nt' else {}))
            meta['pid'] = process.pid
            write_json(meta_path, meta)
            try:
                process.wait(timeout=cap)
                meta['status'] = STATUSES.get(process.returncode, 'SIGNALLED' if process.returncode < 0 else 'UNKNOWN_EXIT')
            except subprocess.TimeoutExpired:
                meta['status'] = 'TIMEOUT'
                stop_process(process)
    except KeyboardInterrupt:
        meta['status'] = 'INTERRUPTED'; interrupted = True
        if process:
            stop_process(process)
    except BaseException as error:
        meta['status'] = 'HARNESS_ERROR'
        meta['harness_error'] = f'{type(error).__name__}: {error}'
        if process:
            stop_process(process)
    finally:
        meta.update(completed=True, finished_utc=utc_now().isoformat(),
                    elapsed_monotonic_seconds=(time.monotonic_ns() - start) / 1e9,
                    exit_code=process.returncode if process else None)
        stderr = (run_dir / 'stderr.txt').read_text(errors='replace') if (run_dir / 'stderr.txt').exists() else ''
        if meta['status'] != 'TIMEOUT' and ('OutOfMemoryError' in stderr or 'Cannot allocate memory' in stderr):
            meta['status'] = 'OOM'
        meta['artifact_digests'] = {p.name.split('.')[0]: {'sha256': sha256(p), 'bytes': p.stat().st_size}
                                    for p in run_dir.iterdir() if p.is_file() and p.name != 'meta.json'}
        write_json(meta_path, meta)
    if interrupted:
        raise KeyboardInterrupt
    return read_trial(meta_path)


def write_progress(config, jobs, campaign):
    rows = []
    for job in jobs:
        for attempt in ('pass1_1200s', 'pass2_3600s') if config['series'] == 'e2' else ('pass1_1200s',):
            path = campaign / attempt / 'runs' / job['job_id'] / 'meta.json'
            if attempt == 'pass2_3600s' and not path.exists():
                continue
            rows.append(dict(model_id=job['model_id'], target_id=job['target_id'], method_id=job['method_id'],
                             merge=job['merge'], attempt=attempt, **read_trial(path)))
    columns = list(dict.fromkeys(key for row in rows for key in row))
    csv_write(campaign / 'progress.csv', rows, columns)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--first-pass-only', action='store_true')
    args = parser.parse_args()
    config = read_json(args.config)
    root = args.root.resolve()
    jobs = list(planned_jobs(config))
    expected = 27 if config['series'] == 'e2' else 54
    if len(jobs) != expected or config.get('repetitions') != 1 or config.get('parallel_trials') != 1:
        raise ValueError('Plan differs from the 27-cell E2 / 54-cell E1 single-trial serial design')
    if args.dry_run:
        for job in jobs:
            print(job['job_id'], job['model_path'], job['target_name'])
        print(f'planned={len(jobs)} heap={config["java_heap"]} timeout={config["timeout_seconds"]}; no JVM launched')
        return 0
    if config['platform'] == 'mac' and sys.platform != 'darwin':
        raise RuntimeError('Mac config requires macOS')
    jar = root / config['classpath']
    provenance = read_json(root / config['jar_metadata'])
    jar_sha = sha256(jar)
    if provenance.get('jar_sha256') != jar_sha or jar_sha == OLD_JAR or not provenance.get('source_commit'):
        raise RuntimeError('New JAR must match its metadata and have a source commit; existing JAR is forbidden')
    for job in jobs:
        if not (root / job['model_path']).is_file():
            raise FileNotFoundError(job['model_path'])
    results = root / config['results_root']
    campaign = results / f'{config["series"]}_{config["platform"]}'
    campaign.mkdir(parents=True, exist_ok=True)
    saved = campaign / 'config.json'
    if saved.exists() and read_json(saved) != config:
        raise RuntimeError('Saved campaign config differs; refusing to mix attempts')
    write_json(saved, config)
    saved_provenance = campaign / 'jar.json'
    if saved_provenance.exists() and read_json(saved_provenance) != provenance:
        raise RuntimeError('Saved campaign JAR differs; refusing to mix attempts')
    write_json(saved_provenance, provenance)
    env = campaign / 'environment.json'
    if not env.exists():
        write_json(env, {'system': platform.system(), 'machine': platform.machine(), 'python': platform.python_version(),
                         'java_version': subprocess.run([config['java'], '-version'], capture_output=True, text=True).stderr,
                         'captured_utc': utc_now().isoformat(), 'timing_scope': 'same-host only; Mac values are reference measurements'})
    with execution_lock(results / 'ablation.lock'):
        for index, job in enumerate(jobs, 1):
            path = campaign / 'pass1_1200s' / 'runs' / job['job_id']
            if not path.exists() and remaining(config.get('deadline')) < config['timeout_seconds'] + 10:
                print('Deadline: no new 1200-second trial can finish within the work window', flush=True)
                break
            print(f'[{index}/{len(jobs)}] pass1 {job["job_id"]}', flush=True)
            result = run_trial(config, job, config['timeout_seconds'], 'pass1_1200s', campaign, root, provenance)
            print(f'  {result["decision"]}, states={result.get("states_discovered", "")}', flush=True)
            write_progress(config, jobs, campaign)
        # Retry only TIMEOUT first attempts, only after all first attempts are terminal.
        first = [read_trial(campaign / 'pass1_1200s' / 'runs' / job['job_id'] / 'meta.json') for job in jobs]
        if (config['series'] == 'e2' and config.get('retry_timeout_seconds') and not args.first_pass_only
                and all(row['status'] not in {'NOT_RUN', 'RUNNING', 'INCOMPLETE'} for row in first)):
            for job, previous in zip(jobs, first):
                if previous['status'] != 'TIMEOUT':
                    continue
                cap = config['retry_timeout_seconds']
                path = campaign / 'pass2_3600s' / 'runs' / job['job_id']
                if not path.exists() and remaining(config['retry_deadline']) < cap + 10:
                    print('Retry cutoff: retaining first-pass TO for remaining cells', flush=True)
                    break
                print('pass2 ' + job['job_id'], flush=True)
                result = run_trial(config, job, cap, 'pass2_3600s', campaign, root, provenance)
                print(f'  {result["decision"]}, states={result.get("states_discovered", "")}', flush=True)
                write_progress(config, jobs, campaign)
        write_progress(config, jobs, campaign)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)

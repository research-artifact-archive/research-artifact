#!/usr/bin/env python3
"""New, create-only 7200-second campaign; never overwrite the 1200-second evidence."""
import argparse, datetime as dt, fcntl, hashlib, json, os, signal, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PC2 = HERE.parent
E6 = PC2.parent
JAR = E6.parents[1] / 'ablation_20260928/jars/e1.jar'

def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat()

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def check():
    config = json.loads((HERE / 'config.json').read_text())
    manifest = json.loads((HERE / 'build/frozen_manifest.json').read_text())
    for name, expected in manifest['files'].items():
        assert sha(HERE / name) == expected, name
    for name, expected in manifest['original_pc2_files'].items():
        assert sha(PC2 / name) == expected, name
    assert sha(JAR) == config['jar_sha256'] == manifest['jar_sha256']
    assert [j['id'] for j in config['jobs']] == ['lazy_transfers', 'direct_full_none']
    return config, manifest

def command(config, job, out):
    return [config['java'], '-Xmx32g', '-Djava.awt.headless=true',
            '-Dmtsa.revised.otf.solver=' + job['solver'],
            '-Dmtsa.otf.contractMerge=' + job['merge'],
            '-Dmtsa.otf.lazyControllableBuckets=' + ('true' if job['solver'] == 'otf' else 'false'),
            '-Dmtsa.otf.guidedStateLimit=0', '-Dmtsa.otf.guidedQueryLimit=0',
            '-Dmtsa.otf.controllableActionOrder=endpoint_guided',
            '-cp', str(HERE / 'frozen/classes') + os.pathsep + str(JAR),
            'ltsa.updatingControllers.cli.Pc2DiagnosticRunner',
            '--lts', str(HERE / 'frozen/inputs/ProductionCell_Arms2_Calibration.lts'),
            '--target', 'UPDATE_CONTROLLER_PC2_CAL', '--output', str(out / 'output.txt'),
            '--transitions', str(out / 'transitions.txt'), '--transition-output', 'summary',
            '--diagnostic-output', str(out / 'certificate_summary.json')]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['preflight', 'run'])
    args = parser.parse_args()
    config, manifest = check()
    if args.phase == 'preflight':
        assert (HERE / 'build/preregistration.json').is_file()
        jobs = [dict(id=j['id'], command=command(config, j, HERE / 'raw' / j['id'])) for j in config['jobs']]
        save(HERE / 'build/preflight.json', dict(status='PASS', at=now(), jobs=jobs,
             scope='Static hashes and exact fixed-CLI command checks; no extra synthesis trial or Java invocation.'))
        print(json.dumps(dict(status='PASS', phase='preflight')), flush=True)
        return
    assert json.loads((HERE / 'build/preflight.json').read_text())['status'] == 'PASS'
    lock = (E6 / 'tools/jvm.lock').open('a+')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    save(HERE / 'raw/runner_started.json', dict(at=now(), pid=os.getpid(), jobs=config['jobs']))
    for index, job in enumerate(config['jobs'], 1):
        check()
        out = HERE / 'raw' / job['id']
        out.mkdir(parents=True, exist_ok=False)
        if dt.datetime.fromisoformat(now()) >= dt.datetime.fromisoformat(config['start_cutoff']):
            save(out / 'not_run.json', dict(at=now(), status='NOT_RUN', reason='7200-second trial cannot finish by the final-report deadline.'))
            continue
        argv = command(config, job, out)
        save(out / 'invocation.json', dict(at=now(), schedule_index=index, command=argv,
             host='mac', heap='32g', timeout_seconds=7200, timeout_scope='whole JVM',
             solver=job['solver'], merge=job['merge'], trial=1,
             input_sha256=config['input_sha256'], jar_sha256=config['jar_sha256'],
             diagnostic_class_sha256=config['diagnostic_class_sha256'],
             frozen_manifest_sha256=sha(HERE / 'build/frozen_manifest.json'),
             role='User-authorized separate extended-budget trial; prior 1200-second TO remains unchanged.'))
        started = time.monotonic()
        timed_out = False
        with (out / 'stdout.log').open('x') as stdout, (out / 'stderr.log').open('x') as stderr:
            proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
            save(out / 'process.json', dict(at=now(), pid=proc.pid, parent_pid=os.getpid()))
            print(json.dumps(dict(event='STARTED', at=now(), job=job['id'], pid=proc.pid)), flush=True)
            try:
                code = proc.wait(timeout=7200)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                code = proc.returncode
        save(out / 'completion.json', dict(at=now(), exit_code=code, timed_out=timed_out,
             wall_seconds=time.monotonic()-started,
             files={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
        print(json.dumps(dict(event='COMPLETED', at=now(), job=job['id'], exit_code=code, timed_out=timed_out)), flush=True)
    check()
    save(HERE / 'raw/runner_finished.json', dict(at=now(), jobs=[j['id'] for j in config['jobs']]))
    print('FINISHED', flush=True)

if __name__ == '__main__':
    main()

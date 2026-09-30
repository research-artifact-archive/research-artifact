#!/usr/bin/env python3
"""Frozen, create-only, serial E6 measurement harness using the existing E1 JAR."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
E6 = Path(__file__).resolve().parent.parent
JAR = E6.parents[1]/'ablation_20260928/jars/e1.jar'
JAR_SHA = 'ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
JAVA = '/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home/bin/java'
JST = dt.timezone(dt.timedelta(hours=9))


def now(): return dt.datetime.now(JST).isoformat()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())


def save(path, data, create=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    if create:
        with path.open('x') as stream:
            json.dump(data, stream, indent=2);stream.write('\n')
    else:
        tmp = path.with_name(path.name+'.tmp')
        tmp.write_text(json.dumps(data, indent=2)+'\n');tmp.replace(path)


def configuration(family):
    c = read(family/'config.json')
    assert c['schema'] == 'e6-family-run-v1'
    assert c['heap'] == '32g' and c['timeout_seconds'] == 1200
    assert c.get('trials', 1) == 1
    jobs = c['jobs'];assert len({j['id'] for j in jobs}) == len(jobs)
    for j in jobs:
        assert j['solver'] in ('lazy', 'direct_full')
        assert j['merge'] in ('none', 'transfers', 'boundaries', 'both')
        assert '/' not in j['id'] and '..' not in j['id']
        p = (family/j['input']).resolve();assert p.is_relative_to(family)
        assert p.is_file()
        if 'compare_input' in j:
            p = (family/j['compare_input']).resolve();assert p.is_relative_to(family) and p.is_file()
    cutoff = dt.datetime.fromisoformat(c['start_cutoff'])
    deadline = dt.datetime.fromisoformat(c['deadline'])
    assert deadline-cutoff >= dt.timedelta(seconds=1260)
    return c


def make_manifest(family, config):
    paths = set([family/'config.json'])
    paths.update(family/j['input'] for j in config['jobs'])
    paths.update(family/j['compare_input'] for j in config['jobs'] if 'compare_input' in j)
    paths.update(family/j['compare_input'] for j in config.get('preflight_job_options', {}).values() if 'compare_input' in j)
    paths.update(E6/p for p in config.get('frozen_paths', []))
    paths.update((E6/'tools').glob('*.py'))
    paths.update((E6/'common').glob('*.java'))
    paths.update((E6/'common/build/classes').rglob('*.class'))
    assert any(p.suffix == '.class' for p in paths), 'Compile adapter before freeze.'
    for p in paths:
        assert p.resolve().is_relative_to(E6) and p.is_file(), str(p)
    assert digest(JAR) == JAR_SHA
    return dict(created_at=now(), family=config['family'], version=config['version'],
                config=config, jar_path=str(JAR), jar_sha256=JAR_SHA,
                java=JAVA, java_version=subprocess.check_output([JAVA, '-version'], stderr=subprocess.STDOUT, text=True),
                files={str(p.relative_to(E6)):digest(p) for p in sorted(paths)},
                timeout_scope='whole JVM including preparation, synthesis, checking, linking, and diagnostics',
                schedule=config['jobs'])


def verify(family):
    m = read(family/'build/frozen_manifest.json')
    assert read(family/'config.json') == m['config'], 'Config changed after freeze.'
    assert digest(JAR) == m['jar_sha256'] == JAR_SHA
    for relative, expected in m['files'].items():
        assert digest(E6/relative) == expected, 'Frozen file changed: '+relative
    return m


def lock_jvm():
    stream = (E6/'tools/jvm.lock').open('a+')
    try: fcntl.flock(stream.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close();raise RuntimeError('Another E6 JVM series holds the lock; no second JVM started.')
    return stream


def execute(family, config, job, directory):
    directory.mkdir(parents=True, exist_ok=False)
    path = family/job['input']
    command = [JAVA, '-Xmx'+config['heap'], '-cp', str(E6/'common/build/classes')+os.pathsep+str(JAR),
               'WitnessDriver', '--input', str(path), '--merge', job['merge'], '--solver', job['solver'],
               '--output', str(directory/'result.json')]
    if 'compare_input' in job:
        command += ['--compare-input', str(family/job['compare_input']), '--compare-merge', job.get('compare_merge','none')]
    invocation = dict(started_at=now(), command=command, job=job, input_sha256=digest(path), jar_sha256=JAR_SHA,
                      frozen_manifest_sha256=digest(family/'build/frozen_manifest.json'),
                      timeout_seconds=config['timeout_seconds'], heap=config['heap'])
    save(directory/'invocation.json', invocation)
    start = time.monotonic();timeout = False;code = None;exception = None
    with (directory/'stdout.log').open('x') as stdout, (directory/'stderr.log').open('x') as stderr:
        try:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            try: code = process.wait(timeout=config['timeout_seconds'])
            except subprocess.TimeoutExpired:
                timeout = True;os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL);process.wait()
                code = process.returncode
        except Exception as exc: exception = type(exc).__name__+': '+str(exc)
    completion = dict(finished_at=now(), wall_seconds=time.monotonic()-start, timed_out=timeout,
                      exit_code=code, exception=exception,
                      files={p.name:digest(p) for p in directory.iterdir() if p.is_file()})
    save(directory/'completion.json', completion)
    return completion


def analyze(family):
    command = [sys.executable, '-B', str(E6/'tools/analyze_family.py'), str(family)]
    proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(proc.stdout, end='', flush=True)
    # Analysis failure is retained, but does not discard or select measurement jobs.
    if proc.returncode:
        logdir = family/'build/analysis_failures';logdir.mkdir(parents=True, exist_ok=True)
        (logdir/(dt.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')).write_text(proc.stdout)
    return proc.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('family', type=Path)
    parser.add_argument('phase', choices=['freeze', 'preflight', 'run', 'analyze', 'audit'])
    args = parser.parse_args();family = args.family.resolve()
    assert family.is_relative_to(E6) and family != E6
    if args.phase == 'analyze': return analyze(family)
    config = configuration(family)
    if args.phase == 'freeze':
        save(family/'build/frozen_manifest.json', make_manifest(family, config))
        print('FROZEN '+digest(family/'build/frozen_manifest.json'));return 0
    manifest = verify(family)
    if args.phase == 'audit':
        print(json.dumps({'status':'PASS', 'at':now(), 'files':len(manifest['files']), 'jar_sha256':JAR_SHA}));return 0
    if args.phase == 'preflight':
        result = {'started_at':now(), 'checks':[], 'issues':[]}
        for command in config.get('endpoint_checks', []):
            p = subprocess.run(command, cwd=E6, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            result['checks'].append({'command':command, 'exit_code':p.returncode, 'output':p.stdout})
            if p.returncode: result['issues'].append('Endpoint check failed.')
        if not result['issues']:
            with lock_jvm():
                for identifier in config.get('preflight_jobs', []):
                    job = dict(next(j for j in config['jobs'] if j['id'] == identifier))
                    job.update(config.get('preflight_job_options', {}).get(identifier, {}))
                    verify(family);directory = family/'raw/preflight'/identifier
                    completion = execute(family, config, job, directory)
                    data = read(directory/'result.json') if (directory/'result.json').exists() else {}
                    ok = not completion['timed_out'] and completion['exit_code'] in (0, 2) and data.get('certificate_checker') == 'PASS'
                    ok = ok and (data.get('decision') != 'WIN' or data.get('link_checker') == 'PASS')
                    result['checks'].append({'job':identifier, 'status':'PASS' if ok else 'FAIL'})
                    if not ok: result['issues'].append('Preflight trial failed: '+identifier)
        result.update(finished_at=now(), status='FAIL' if result['issues'] else 'PASS')
        save(family/'validation/preflight.json', result);print(json.dumps(result));return bool(result['issues'])
    assert read(family/'validation/preflight.json')['status'] == 'PASS'
    with lock_jvm():
        raw = family/'raw/series';raw.mkdir(parents=True, exist_ok=False)
        save(family/'raw/runner_started.json', {'at':now(), 'pid':os.getpid(), 'manifest_sha256':digest(family/'build/frozen_manifest.json')})
        for index, job in enumerate(config['jobs'], 1):
            verify(family)
            if dt.datetime.now(JST) >= dt.datetime.fromisoformat(config['start_cutoff']):
                save(family/'raw/deadline_reached.json', {'at':now(), 'next_job':job['id'], 'reason':'Predeclared start cutoff.'})
                break
            print(json.dumps({'event':'start', 'at':now(), 'index':index, 'job':job['id']}), flush=True)
            completion = execute(family, config, job, raw/job['id'])
            print(json.dumps({'event':'finished', 'job':job['id'], **completion}), flush=True)
            analyze(family)
        verify(family)
        save(family/'raw/runner_finished.json', {'at':now(), 'manifest_sha256':digest(family/'build/frozen_manifest.json')})
        return analyze(family)


if __name__ == '__main__': raise SystemExit(main())

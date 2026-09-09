"""Run the fixed JMH cells once, with separate logs and complete status accounting."""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import json
import os
import platform
import random
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
JAVA = Path('/opt/homebrew/opt/openjdk@17/bin/java')
JAR = HERE / 'bench/target/benchmarks.jar'
METHODS = ('get', 'prepare', 'replaceMatch', 'replaceMismatch',
           'validateCallbackMatch', 'validateCallbackMismatch', 'freshCallback')
CAP = 1200
CELL_CAP = 60
STOP = datetime.datetime(2026, 9, 9, 4, 50, tzinfo=datetime.timezone.utc).timestamp()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def prepare():
    cells = [dict(id=f'{layout}-{length}-{method}', layout=layout, length=length, method=method)
             for layout in ('distinct', 'colliding') for length in (1, 8, 64, 512) for method in METHODS]
    random.Random(202609090559).shuffle(cells)
    assert len(cells) == 56
    files = [HERE / 'PLAN.md', HERE / 'run.py', HERE / 'analyze.py', HERE / 'bench/pom.xml', JAR,
             HERE / 'THIRD_MODE_PRICE_REGION_DRAFT.md']
    files.extend(sorted((HERE / 'bench/src').rglob('*.java')))
    save(HERE / 'CELLS.json', cells)
    files.append(HERE / 'CELLS.json')
    manifest = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    classification='exploratory average-time API calibration, not a worst-case guarantee',
                    cells=56, forks_per_cell=2, retained_iterations_per_fork=5,
                    warmup_iterations_per_fork=3, iteration_time='200ms', threads=1,
                    java_version=subprocess.check_output([str(JAVA), '-version'], stderr=subprocess.STDOUT, text=True),
                    java_sha256=sha(JAVA.resolve()), platform=platform.platform(),
                    files={str(path): sha(path) for path in files},
                    cell_cap_seconds=CELL_CAP, total_cap_seconds=CAP, stop_before_utc=STOP,
                    untimed_sanity='8 states and all7 primitive paths checked before timings; separate NativeCalibrationCheck',
                    output='all per-cell stdout/stderr, JSON samples, errors and missing cells retained')
    save(HERE / 'MANIFEST.json', manifest)
    print('Fixed56 cells,112 forks,560 retained iteration measurements; no timing outcome read.')


def terminate(process):
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def run():
    manifest = json.loads((HERE / 'MANIFEST.json').read_text())
    for path, digest in manifest['files'].items():
        assert sha(path) == digest, ('input changed', path)
    cells = json.loads((HERE / 'CELLS.json').read_text())
    output = HERE / 'attempt01'
    output.mkdir(exist_ok=False)
    start = time.monotonic()
    save(output / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                        manifest_sha256=sha(HERE / 'MANIFEST.json'), pid=os.getpid()))
    results = []
    for index, cell in enumerate(cells):
        directory = output / cell['id']
        directory.mkdir()
        row = dict(cell, ordinal=index)
        seconds_left = min(CAP - (time.monotonic() - start), STOP - time.time())
        if seconds_left <= 0:
            row.update(status='NOT_RUN', reason='fixed campaign/stop cap')
            save(directory / 'RESULT.json', row)
            results.append(row)
            continue
        argv = [str(JAVA), '-jar', str(JAR), r'^org\.anonymous\.retry\.MyBenchmark\.' + cell['method'] + '$',
                '-p', f"length={cell['length']}", '-p', f"layout={cell['layout']}",
                '-f', '2', '-wi', '3', '-w', '200ms', '-i', '5', '-r', '200ms', '-t', '1',
                '-jvm', str(JAVA), '-to', '20s', '-foe', 'true', '-rf', 'json',
                '-rff', str(directory / 'JMH.json')]
        row.update(argv=argv, start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save(directory / 'INPUT.json', row)
        began = time.monotonic()
        with (directory / 'STDOUT.log').open('xb') as stdout, (directory / 'STDERR.log').open('xb') as stderr:
            process = subprocess.Popen(argv, cwd=HERE / 'bench', stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            save(directory / 'PROCESS.json', dict(pid=process.pid, pgid=process.pid))
            try:
                code = process.wait(timeout=min(CELL_CAP, seconds_left))
                row.update(exit_code=code, status='SUCCESS' if code == 0 else 'FAILURE')
            except subprocess.TimeoutExpired:
                terminate(process)
                row.update(status='TIMEOUT', reason='fixed cell/campaign cap')
            except BaseException:
                terminate(process)
                raise
        row['wall_seconds'] = time.monotonic() - began
        row['end_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if (directory / 'JMH.json').is_file():
            row['jmh_sha256'] = sha(directory / 'JMH.json')
            try:
                data = json.loads((directory / 'JMH.json').read_text())
                assert len(data) == 1
                record = data[0]
                assert record['benchmark'] == 'org.anonymous.retry.MyBenchmark.' + cell['method']
                assert record['params'] == dict(length=str(cell['length']), layout=cell['layout'])
                samples = record['primaryMetric']['rawData']
                assert len(samples) == 2 and all(len(fork) == 5 for fork in samples)
                assert all(value > 0 for fork in samples for value in fork)
                row['retained_samples'] = sum(map(len, samples))
            except Exception as error:
                if row['status'] == 'SUCCESS':
                    row.update(status='INVALID', reason=repr(error))
        elif row['status'] == 'SUCCESS':
            row.update(status='INVALID', reason='missing JMH output')
        save(directory / 'RESULT.json', row)
        results.append(row)
        print(f"{index + 1}/56 {cell['id']} {row['status']} {row['wall_seconds']:.2f}s", flush=True)
    save(output / 'RESULTS.json', results)
    summary = dict(denominator=56, partition=dict(collections.Counter(row['status'] for row in results)),
                   wall_seconds=time.monotonic() - start, reused_or_retried_cells=0,
                   retained_samples=sum(row.get('retained_samples', 0) for row in results),
                   end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save(output / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run'))
    arguments = parser.parse_args()
    {'prepare': prepare, 'run': run}[arguments.command]()

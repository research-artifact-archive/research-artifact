#!/usr/bin/env python3
"""Compile the finite-model adapter and run one contract in a new directory.

Requires JDK 17 and a locally built E1-compatible solver JAR. No JAR is
downloaded or distributed. The saved campaign, drivers, and inputs are never
edited. Every result is a user replication, separate from published timings.

Exit codes: 0 checked WIN, 2 checked LOSS, 124 timeout, 1 other failure.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def utc():
    return datetime.now(timezone.utc).isoformat()


def execute(command, cwd, timeout, stdout, stderr):
    started = time.monotonic()
    with stdout.open('x', encoding='utf-8') as out, stderr.open('x', encoding='utf-8') as err:
        try:
            process = subprocess.run(command, cwd=cwd, stdout=out, stderr=err, timeout=timeout)
            return {'exit_code': process.returncode, 'timed_out': False,
                    'wall_seconds': time.monotonic() - started}
        except subprocess.TimeoutExpired:
            # subprocess.run terminates and waits for the direct child. The
            # adapter launches no processes, and this runner uses no shell.
            return {'exit_code': None, 'timed_out': True,
                    'wall_seconds': time.monotonic() - started}


def verify_result(output, jar_hash, input_hash, exit_code):
    result = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    proof = json.loads((output / 'certificate.json').read_text(encoding='utf-8'))
    decision = result.get('decision')
    if decision not in ('WIN', 'LOSS') or proof.get('decision') != decision:
        raise ValueError('Missing or inconsistent result/certificate decision')
    if exit_code != (0 if decision == 'WIN' else 2):
        raise ValueError('JVM exit code does not match the decision')
    if result.get('jar_sha256') != jar_hash or proof.get('jar_sha256') != jar_hash:
        raise ValueError('Result/certificate does not identify the actual solver JAR')
    if result.get('input_sha256') != input_hash:
        raise ValueError('Result does not identify the supplied finite input')
    if result.get('certificate_sha256') != digest(output / 'certificate.json'):
        raise ValueError('Serialized certificate digest differs')
    if result.get('certificate_checker') != 'PASS' or result.get('endpoint_checker') != 'PASS':
        raise ValueError('Native certificate/endpoint checking did not pass')
    if decision == 'WIN' and result.get('link_checker') != 'PASS':
        raise ValueError('Winning result did not pass the native Link check')
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', required=True, type=Path, help='local E1-compatible solver JAR')
    parser.add_argument('--input', required=True, type=Path, help='finite fg-ducs-witness-v1 JSON contract')
    parser.add_argument('--driver-source', required=True, type=Path,
                        help='directory containing WitnessDriver.java and GeneratedContractInput.java')
    parser.add_argument('--output', required=True, type=Path, help='new result directory; existing paths are refused')
    parser.add_argument('--merge', choices=('none', 'transfers', 'boundaries', 'both'), default='none')
    parser.add_argument('--solver', choices=('lazy', 'direct_full'), default='lazy')
    parser.add_argument('--compare-input', type=Path, help='optional independently generated grouped contract')
    parser.add_argument('--compare-merge', choices=('none', 'transfers', 'boundaries', 'both'), default='none')
    parser.add_argument('--heap', default='2g', help='maximum Java heap (default: 2g)')
    parser.add_argument('--timeout', type=float, default=60, help='whole-JVM limit in seconds (default: 60)')
    parser.add_argument('--java', default='java', help='JDK 17 java executable')
    parser.add_argument('--javac', default='javac', help='JDK 17 javac executable')
    args = parser.parse_args()
    if not re.fullmatch(r'[1-9][0-9]*[kKmMgG]?', args.heap):
        parser.error('--heap must be a positive Java heap size such as 2g')
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be a positive finite number')
    if args.compare_input is None and args.compare_merge != 'none':
        parser.error('--compare-merge requires --compare-input')
    paths = {'jar': args.jar.resolve(), 'input': args.input.resolve(),
             'driver': args.driver_source.resolve() / 'WitnessDriver.java',
             'adapter': args.driver_source.resolve() / 'GeneratedContractInput.java'}
    if args.compare_input is not None:
        paths['compare_input'] = args.compare_input.resolve()
    for label, path in paths.items():
        if not path.is_file():
            parser.error(label + ' is not an existing file: ' + str(path))
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        parser.error('Output already exists; choose a new directory: ' + str(output))
    original = {name: digest(path) for name, path in paths.items()}
    driver_text = paths['driver'].read_text(encoding='utf-8')
    driver_text, replacements = re.subn(
        r'(public static final String E1_SHA\s*=\s*")[0-9a-f]{64}(";)',
        lambda m: m[1] + original['jar'] + m[2], driver_text)
    if replacements != 1:
        parser.error('Expected exactly one documented E1_SHA declaration in WitnessDriver.java')
    output.mkdir(parents=True, exist_ok=False)
    output = output.resolve()
    build = output / 'build'
    source = build / 'src'
    classes = build / 'classes'
    source.mkdir(parents=True)
    classes.mkdir()
    (source / 'WitnessDriver.java').write_text(driver_text, encoding='utf-8')
    shutil.copyfile(paths['adapter'], source / 'GeneratedContractInput.java')
    shutil.copyfile(paths['input'], output / 'input.json')
    if args.compare_input is not None:
        shutil.copyfile(paths['compare_input'], output / 'compare-input.json')
    record = {
        'schema': 'fg-ducs-user-replication-v1',
        'run_kind': 'user_replication', 'published_measurement': False,
        'started_utc': utc(), 'status': 'PREPARING',
        'sources': {name: {'path': str(path), 'sha256': original[name]} for name, path in paths.items()},
        'adapter_change': 'Only the copied WitnessDriver E1_SHA literal is set to the actual local JAR SHA-256.',
        'compiled_driver_sha256': digest(source / 'WitnessDriver.java'),
        'heap': args.heap, 'timeout_seconds': args.timeout,
        'timeout_scope': 'whole JVM; compilation is separate (60-second limit)',
        'merge': args.merge, 'solver': args.solver,
        'comparison_scope': 'Functional replication only; never pooled with archived paper measurements.',
    }
    save(output / 'replication.json', record)
    exit_code = 1
    try:
        command = [args.javac, '--release', '17', '-cp', str(paths['jar']), '-d', str(classes),
                   str(source / 'WitnessDriver.java'), str(source / 'GeneratedContractInput.java')]
        record['compile_command'] = command
        save(output / 'replication.json', record)
        compiled = execute(command, output, 60, build / 'javac.stdout.log', build / 'javac.stderr.log')
        record['compile'] = compiled
        if compiled['timed_out'] or compiled['exit_code'] != 0:
            raise RuntimeError('Adapter compilation failed; see build/javac.stderr.log')
        command = [args.java, '-Xmx' + args.heap, '-Djava.awt.headless=true', '-cp',
                   str(classes) + os.pathsep + str(paths['jar']), 'WitnessDriver',
                   '--input', str(output / 'input.json'), '--merge', args.merge,
                   '--solver', args.solver, '--output', str(output / 'result.json')]
        if args.compare_input is not None:
            command += ['--compare-input', str(output / 'compare-input.json'), '--compare-merge', args.compare_merge]
        record['command'] = command
        record['status'] = 'RUNNING'
        save(output / 'replication.json', record)
        record['execution'] = execute(command, output, args.timeout,
                                      output / 'stdout.log', output / 'stderr.log')
        if record['execution']['timed_out']:
            record['status'] = 'TIMEOUT'
            record['decision'] = None
            exit_code = 124
        elif record['execution']['exit_code'] not in (0, 2):
            record['status'] = 'ERROR'
            record['decision'] = None
            record['error'] = 'JVM did not return a checked decision; inspect stdout.log and stderr.log.'
        else:
            decision = verify_result(output, original['jar'], original['input'], record['execution']['exit_code'])
            record['status'] = 'CHECKED_' + decision
            record['decision'] = decision
            exit_code = 0 if decision == 'WIN' else 2
    except Exception as error:
        record['status'] = 'ERROR'
        record['decision'] = None
        record['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        changed = [name for name, path in paths.items() if not path.is_file() or digest(path) != original[name]]
        record['source_files_unchanged'] = not changed
        if changed:
            record['status'] = 'ERROR'
            record['decision'] = None
            record['error'] = 'Source inputs changed during execution: ' + ', '.join(changed)
            exit_code = 1
        record['finished_utc'] = utc()
        record['output_files'] = {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                                  for p in sorted(output.iterdir()) if p.is_file() and p.name != 'replication.json'}
        save(output / 'replication.json', record)
    print(json.dumps({'status': record['status'], 'decision': record.get('decision'),
                      'published_measurement': False, 'output': str(output),
                      'jar_sha256': original['jar'], 'source_files_unchanged': record['source_files_unchanged']}))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

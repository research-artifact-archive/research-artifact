#!/usr/bin/env python3
"""Recheck the supplement's saved evidence in a new copy; never run Java."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SUB = Path('FSE2027_SUBMISSION_20260914')


def value(path):
    if path.suffix == '.csv':
        with path.open(newline='') as stream:
            return list(csv.DictReader(stream))
    if path.suffix == '.json':
        return json.loads(path.read_text())
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package, output = args.package.resolve(), args.output.resolve()
    source = package / 'evidence'
    if output == source or source in output.parents:
        parser.error('Output must be outside the saved evidence tree')
    output.mkdir(parents=True, exist_ok=False)
    copied = output / 'evidence'
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
    shutil.copytree(source, copied, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    logs = output / 'logs'; logs.mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0', FGDUCS_PACKAGE_ROOT=str(package))
    tasks = [
        ('r1-entry', 'verify_r1_entry_invariant.py', ['r1-entry-invariant-verification.csv']),
        ('completion-ranks', 'summarize_completion_ranks.py', ['completion_ranks.csv', 'completion_ranks_summary.json']),
        ('railcab-base', 'railcab_policy_demo/extract_policy_fragment.py', ['railcab_policy_demo/policy-fragment.json', 'railcab_policy_demo/policy-fragment-edges.csv', 'railcab_policy_demo/policy-fragment-states.csv']),
        ('railcab-r1', 'railcab_r1_policy_demo/extract_policy_fragment.py', ['railcab_r1_policy_demo/policy-fragment.json', 'railcab_r1_policy_demo/policy-fragment-edges.csv', 'railcab_r1_policy_demo/policy-fragment-states.csv']),
        ('railcab-stop-brake', 'extract_railcab_stop_brake_paths.py', ['railcab_stop_brake_paths.csv']),
        ('frontend-lookup', 'frontend_lookup_demo/verify_saved.py', ['frontend_lookup_demo/lookup_check_summary.csv', 'frontend_lookup_demo/negative_checks.json', 'frontend_lookup_demo/verification_details.json']),
        ('quiescent-goal', 'quiescent_goal_demo/verify_saved.py', ['quiescent_goal_demo/summary.csv', 'quiescent_goal_demo/independent_oracle.json']),
        ('load-target', 'load_target_selector_demo/verify_saved.py', ['load_target_selector_demo/summary.csv', 'load_target_selector_demo/independent_oracle.json']),
    ]
    started = time.monotonic()
    def run(name, command):
        result = subprocess.run(command, cwd=output, env=env, capture_output=True, text=True, timeout=300)
        text = result.stdout + result.stderr
        for path, replacement in [(str(output), '<OUTPUT>'), (str(package), '<PACKAGE>'), (str(Path.home()), '<USER_HOME>')]:
            text = text.replace(path, replacement)
        (logs / (name + '.log')).write_text(text + '\nEXIT: ' + str(result.returncode) + '\n')
        if result.returncode:
            raise RuntimeError(name + ' failed; see ' + str(logs / (name + '.log')))
        return text
    for name, script, generated in tasks:
        run(name, [sys.executable, '-B', str(copied / script)])
        for relative in generated:
            assert value(copied / relative) == value(source / relative), ('saved output differs', relative)
        print('PASS:', name, '(' + str(len(generated)) + ' saved outputs agree)', flush=True)
        if name == 'r1-entry':
            rows = value(copied / generated[0])
            passed = sum(row['static_entry_invariant_condition'] == 'PASS' for row in rows)
            print('PASS: guarded-invariant saved CSV revalidated:', str(passed) + '/' + str(len(rows)), flush=True)
    macro_output = run('editorial-numbers', [sys.executable, '-B', str(copied / 'generate_editorial_numbers.py'),
                             '--generated', str(package / SUB / 'paper/build/generated'),
                             '--evidence', str(copied), '--output', str(output / 'generated')])
    print(macro_output.rstrip(), flush=True)
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, ('saved evidence changed', path)
    print('PASS: all', len(before), 'saved evidence files unchanged; no JVM invoked')
    print('ELAPSED_SECONDS:', round(time.monotonic() - started, 3))


if __name__ == '__main__':
    main()

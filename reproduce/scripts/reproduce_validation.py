#!/usr/bin/env python3
"""Reproduce validation in a fresh directory, preserving the distributed runs."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'FSE2027_SUBMISSION_20260914/experiments/semantic_revision_20260914'
SCRIPTS = ROOT / 'Implementation/Experiment/FSE2027/scripts'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['rq1', 'rq2'])
    parser.add_argument('--java', default='java')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--derive-only', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    relative = output.relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=False)
    if args.derive_only and args.phase == 'rq1':
        inputs = ROOT / 'Implementation/Experiment/FSE2027/results/macos24-paper-final-20260805g-correctness/inputs'
        subprocess.run([sys.executable, str(BASE / 'rederive_oracle.py'),
                        '--semantic-dir', str(inputs / 'semantic_boundaries_v2/Models'),
                        '--contract-dir', str(inputs / 'contract_gate/Models'),
                        '--output', str(output)], cwd=ROOT, check=True)
        return
    if args.derive_only:
        # Load only the original module's definitions, before its output-writing
        # driver. The derive() function and all semantic operations are unchanged.
        source_path = BASE / 'derive_rq2_expectations.py'
        source = source_path.read_text()
        marker = '\nrows=[]\n'
        if source.count(marker) != 1:
            raise ValueError('Expected the known oracle module layout')
        namespace = {'__file__': str(source_path), '__name__': 'rq2_definitions'}
        exec(compile(source.split(marker)[0], str(source_path), 'exec'), namespace)
        rows = []
        for model in namespace['CONFIG']['models']:
            for method in model.get('method_ids', [m['id'] for m in namespace['CONFIG']['methods']]):
                result = namespace['derive'](ROOT / model['path'], method)
                rows.append(dict(model_id=model['id'], method_id=method, **result))
        with (output / 'expected.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(json.dumps({'jobs': len(rows), 'WIN': sum(r['expected_decision'] == 'WIN' for r in rows),
                          'LOSS': sum(r['expected_decision'] == 'LOSS' for r in rows)}))
        return
    config = json.loads((BASE / args.phase / 'raw/config.json').read_text())
    java = shutil.which(args.java)
    if java is None:
        raise FileNotFoundError('JDK executable not found: ' + args.java)
    config['java'] = java
    config['results_root'] = relative.as_posix()
    # The saved settings describe the source host. Replication may use another
    # host; semantic method properties, cases, limits, and seeds remain intact.
    config.pop('host_requirements', None)
    # Metadata manifests have redacted personal paths. Validate unchanged model
    # bytes through their per-model digests instead of historical metadata hashes.
    config.pop('generated_input_manifests', None)
    config_path = output / 'replication-config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    command = [sys.executable, str(SCRIPTS / 'run_experiment.py'), '--config', str(config_path)]
    if args.plan_only:
        command += ['--dry-run']
    else:
        command += ['--run-id', 'fresh']
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()

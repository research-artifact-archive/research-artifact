#!/usr/bin/env python3
"""Reproduce the three C143 saved-evidence analyses and compare every output."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def compare_json(actual, saved, volatile=()):
    left, right = (json.loads(p.read_text()) for p in (actual, saved))
    for key in volatile:
        require(key in left and key in right, 'Missing temporary-directory field: ' + key)
        del left[key]; del right[key]
    require(left == right, 'Recomputed output differs from ' + saved.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True, help='A fresh output directory')
    args = parser.parse_args()
    root, output = args.artifact_root.resolve(), args.output.resolve()
    evidence = root/'paper/source/evidence'
    if output.exists():
        parser.error('Choose a fresh output directory')
    if evidence == output or evidence in output.parents:
        parser.error('Write outputs outside paper/source/evidence')
    before = snapshot(evidence)
    output.mkdir(parents=True)
    logs = output/'logs'; logs.mkdir()
    checks = []

    def run(name, command):
        result = subprocess.run([sys.executable, '-B', *map(str, command)],
                                cwd=root, text=True, capture_output=True)
        (logs/(name+'.stdout.txt')).write_text(result.stdout)
        (logs/(name+'.stderr.txt')).write_text(result.stderr)
        require(result.returncode == 0, name + ' failed; inspect the output logs')

    try:
        # Bind every copied input to the full public archive, including the
        # older unfavorable measurements; analysis-local copies are not new data.
        copied = 0
        for name in ('railcab_saved_activation', 'command_observation'):
            inputs = evidence/name/'inputs'
            for path in sorted(inputs.rglob('*')):
                if path.is_file():
                    source = root/path.relative_to(inputs)
                    require(source.is_file() and source.read_bytes() == path.read_bytes(),
                            'Copied input differs from public archive: ' + str(path.relative_to(evidence)))
                    copied += 1
        threads = evidence/'threads_saved_serialization'
        provenance = json.loads((threads/'provenance.json').read_text())
        # The checker verifies the provenance structure; copied_file identifies
        # its local input and public_release.file identifies the published data.
        for case in provenance['cases']:
            for row in case['files'].values():
                source = root/row['public_release']['file']
                require(source.is_file() and source.read_bytes() == (threads/row['copied_file']).read_bytes(),
                        'Threads input differs from public archive: ' + row['copied_file'])
                copied += 1
        checks.append({'check': 'copied_inputs_match_public_archive', 'status': 'PASS', 'files': copied})

        for name, script, volatile in (
            ('railcab_saved_activation', 'analyze_saved_railcab.py', ('temporary_run_name',)),
            ('command_observation', 'analyze_command_observation.py', ('temporary_inputs',)),
        ):
            saved = evidence/name
            fresh = output/name; fresh.mkdir()
            run(name, [saved/script, '--artifact-root', saved/'inputs', '--output', fresh/'analysis.json'])
            compare_json(fresh/'analysis.json', saved/'analysis.json')
            run(name+'_controls', [saved/'test_negative_controls.py', '--artifact-root', saved/'inputs',
                '--output', fresh/'negative_controls.json', '--work-dir', fresh/'negative_control_runs'])
            compare_json(fresh/'negative_controls.json', saved/'negative_controls.json', volatile)
            controls = json.loads((fresh/'negative_controls.json').read_text())
            require(controls['status'] == 'PASS' and controls['originals_unchanged'], 'Negative controls failed')
            checks.append({'check': name, 'status': 'PASS', 'analysis_all_fields_equal': True,
                           'negative_controls_all_fields_equal_except': list(volatile),
                           'controls': len(controls['controls'])})
            print('PASS: ' + name, flush=True)

        fresh = output/'threads_saved_serialization'
        run('threads_saved_serialization', [threads/'check_saved_serialization.py', '--root', threads, '--output', fresh])
        actual, saved = snapshot(fresh), snapshot(threads/'output')
        require(actual == saved, 'Threads generated files differ from saved output')
        summary = json.loads((fresh/'summary.json').read_text())
        require(summary['status'] == 'PASS' and summary['cases'] == 10 and summary['negative_controls_passed'] == 50,
                'Threads population or controls changed')
        checks.append({'check': 'threads_saved_serialization', 'status': 'PASS',
                       'byte_identical_output_files': len(saved), 'cases': 10, 'negative_controls': 50})
        print('PASS: threads_saved_serialization', flush=True)
    except Exception as error:
        checks.append({'check': 'reproduction', 'status': 'FAIL', 'reason': str(error)})
    unchanged = snapshot(evidence) == before
    passed = unchanged and all(row['status'] == 'PASS' for row in checks)
    report = {'status': 'PASS' if passed else 'FAIL', 'checks': checks,
              'distributed_evidence_unchanged': unchanged,
              'scope': 'Static saved-input analysis only; no Java, synthesis, controller execution or performance measurement.',
              'limits': 'Command/reset projections are not observed activations; Railcab assumes saved old-entry vectors; Threads uses related identity-transfer instances with empty requirements.'}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    if not passed:
        raise SystemExit('FAIL: inspect ' + str(output/'report.json'))
    print('PASS: all three saved analyses and their controls reproduce; distributed inputs unchanged.')


if __name__ == '__main__':
    main()

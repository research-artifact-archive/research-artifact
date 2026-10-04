#!/usr/bin/env python3
"""Replay one positive and three negative controls on copies of saved inputs.

No Java, synthesis, performance measurement, or original-input modification.
Every run gets a fresh temporary directory, retained for inspection.
"""
from pathlib import Path
import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

FILES = [
    'results/supplement-checks/railcab_policy_demo/handoff-bundle.json',
    'results/supplement-checks/railcab_r1_policy_demo/handoff-bundle.json',
    'results/supplement-checks/frontend_lookup_demo/runs/railcab__base/lookup.json',
    'results/supplement-checks/frontend_lookup_demo/runs/railcab__r1/lookup.json',
    'results/initialization/raw/expanded-predicates/railcab.json',
    'results/supplement-checks/source_invariant_lookup/analyze_new_invariants.py',
    'tool/models/Railcab_FG.lts',
]
BASE = FILES[0]
REQUIREMENT = 'P_CHECK_STATUS_AFTER_APPROACHING_CROSSING'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def mutate(bundle, control):
    states = {s['id']: s for s in bundle['configurations']}
    if control == 'positive_unchanged':
        return {'kind': 'none'}
    if control == 'wrong_installed_monitor':
        edge = next(e for e in bundle['strategy']
                    if e['source'] == 'M12' and e['action'] == 'startNewSpec_' + REQUIREMENT)
        need(len(edge['outcomes']) == 1 and edge['outcomes'][0]['target'] == 'M11',
             'Unexpected saved activation edge')
        target = states['M11']
        key = next(k for k in target['active_monitor_states'] if k.split(':')[1] == REQUIREMENT)
        before = target['active_monitor_states'][key]
        need(before == 0, 'Unexpected installed monitor state')
        target['active_monitor_states'][key] = 1
        return {'kind': control, 'state': 'M11', 'field': 'active_monitor_states.' + key,
                'before': before, 'after': 1, 'requirement': REQUIREMENT,
                'reason': 'Wrong but valid non-error monitor state for the saved start tuple'}
    if control == 'wrong_nonentry_observer':
        target = states['M0']
        roots = {r['root_configuration'] for r in bundle['q0_entries']}
        need('M0' not in roots and not target['initial'] and not target['goal'],
             'Mutation must not alter a seed or handover')
        need(not any(k.startswith('new:') for k in target['active_monitor_states']),
             'Mutation should isolate observer consistency from active truth')
        need(not any(e['action'].startswith('startNewSpec_') and
                     (e['source'] == 'M0' or any(o['target'] == 'M0' for o in e['outcomes']))
                     for e in bundle['strategy']), 'Mutation must not change an activation key')
        before = target['physical_state']
        matches = list(re.finditer(r'@\[([^\]]+)\]', before))
        need(len(matches) == 1, 'Unexpected physical-vector encoding')
        match = matches[0]
        values = [int(x.strip()) for x in match.group(1).split(',')]
        need(len(values) == 10 and values[0] == 0, 'Unexpected observer value')
        values[0] = 1
        after = before[:match.start(1)] + ', '.join(map(str, values)) + before[match.end(1):]
        target['physical_state'] = after
        return {'kind': control, 'state': 'M0', 'field': 'physical_state',
                'observer': 'ApproachingCrossingHappen', 'index': 0,
                'before': before, 'after': after,
                'reason': 'One nonentry saved observer bit disagrees with source propagation'}
    if control == 'unsafe_post_observation':
        target = next(s for s in bundle['post_states'] if s['id'] == 'N1')
        need(any(h['post_state_id'] == 'N1' for h in bundle['handoffs']),
             'Mutation source must be selected by a saved handover')
        edge = next(e for e in target['transitions'] if e['action'] == 'idle_c')
        need(edge['outcomes'] == ['N2'], 'Unexpected saved post edge')
        edge['action'] = 'brake'
        return {'kind': control, 'state': 'N1', 'target': 'N2', 'field': 'transitions.action',
                'before': 'idle_c', 'after': 'brake',
                'requirement': 'P_BRAKE_IF_SOMETHING_BAD',
                'reason': 'Braking with CantEnter=false and NotWorking=false violates the source invariant'}
    raise ValueError('Unknown control: ' + control)


def execute(checker, stage, control):
    output = stage.parent / (control + '_analysis.json')
    command = [sys.executable, '-B', str(checker), '--artifact-root', str(stage), '--output', str(output)]
    completed = subprocess.run(command, text=True, capture_output=True, timeout=60)
    need(output.exists(), f'{control}: checker did not produce its normal report: {completed.stderr}')
    report = json.loads(output.read_text())
    reports = {r['variant']: r for r in report['reports']}
    base, r1 = reports['base'], reports['r1']
    diffs = base['source_replay']['physical_reference_differences']
    issues = base['issues']
    bad_tables = [x for x in base['start_rows'] if not x['table_match']]
    need(r1['status'] == 'PASS', f'{control}: unmodified R1 should remain PASS')
    if control == 'positive_unchanged':
        passed = completed.returncode == 0 and base['status'] == 'PASS' and not issues and not diffs
        detection = []
    elif control == 'wrong_installed_monitor':
        detection = [x for x in issues if x['kind'] == 'reference_activation_mismatch'
                     and x['target'] == 'M11' and x['requirement'] == REQUIREMENT]
        passed = completed.returncode == 1 and base['status'] == 'MISMATCH' and bool(detection) and bool(bad_tables)
    elif control == 'wrong_nonentry_observer':
        detection = [x for x in diffs if x['phase'] == 'update' and x['state'] == 'M0'
                     and 'ApproachingCrossingHappen' in x['columns']]
        passed = (completed.returncode == 1 and base['status'] == 'MISMATCH'
                  and len(detection) == 1 and len(diffs) == 1 and not issues and not bad_tables)
    else:
        detection = [x for x in issues if x['kind'] == 'active_source_invariant_false'
                     and x['phase'] == 'post' and x['state'] == 'N2'
                     and x['requirement'] == 'P_BRAKE_IF_SOMETHING_BAD'
                     and x['prefix'][-1] == 'brake']
        passed = completed.returncode == 1 and base['status'] == 'MISMATCH' and bool(detection)
    return {'control': control, 'control_passed': bool(passed), 'command_template': ['python3', '-B', checker.name, '--artifact-root', control, '--output', output.name],
            'checker_exit_code': completed.returncode, 'checker_status': {v: r['status'] for v, r in reports.items()},
            'issue_counts': dict(__import__('collections').Counter(x['kind'] for x in issues)),
            'observer_difference_count': len(diffs), 'bad_table_match_count': len(bad_tables),
            'expected_detection': detection[:3], 'analysis_file': output.name,
            'stdout': completed.stdout, 'stderr': completed.stderr}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--checker', type=Path, default=Path(__file__).parent / 'analyze_saved_railcab.py')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, default=Path(__file__).parent / 'negative_control_runs')
    args = parser.parse_args()
    need(not args.output.exists(), 'Use a fresh result path')
    original = {relative: (args.artifact_root / relative).read_bytes() for relative in FILES}
    checker_before = args.checker.read_bytes()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run_', dir=args.work_dir)).resolve()
    results = []
    for control in ['positive_unchanged', 'wrong_installed_monitor',
                    'wrong_nonentry_observer', 'unsafe_post_observation']:
        stage = run / control
        for relative in FILES:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.artifact_root / relative, target)
        bundle_path = stage / BASE
        bundle = json.loads(bundle_path.read_text())
        mutation = mutate(bundle, control)
        if control != 'positive_unchanged':
            bundle_path.write_text(json.dumps(bundle, indent=2) + '\n')
        result = execute(args.checker.resolve(), stage, control)
        result['mutation'] = mutation
        results.append(result)
    originals_unchanged = all((args.artifact_root / r).read_bytes() == data for r, data in original.items())
    checker_unchanged = args.checker.read_bytes() == checker_before
    payload = {'scope': 'Checker controls on copied saved data; no synthesis, application execution, or performance experiment',
               'path_reporting': 'Only portable input and temporary directory names are recorded; command_template names the checker and per-control copy.',
               'input_root_argument': 'inputs', 'temporary_run_name': run.name,
               'copied_input_files': FILES, 'originals_unchanged': originals_unchanged,
               'main_checker_unchanged': checker_unchanged, 'controls': results,
               'status': 'PASS' if originals_unchanged and checker_unchanged and all(r['control_passed'] for r in results) else 'FAIL'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + '\n')
    for r in results:
        print(json.dumps({k: r[k] for k in ['control', 'control_passed', 'checker_exit_code', 'checker_status',
                                           'issue_counts', 'observer_difference_count', 'bad_table_match_count']}))
    print('overall', payload['status'], 'originals_unchanged', originals_unchanged, 'main_checker_unchanged', checker_unchanged)
    raise SystemExit(0 if payload['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()

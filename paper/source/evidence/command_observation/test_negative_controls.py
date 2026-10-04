#!/usr/bin/env python3
"""Semantic-layer fault injections for the command/reset analysis.

Only temporary copies are changed. These exercise intersection, Boolean-reset,
and lookup-language checks after loading saved data, not metadata-integrity
gates and not a compiler or controller execution.
"""
from pathlib import Path
from copy import deepcopy
import argparse
import importlib.util
import json
import re
import sys
import tempfile

sys.dont_write_bytecode = True


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--analysis-script', type=Path, default=Path(__file__).parent / 'analyze_command_observation.py')
    parser.add_argument('--work-dir', type=Path, default=Path(__file__).parent / 'negative_control_runs')
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    A = module('command_analysis', args.analysis_script)
    H = module('source_parser', root / A.PARSER)
    C = module('coverage_checker', root / 'results/initialization/check_coverage.py')
    A.need(not args.output.exists(), 'Choose a new result path')
    args.work_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='controls_', dir=args.work_dir)).resolve()
    constants_text = (root / A.CONSTANTS).read_text()
    constants = {name: A.one(r'\b' + name + r'\s*=\s*"([^"]+)"\s*;', constants_text, name)
                 for name in ['STOP_OLD_SPEC_PREFIX', 'START_NEW_SPEC_PREFIX', 'BEGIN_UPDATE', 'FINISH_UPDATE']}
    snapshots = {}

    def read(path):
        path = root / path
        snapshots.setdefault(path, path.read_bytes())
        return path.read_text()

    def fixture(model):
        export = json.loads(read('results/initialization/raw/expanded-predicates/' + model + '.json'))
        source_text = read('tool/models/' + export['source_name'])
        source = H.Source(root / 'tool/models' / export['source_name'])
        inventory = A.command_inventory(source, export, constants, H)
        lookup = json.loads(read('results/supplement-checks/frontend_lookup_demo/runs/' + model + '__base/lookup.json'))
        return export, source_text, source, inventory, lookup

    rail_export, rail_text, rail_source, rail_inventory, rail_lookup = fixture('railcab')
    gsm_export, gsm_text, gsm_source, gsm_inventory, gsm_lookup = fixture('gsm')
    controls = []

    # 1: A declared source fluent starts observing an actual transfer command.
    command = 'reconfigure_MILESTONES'
    A.need(command in rail_inventory['progress_commands'], 'Control command is not in the verified inventory')
    changed, count = re.subn(r'(?m)^fluent\s+ApproachingCrossingHappen\s*=\s*[^\n]+$',
                            'fluent ApproachingCrossingHappen = <{approachingCrossing,reconfigure_MILESTONES},{endOfTS}>', rail_text)
    A.need(count == 1, 'Expected one fluent declaration to mutate')
    changed_path = work / 'declared_fluent_observes_command.lts'
    changed_path.write_text(changed)
    mutated_source = H.Source(changed_path)
    fluent = mutated_source.fluent('ApproachingCrossingHappen')
    hits = A.observer_intersections({'ApproachingCrossingHappen': fluent},
                                   set(rail_inventory['progress_commands']), set(rail_inventory['boundary_events']))
    passed = hits[0]['kind'] == 'declared_fluent' and hits[0]['progress_initiating'] == [command]
    controls.append({'control': 'declared_fluent_command_intersection', 'passed': passed,
                     'mutation': 'Add verified command reconfigure_MILESTONES to the initiating set of ApproachingCrossingHappen',
                     'mutated_input': changed_path.name, 'expected_detection': hits})

    # 2: A saved NEW monitor observes that model's transfer and enters ERROR.
    gsm_row = deepcopy(next(r for r in gsm_export['requirements'] if r['target'] == 'base' and r['kind'] == 'new'))
    command = 'reconfigure_ENV'
    A.need(command in gsm_inventory['progress_commands'] and command not in gsm_row['alphabet'],
           'Control transfer must be a real command previously absent from the monitor')
    gsm_row['alphabet'].append(command)
    gsm_row['transitions'].append([0, command, -1])
    changed_path = work / 'monitor_command_to_error.json'
    changed_path.write_text(json.dumps(gsm_row, indent=2) + '\n')
    command_checks, nonloops = A.command_effects(gsm_row, set(gsm_inventory['progress_commands']),
                                               set(gsm_inventory['boundary_events']), H)
    affected = next(r for r in command_checks if r['command'] == command)
    passed = affected['in_saved_monitor_alphabet'] and not affected['all_nonerror_states_self_loop']
    controls.append({'control': 'monitor_command_not_stuttering', 'passed': passed,
                     'mutation': 'Add the real command reconfigure_ENV to the saved GSM monitor with transition 0 -> ERROR',
                     'mutated_input': changed_path.name, 'expected_detection': {'command': affected, 'nonloops': nonloops}})

    # 3: Positive event truth is deliberately required, so resetting it is unsafe.
    changed, count = re.subn(r'(?m)^ltl_property\s+P_NEW_DECODE\s*=\s*[^\n]+$',
                            'ltl_property P_NEW_DECODE = []decode[2]', gsm_text)
    A.need(count == 1, 'Expected one NEW invariant to mutate')
    changed_path = work / 'positive_event_requirement.lts'
    changed_path.write_text(changed)
    mutated_source = H.Source(changed_path)
    body, line = mutated_source.definition('ltl_property', 'P_NEW_DECODE')
    ast = H.Formula(mutated_source, body[2:].strip()).ast
    fluents = {H.canonical(atom): mutated_source.fluent(atom) for atom in H.atoms(ast)}
    reset = A.reset_table(ast, fluents, H)
    passed = reset['status'] == 'COUNTEREXAMPLE' and len(reset['counterexamples']) == 1
    controls.append({'control': 'source_reset_not_truth_preserving', 'passed': passed,
                     'mutation': 'Replace the GSM NEW invariant by the positive actual event predicate decode[2]',
                     'mutated_input': changed_path.name, 'expected_detection': reset})

    # 4: A reset key exists and stays non-error, but selects a different language.
    name = 'P_CHECK_STATUS_AFTER_APPROACHING_CROSSING'
    actual = deepcopy(next(r for r in rail_lookup['requirements'] if r['requirement'] == name))
    cell = next(c for c in actual['actual_lookup_entries'] if c['observer_state_indices'] == [1, 0, 0])
    A.need(cell['monitor_state'] == 1, 'Unexpected Railcab safe reset cell')
    cell['monitor_state'] = 0
    changed_path = work / 'reset_lookup_language_mismatch.json'
    changed_path.write_text(json.dumps(actual, indent=2) + '\n')
    row = next(r for r in rail_export['requirements']
               if r['target'] == 'base' and r['kind'] == 'new' and r['requirement'] == name)
    body, line = rail_source.definition('ltl_property', name)
    ast = H.Formula(rail_source, body[2:].strip()).ast
    fluents = {H.canonical(atom): rail_source.fluent(atom) for atom in H.atoms(ast)}
    result = A.analyze_lookup_reset(row, actual, fluents, H, C.language_equivalence)
    detection = [c for c in result['nonerror_preservation_counterexamples']
                 if c['key'] == [1, 0, 1] and c['reset_key'] == [1, 0, 0]
                 and c['outcome'] == 'NONERROR_LANGUAGE_MISMATCH'
                 and c['distinguishing_suffix'] == ['checkCrossingStatus']]
    controls.append({'control': 'reset_lookup_residual_language_mismatch', 'passed': len(detection) == 1,
                     'mutation': 'Change the selected state at Railcab key (1,0,0) from 1 to 0; the (1,0,1) cell still selects 1',
                     'mutated_input': changed_path.name, 'expected_detection': detection})

    unchanged = all(path.read_bytes() == before for path, before in snapshots.items())
    payload = {'scope': 'Four semantic-layer negative controls on copied inputs; no metadata tampering, synthesis, controller execution or performance trial',
               'status': 'PASS' if unchanged and all(c['passed'] for c in controls) else 'FAIL',
               'originals_unchanged': unchanged,
               'original_inputs_checked': [str(path.relative_to(root)) for path in snapshots],
               'temporary_inputs': work.name, 'controls': controls}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + '\n')
    for control in controls:
        print(json.dumps({'control': control['control'], 'expected_defect_detected': control['passed']}))
    print('overall', payload['status'], 'originals_unchanged', unchanged)
    raise SystemExit(0 if payload['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()

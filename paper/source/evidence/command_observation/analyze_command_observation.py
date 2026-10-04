#!/usr/bin/env python3
"""Static source/command/monitor analysis of the nine archived FG inputs.

Reads the public artifact without modifying it. No Java, synthesis, execution
of controllers, timing experiment, or model generation is performed. Every
Boolean valuation and any counterexample is retained in the output.
"""
from pathlib import Path
from collections import Counter, deque
from itertools import product
import argparse
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode = True
PARSER = 'results/supplement-checks/source_invariant_lookup/analyze_new_invariants.py'
CONSTANTS = 'tool/source/mtsa/src/main/java/ltsa/updatingControllers/UpdateConstants.java'
PROTOCOL = 'tool/source/mtsa/src/main/java/ltsa/updatingControllers/structures/UpdateProtocolSpec.java'
TARGETS = ('base', 'r1', 'r2')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def one(pattern, text, message):
    matches = re.findall(pattern, text)
    need(len(matches) == 1, message + ': expected one match, got ' + str(len(matches)))
    return matches[0]


def safety_names(source, goal):
    body, line = source.definition('controllerSpec', goal)
    names = one(r'\bsafety\s*=\s*\{([^}]+)\}', body, 'Safety list ' + goal)
    names = [x.strip() for x in names.split(',')]
    need(all(re.fullmatch(r'[A-Za-z_]\w*', x) for x in names), 'Unsupported safety-list syntax')
    need(len(names) == len(set(names)), 'Duplicate safety name')
    return set(names), line


def command_inventory(source, exports, constants, H):
    declared = {}
    for name in ('StopOldSpecActions', 'StartNewSpecActions', 'ReconfigureActions'):
        body, line = source.definition('set', name)
        declared[name] = {'line': line, 'definition': body, 'actions': sorted(source.actions(name))}
    groups = {k: set(v['actions']) for k, v in declared.items()}
    need(not (groups['StopOldSpecActions'] & groups['StartNewSpecActions']
              or groups['StopOldSpecActions'] & groups['ReconfigureActions']
              or groups['StartNewSpecActions'] & groups['ReconfigureActions']), 'Command groups overlap')
    contracts = []
    all_old = all_new = all_maps = None
    need({c['target'] for c in exports['contracts']} == set(TARGETS), 'Unexpected contract population')
    for contract in exports['contracts']:
        definition = contract['definition']
        body, line = source.definition('updatingController', definition)
        need(re.search(r'\bfine_grained\b', body) and not re.search(r'\bselective_fine_grained\b', body),
             'Expected non-selective fine-grained controller')
        old_goal = one(r'\boldGoal\s*=\s*([A-Za-z_]\w*)\s*,', body, 'Old goal ' + definition)
        new_goal = one(r'\bnewGoal\s*=\s*([A-Za-z_]\w*)\s*,', body, 'New goal ' + definition)
        old_names, old_line = safety_names(source, old_goal)
        new_names, new_line = safety_names(source, new_goal)
        map_body = one(r'\bmapRelation\s*=\s*\{([^}]+)\}', body, 'Mapping list ' + definition)
        maps = {x.strip() for x in map_body.split(',')}
        need(maps == set(contract['map_relations']), 'Source/export mapping names differ')
        need(len(maps) == contract['components'], 'Source/export component count differs')
        need(new_names == {r['requirement'] for r in exports['requirements']
                           if r['target'] == contract['target'] and r['kind'] == 'new'},
             'New goal/export requirements differ')
        generated_stops = {constants['STOP_OLD_SPEC_PREFIX'] + n for n in old_names}
        generated_starts = {constants['START_NEW_SPEC_PREFIX'] + n for n in new_names}
        need(generated_stops == groups['StopOldSpecActions'], 'Declared stop set differs from goal-derived commands')
        need(generated_starts == groups['StartNewSpecActions'], 'Declared start set differs from goal-derived commands')
        relation_records = []
        transfer_commands = set()
        for relation in sorted(maps):
            relation_body, relation_line = source.definition('relation', relation)
            need(relation_body.startswith('{') and relation_body.endswith('}'), 'Unsupported relation syntax')
            actions = set()
            entries = H.split_top(relation_body[1:-1], ',')
            for entry in entries:
                need(entry.count('=') == 1 and entry.count('->') == 1,
                     'Expected one literal transfer action per mapping entry: ' + relation)
                action = one(r'=\s*([a-z]\w*)\s*->', entry, 'Transfer action in ' + relation)
                actions.add(action)
            need(len(actions) == 1, 'Multiple transfer names in one mapping: ' + relation)
            transfer_commands.update(actions)
            relation_records.append({'relation': relation, 'line': relation_line,
                                     'source_entries': len(entries), 'actions': sorted(actions)})
        need(transfer_commands == groups['ReconfigureActions'], 'Declared transfer set differs from used relations')
        if all_old is None:
            all_old, all_new, all_maps = old_names, new_names, maps
        else:
            need((old_names, new_names, maps) == (all_old, all_new, all_maps), 'Variant changes command population')
        contracts.append({'target': contract['target'], 'definition': definition, 'source_line': line,
                          'old_goal': old_goal, 'old_goal_line': old_line, 'old_safety_names': sorted(old_names),
                          'new_goal': new_goal, 'new_goal_line': new_line, 'new_safety_names': sorted(new_names),
                          'relations': relation_records, 'all_three_declared_sets_match': True})
    progress = set().union(*groups.values())
    boundaries = {constants['BEGIN_UPDATE'], constants['FINISH_UPDATE']}
    return {'declared_sets': declared, 'contracts': contracts,
            'progress_commands': sorted(progress), 'boundary_events': sorted(boundaries),
            'progress_command_count': len(progress),
            'basis': 'Explicit source sets, actual exported controller definitions and map names, selected goal safety lists, and literal actions in every selected relation; prefixes are read only to reproduce the documented forFineGrained construction, not to infer absence'}


def reset_table(ast, source_fluents, H):
    order = sorted(source_fluents)
    events = {n for n, f in source_fluents.items() if f['kind'] == 'event_predicate'}
    rows, counterexamples = [], []
    for values in product((False, True), repeat=len(order)):
        valuation = dict(zip(order, values))
        reset = {n: False if n in events else v for n, v in valuation.items()}
        before, after = H.evaluate(ast, valuation), H.evaluate(ast, reset)
        row = {'bits': list(map(int, values)), 'phi': before,
               'reset_bits': [int(reset[n]) for n in order], 'phi_after_reset': after,
               'implication_holds': not before or after}
        rows.append(row)
        if before and not after:
            counterexamples.append({'valuation': valuation, 'reset_valuation': reset})
    return {'atom_order': order, 'atom_count': len(order), 'event_predicates': sorted(events),
            'declared_fluents': sorted(set(order) - events), 'assignment_count': len(rows),
            'reset_is_identity': not events, 'all_assignments': rows,
            'safe_assignment_count': sum(r['phi'] for r in rows),
            'counterexamples': counterexamples,
            'status': 'HOLDS_ALL_BOOLEAN_VALUATIONS' if not counterexamples else 'COUNTEREXAMPLE'}


def observer_intersections(fluents, progress, boundaries):
    records = []
    for atom, fluent in sorted(fluents.items()):
        initiating, terminating = set(fluent['initiating']), set(fluent['terminating'])
        records.append({'atom': atom, 'kind': fluent['kind'], 'source_line': fluent.get('source_line'),
                        'initiating': sorted(initiating), 'terminating': sorted(terminating),
                        'progress_initiating': sorted(initiating & progress),
                        'progress_terminating': sorted(terminating & progress),
                        'boundary_initiating': sorted(initiating & boundaries),
                        'boundary_terminating': sorted(terminating & boundaries),
                        'terminating_wildcard': '*' in terminating})
    return records


def command_effects(row, progress, boundaries, H):
    step = H.monitor(row)
    alpha = set(row['alphabet'])
    checks, nonloops = [], []
    for command in sorted(progress | boundaries):
        effects = [{'source': state, 'target': step(state, command)}
                   for state in range(row['monitor_nonerror_states'])]
        failures = [effect for effect in effects if effect['source'] != effect['target']]
        checks.append({'command': command, 'category': 'progress' if command in progress else 'boundary',
                       'in_saved_monitor_alphabet': command in alpha,
                       'decoding': 'explicit alphabet transition' if command in alpha else 'outside alphabet stutter',
                       'state_effects': effects, 'all_nonerror_states_self_loop': not failures})
        nonloops.extend({'command': command, **effect} for effect in failures)
    return checks, nonloops


def decode_observer(column, H):
    """Derive the Boolean meaning from initial truth and every saved transition."""
    alphabet = sorted(set(column['alphabet']) - {'tau'})
    named_semantic_events = (set(column['initiating']) | set(column['terminating'])) - {'*'}
    need(named_semantic_events <= set(alphabet), 'Observer omits a named semantic event')
    edges = {}
    for source, event, target in column['transitions']:
        need(event != 'tau' and event in alphabet, 'Unexpected observer transition label')
        need((source, event) not in edges or edges[source, event] == target, 'Nondeterministic observer')
        edges[source, event] = target
    initial = column['initial_state']
    truth = {initial: bool(column['initial_value'])}
    prefixes = {initial: []}
    queue = deque([initial])
    checked = 0
    while queue:
        state = queue.popleft()
        for event in alphabet:
            need((state, event) in edges, 'Missing transition in observer alphabet')
            target = edges[state, event]
            need(target in range(column['nonerror_states']), 'Observer transition reaches an invalid state')
            value = H.advance((truth[state],), [column], event)[0]
            checked += 1
            need(target not in truth or truth[target] == value,
                 'Observer state has inconsistent Boolean meanings: ' + column['name'])
            if target not in truth:
                truth[target] = value
                prefixes[target] = prefixes[state] + [event]
                queue.append(target)
    need(set(truth) == set(range(column['nonerror_states'])), 'Unresolved observer state meaning')
    false_states = [state for state, value in truth.items() if not value]
    true_states = [state for state, value in truth.items() if value]
    need(len(false_states) == len(true_states) == 1, 'Not a unique two-state Boolean encoding')
    return {'column_name': column['name'], 'initial_state': initial,
            'initial_truth': bool(column['initial_value']), 'false_state': false_states[0],
            'true_state': true_states[0], 'state_meanings': [
                {'state': state, 'truth': truth[state], 'witness_from_initial': prefixes[state]}
                for state in sorted(truth)], 'saved_transition_cells_checked': checked,
            'decoding_scope': 'All saved observer states and labels; meanings derived from initial truth and transition semantics, not state-number or name conventions'}


def analyze_lookup_reset(row, actual, source_fluents, H, equivalence):
    columns = actual['observers_in_actual_column_order']
    decoded = []
    for index, column in enumerate(columns):
        matches = [f for f in source_fluents.values()
                   if H.semantic_signature(f) == H.semantic_signature(column)]
        need(matches and len({f['kind'] for f in matches}) == 1, 'Ambiguous source kind for observer column')
        record = decode_observer(column, H)
        record.update(column_index=index, source_kind=matches[0]['kind'],
                      matching_source_atoms=sorted(f['name'] for f in matches))
        decoded.append(record)
    cells = {tuple(cell['observer_state_indices']): cell['monitor_state']
             for cell in actual['actual_lookup_entries']}
    need(len(cells) == len(actual['actual_lookup_entries']), 'Duplicate saved lookup key')
    event_indices = {d['column_index'] for d in decoded if d['source_kind'] == 'event_predicate'}
    alphabet = (set(row['alphabet']) - {'tau'})
    for column in columns:
        alphabet.update(set(column['alphabet']) - {'tau'})
    other = '__FGDUCS_COMMAND_ANALYSIS_OTHER__'
    need(other not in alphabet, 'OTHER label collides with saved alphabet')
    alphabet = sorted(alphabet) + [other]
    records, cache = [], {}
    for key, state in sorted(cells.items()):
        need(len(key) == len(decoded), 'Lookup arity differs from observer columns')
        reset_key = tuple(d['false_state'] if i in event_indices else key[i]
                          for i, d in enumerate(decoded))
        values = []
        for raw, d in zip(key, decoded):
            need(raw in (d['false_state'], d['true_state']), 'Lookup contains undecoded observer state')
            values.append(raw == d['true_state'])
        present = reset_key in cells
        reset_state = cells.get(reset_key)
        same, witness = None, None
        if present:
            pair = state, reset_state
            if pair not in cache:
                cache[pair] = equivalence(row, state, reset_state, alphabet)
            same, witness = cache[pair]
        original_error = state == row['error_state']
        if not present:
            outcome = 'MISSING'
        elif reset_state == row['error_state']:
            outcome = 'ERROR_REMAINS' if original_error else 'NONERROR_TO_ERROR'
        elif original_error:
            outcome = 'ERROR_TO_NONERROR'
        elif same:
            outcome = 'NONERROR_EQUIVALENT'
        else:
            outcome = 'NONERROR_LANGUAGE_MISMATCH'
        records.append({'key': list(key), 'decoded_truth': values, 'selected_state': state,
                        'original_class': 'ERROR' if original_error else 'NONERROR',
                        'reset_key': list(reset_key), 'key_changed': key != reset_key,
                        'reset_key_present': present, 'reset_selected_state': reset_state,
                        'same_state_id': present and state == reset_state,
                        'error_continuation_language_equivalent': same,
                        'distinguishing_suffix': witness, 'outcome': outcome})
    counts = Counter(record['outcome'] for record in records)
    return {'scope': 'A transformation of every saved table cell; not observed activation frequencies or plant reachability',
            'column_decoders': decoded, 'event_column_indices': sorted(event_indices),
            'comparison_alphabet': alphabet,
            'outside_alphabet_basis': 'The fresh OTHER represents all labels absent from the saved monitor alphabet, which stutter in both compared states',
            'language_equivalence_reuse': 'results/initialization/check_coverage.py:language_equivalence and its existing deterministic monitor decoder; not an independent second language checker',
            'cells': records, 'outcome_counts': dict(counts),
            'nonerror_cells': sum(r['original_class'] == 'NONERROR' for r in records),
            'error_cells': sum(r['original_class'] == 'ERROR' for r in records),
            'nonerror_preservation_counterexamples': [r for r in records if r['original_class'] == 'NONERROR'
                                                    and r['outcome'] != 'NONERROR_EQUIVALENT'],
            'unique_monitor_state_pairs_compared': len(cache)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    need(not args.output.exists(), 'Choose a new output path')
    spec = importlib.util.spec_from_file_location('archived_source_parser', root / PARSER)
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    coverage_spec = importlib.util.spec_from_file_location('archived_coverage', root / 'results/initialization/check_coverage.py')
    coverage = importlib.util.module_from_spec(coverage_spec)
    coverage_spec.loader.exec_module(coverage)
    constants_text = (root / CONSTANTS).read_text()
    constants = {name: one(r'\b' + name + r'\s*=\s*"([^"]+)"\s*;', constants_text, name)
                 for name in ['STOP_OLD_SPEC_PREFIX', 'START_NEW_SPEC_PREFIX', 'BEGIN_UPDATE', 'FINISH_UPDATE']}
    model_reports, positions, occurrences = [], [], []
    for model, expected in H.EXPECTED.items():
        export_path = root / 'results/initialization/raw/expanded-predicates' / (model + '.json')
        exports = json.loads(export_path.read_text())
        source_path = root / 'tool/models' / exports['source_name']
        source = H.Source(source_path)
        source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        inventory = command_inventory(source, exports, constants, H)
        progress, boundaries = set(inventory['progress_commands']), set(inventory['boundary_events'])
        rows = [r for r in exports['requirements'] if r['kind'] == 'new']
        need(Counter(r['target'] for r in rows) == Counter(dict.fromkeys(TARGETS, expected)), 'Wrong NEW occurrence population')
        actual, meta_records = {}, []
        for target in TARGETS:
            folder = root / 'results/supplement-checks/frontend_lookup_demo/runs' / (model + '__' + target)
            lookup, meta = (json.loads((folder / name).read_text()) for name in ['lookup.json', 'meta.json'])
            contract = next(c for c in exports['contracts'] if c['target'] == target)
            need(lookup['definition'] == contract['definition'], 'Lookup/contract definition differs')
            need(lookup['source_name'] == exports['source_name'], 'Lookup/export source name differs')
            need(meta['input_sha256'] == source_digest, 'Source input bytes differ from lookup metadata')
            need(meta['status'] == 'EXPORTED', 'Incomplete saved lookup export')
            actual[target] = {x['requirement']: x for x in lookup['requirements']}
            need(len(actual[target]) == expected, 'Wrong actual lookup requirement population')
            meta_records.append({'target': target, 'input_matches_saved_metadata': True,
                                 'jar_sha256': meta['jar_sha256'], 'lookup_definition': lookup['definition']})
        log = export_path.with_suffix('.log').read_text()
        need(one(r'(?m)^INPUT_SHA256=([0-9a-f]+)$', log, 'Expanded export input') == source_digest,
             'Source input differs from expanded-export log')
        jar = one(r'(?m)^JAR_SHA256=([0-9a-f]+)$', log, 'Expanded export JAR')
        need(all(m['jar_sha256'] == jar for m in meta_records), 'Expanded/actual exports use different JARs')
        model_reports.append({'model': model, 'source_path': source_path.relative_to(root).as_posix(),
                              'new_positions': expected, 'commands': inventory,
                              'input_matches_all_saved_exports': True, 'metadata': meta_records})
        grouped = {}
        for row in rows:
            target, name = row['target'], row['requirement']
            saved = actual[target][name]
            monitor = saved['monitor']
            need(set(monitor['alphabet']) == set(row['alphabet']) and
                 set(map(tuple, monitor['transitions'])) == set(map(tuple, row['transitions'])) and
                 (monitor['nonerror_states'], monitor['initial_state'], monitor['error_state']) ==
                 (row['monitor_nonerror_states'], row['monitor_initial'], row['error_state']),
                 'Actual/expanded monitor disagrees')
            alpha = set(monitor['alphabet'])
            command_checks, nonloops = command_effects(row, progress, boundaries, H)
            item = {'model': model, 'target': target, 'requirement': name,
                    'monitor_nonerror_states': monitor['nonerror_states'],
                    'saved_monitor_alphabet': sorted(alpha),
                    'progress_alphabet_intersection': sorted(alpha & progress),
                    'boundary_alphabet_intersection': sorted(alpha & boundaries),
                    'command_checks': command_checks, 'non_self_loops': nonloops,
                    'actual_and_expanded_monitor_identical': True}
            occurrences.append(item)
            grouped.setdefault(name, []).append((row, saved))
        for name, variants in grouped.items():
            body, line = source.definition('ltl_property', name)
            need(body.startswith('[]'), 'Expected a pure invariant')
            ast = H.Formula(source, body[2:].strip()).ast
            fluents = {H.canonical(atom): source.fluent(atom) for atom in H.atoms(ast)}
            need(len(fluents) <= 16, 'Unexpectedly large Boolean space: report rather than sample')
            for row, saved in variants:
                references = row['referenced_fluents']
                need(set(fluents) == {H.canonical(f['name']) for f in references}, 'Source/export atom set differs')
                for f in references:
                    parsed = fluents[H.canonical(f['name'])]
                    need(H.semantic_signature(parsed) == H.semantic_signature(f) and parsed['kind'] == f['kind'],
                         'Source/export fluent semantics differ')
                need(Counter(H.semantic_signature(f) for f in fluents.values()) ==
                     Counter(H.semantic_signature(f) for f in saved['observers_in_actual_column_order']),
                     'Source/actual observer semantics differ')
            structures = [json.dumps(saved['monitor'], sort_keys=True) for row, saved in variants]
            need(len(variants) == 3, 'Missing variant of source position')
            observation_rows = observer_intersections(fluents, progress, boundaries)
            declared_hits = [f for f in observation_rows if f['kind'] == 'declared_fluent' and
                             (f['progress_initiating'] or f['progress_terminating'] or f['terminating_wildcard'])]
            event_hits = [f for f in observation_rows if f['kind'] == 'event_predicate' and f['progress_initiating']]
            for row, saved in variants:
                item = next(o for o in occurrences if (o['model'], o['target'], o['requirement']) ==
                            (model, row['target'], name))
                item['lookup_reset'] = analyze_lookup_reset(row, saved, fluents, H, coverage.language_equivalence)
            positions.append({'model': model, 'requirement': name,
                              'source_path': source_path.relative_to(root).as_posix(), 'source_line': line,
                              'source_formula': body, 'expanded_formula_ast': ast,
                              'variants': sorted(row['target'] for row, saved in variants),
                              'saved_monitor_identical_across_variants': len(set(structures)) == 1,
                              'observer_command_intersections': observation_rows,
                              'declared_fluent_observes_progress': bool(declared_hits),
                              'declared_fluent_progress_witnesses': declared_hits,
                              'event_predicate_names_a_progress_command': bool(event_hits),
                              'event_predicate_progress_witnesses': event_hits,
                              'simultaneous_event_reset': reset_table(ast, fluents, H)})
    need(len(positions) == 46 and len(occurrences) == 138 and len(model_reports) == 9, 'Incomplete analysis population')
    totals = {'models': len(model_reports), 'source_positions': len(positions), 'variant_occurrences': len(occurrences),
              'progress_commands_summed_per_model': sum(m['commands']['progress_command_count'] for m in model_reports),
              'max_atoms_per_position': max(p['simultaneous_event_reset']['atom_count'] for p in positions),
              'boolean_assignments': sum(p['simultaneous_event_reset']['assignment_count'] for p in positions),
              'positions_with_event_predicates': sum(not p['simultaneous_event_reset']['reset_is_identity'] for p in positions),
              'positions_without_event_predicates': sum(p['simultaneous_event_reset']['reset_is_identity'] for p in positions),
              'declared_fluent_progress_intersection_positions': sum(p['declared_fluent_observes_progress'] for p in positions),
              'event_predicate_progress_intersection_positions': sum(p['event_predicate_names_a_progress_command'] for p in positions),
              'monitor_progress_alphabet_intersection_occurrences': sum(bool(o['progress_alphabet_intersection']) for o in occurrences),
              'monitor_boundary_alphabet_intersection_occurrences': sum(bool(o['boundary_alphabet_intersection']) for o in occurrences),
              'non_self_loop_command_state_pairs': sum(len(o['non_self_loops']) for o in occurrences),
              'reset_counterexample_positions': sum(bool(p['simultaneous_event_reset']['counterexamples']) for p in positions),
              'reset_counterexample_assignments': sum(len(p['simultaneous_event_reset']['counterexamples']) for p in positions),
              'identical_three_variant_monitor_groups': sum(p['saved_monitor_identical_across_variants'] for p in positions)}
    reset_cells = [cell for occurrence in occurrences for cell in occurrence['lookup_reset']['cells']]
    need(len(reset_cells) == 1587 and sum(c['original_class'] == 'NONERROR' for c in reset_cells) == 900
         and sum(c['original_class'] == 'ERROR' for c in reset_cells) == 687, 'Unexpected saved lookup cell population')
    totals.update(lookup_cells=len(reset_cells), nonerror_lookup_cells=900, error_lookup_cells=687,
                  lookup_reset_outcomes=dict(Counter(c['outcome'] for c in reset_cells)),
                  nonerror_reset_changed_keys=sum(c['key_changed'] for c in reset_cells if c['original_class'] == 'NONERROR'),
                  nonerror_reset_changed_state_ids=sum(not c['same_state_id'] for c in reset_cells if c['original_class'] == 'NONERROR'),
                  nonerror_reset_counterexamples=sum(c['outcome'] != 'NONERROR_EQUIVALENT' for c in reset_cells if c['original_class'] == 'NONERROR'),
                  observer_column_occurrences=sum(len(o['lookup_reset']['column_decoders']) for o in occurrences),
                  observer_transition_cells_decoded=sum(d['saved_transition_cells_checked'] for o in occurrences
                                                        for d in o['lookup_reset']['column_decoders']))
    payload = {'analysis_kind': 'Static finite analysis of saved FSP source and saved monitor exports',
               'status': 'COMPLETE', 'totals': totals,
               'command_scope': 'Actual fine-grained progress commands (stop/start/transfer) of the saved Base/R1/R2 contracts; entry/finish boundaries reported separately; legacy and selective modes are not included',
               'source_parser': PARSER, 'parser_reuse': 'Reuses the archived restricted parser and Boolean evaluator; not an independent second parser',
               'command_construction_basis': [CONSTANTS + ':8-20', PROTOCOL + ':76-97', PROTOCOL + ':140-176',
                                              'tool/source/mtsa/src/main/java/ltsa/lts/UpdatingControllersDefinition.java:184-195,248-300'],
               'monitor_decoding': 'Outside the saved alphabet stutters; missing transitions inside the alphabet go to ERROR; ERROR absorbs. Effects enumerate every nonerror state; tau is not a command.',
               'boolean_scope': 'Every Boolean valuation of the source atoms, including physically unreachable or mutually inconsistent valuations; all implicit event predicates are reset simultaneously to false, and all declared fluents are preserved',
               'table_projection_scope': 'All 900 non-error and all 687 error table cells, including unchanged keys; these are repeated variant occurrences, not actual activation frequencies',
               'language_checker_reuse': 'Reuses results/initialization/check_coverage.py:language_equivalence; preserves distinguishing words for inequivalent states',
               'not_established': ['general command/residual-language equivalence theorem', 'physical decoding or key correctness for all applications',
                                   'history feasibility or actual activation/fallback behavior', 'arbitrary FSP/compiler correctness',
                                   'runtime conformance', 'proof that all inspected commands can occur at every state'],
               'models': model_reports, 'source_positions': positions, 'monitor_occurrences': occurrences}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(totals, indent=2))
    print('All positions and all Boolean assignments, including every counterexample, are retained.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Independent static verification of saved Threads merged-policy serialization.

Python standard library only. No solver, Java, performance measurement, existing
checker import, fixed point, or winning-policy search is used. The transformer
retains every saved ordinary strategy edge and replaces its single simultaneous
identity-transfer edge by rho_1,...,rho_n. The verifier reconstructs complete
plant Post from copied local LTSs and validates the resulting supplied policy.
"""
import argparse
import copy
import csv
import itertools
import json
from collections import defaultdict, deque
from pathlib import Path

MERGED = 'ablation.merge.transfers'


class Invalid(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def physical(q):
    return tuple(tuple(x) for x in q['physical'])


def key(q):
    return physical(q), tuple(sorted(q['pending']))


def lts_index(lts):
    states = set(lts['states'])
    require(len(states) == len(lts['states']), 'duplicate LTS states')
    require(lts['initial'] in states, 'invalid LTS initial')
    edges = {tuple(e) for e in lts['edges']}
    require(len(edges) == len(lts['edges']), 'duplicate LTS edges')
    out = defaultdict(set)
    for s, a, t in edges:
        require(s in states and t in states, 'edge outside LTS state set')
        out[s, a].add(t)
    return out, {a for _, a, _ in edges}


class Plant:
    def __init__(self, data):
        self.data = data
        self.components = data['components']
        self.ordinary = set(data['ordinary'])
        self.controllable = set(data['controllable'])
        self.uc = self.ordinary - self.controllable
        self.local = [{v.upper(): lts_index(c[v]) for v in ('old', 'new')}
                      for c in self.components]
        self.updates = {c['transfer_action'] for c in self.components}
        self.actions = self.ordinary | self.updates
        require(not (self.ordinary & self.updates), 'ordinary/update action overlap')
        require(self.controllable <= self.ordinary, 'invalid controllable alphabet')
        require(not data['requirements'] and not data['precedence'],
                'scope excludes monitors, initializer boundaries, and precedence')

    def post(self, q, action):
        """Return all semantic outcomes as (physical, pending) keys."""
        phys = physical(q)
        pending = set(q['pending'])
        require(action in self.actions, 'policy action outside input alphabet')
        if action in self.ordinary:
            participates = False
            choices = []
            for (version, state), component in zip(phys, self.local):
                out, alphabet = component[version]
                if action in alphabet:
                    participates = True
                    choices.append([(version, t) for t in out.get((state, action), ())])
                else:
                    choices.append([(version, state)])
            if not participates or not all(choices):
                return set()
            return {(tuple(p), tuple(sorted(pending))) for p in itertools.product(*choices)}
        if action not in pending:
            return set()
        choices = []
        for i, (version, state) in enumerate(phys):
            c = self.components[i]
            if c['transfer_action'] == action:
                if version != 'OLD' or state not in c['transfer']:
                    return set()
                choices.append([('NEW', t) for t in c['transfer'][state]])
            else:
                choices.append([(version, state)])
        return {(tuple(p), tuple(sorted(pending - {action})))
                for p in itertools.product(*choices)}


def validate_inputs(fine, merged):
    n, b = fine['parameters']['n'], fine['parameters']['B']
    require(fine['family'] == 'threads' and fine['parameters']['regime'] == 'backpressure',
            'unexpected family or arrival regime')
    require(2 <= n <= 6 and b in (1, 2), 'outside declared cohort')
    require(len(fine['components']) == n, 'component count differs')
    require(merged.get('generated_contract_mode') == 'transfers', 'missing merged mode')
    for field in ('ordinary', 'controllable', 'requirements', 'precedence', 'endpoints'):
        require(fine[field] == merged[field], 'fine/merged input differs: ' + field)
    require(len(merged['components']) == n, 'merged component count differs')
    pair_count = 0
    for i, (c, d) in enumerate(zip(fine['components'], merged['components']), 1):
        require(c['transfer_action'] == 'rho_' + str(i), 'unexpected singleton update label')
        require(d['transfer_action'] == MERGED, 'unexpected merged update label')
        for field in ('id', 'old', 'new', 'transfer'):
            require(c[field] == d[field], 'fine/merged component differs: ' + field)
        require(c['old'] == c['new'], 'scope requires identical OLD/NEW local LTS')
        old, oa = lts_index(c['old']); new, na = lts_index(c['new'])
        require(oa == na, 'local alphabet changes')
        for s, targets in c['transfer'].items():
            require(targets == [s] and s.startswith('I'), 'scope requires idle identity transfers')
            require(s in c['old']['states'], 'transfer source outside OLD')
            eu = {a for a in oa - set(fine['controllable']) if old.get((s, a))}
            bu = oa - set(fine['controllable']) - eu
            en = {a for a in na - set(fine['controllable']) if new.get((s, a))}
            bn = na - set(fine['controllable']) - en
            require(en <= eu and bu <= bn, 'generalized local UC preservation fails')
            pair_count += 1
    return pair_count


def endpoint_check(data, version):
    """Reconstruct the entire reachable local-plant/controller endpoint product."""
    plant = Plant(data)
    ep = data['endpoints'][version]
    declared, alphabet = lts_index(ep['lts'])
    ctrl, ca = lts_index(ep['controller'])
    tag = version.upper()
    initial_phys = tuple((tag, c[version]['initial']) for c in data['components'])
    initial = initial_phys, ep['controller']['initial']
    seen = {initial}; todo = deque([initial]); product_edges = set()
    while todo:
        p, control = todo.popleft()
        q = {'physical': p, 'pending': []}
        outgoing = 0
        for a in plant.ordinary:
            targets = plant.post(q, a)
            if not targets:
                continue
            cs = ctrl.get((control, a), set()) if a in ca else {control}
            require(cs or a not in plant.uc, 'endpoint controller disables UC')
            for tp, _ in targets:
                for tc in cs:
                    nxt = tp, tc
                    product_edges.add((p, a, tp)); outgoing += 1
                    if nxt not in seen:
                        seen.add(nxt); todo.append(nxt)
        require(outgoing > 0, 'endpoint product deadlock')
    reachable = {ep['lts']['initial']}; todo = deque(reachable)
    while todo:
        s = todo.popleft()
        for a in alphabet:
            for t in declared.get((s, a), ()):
                if t not in reachable:
                    reachable.add(t); todo.append(t)
    require(reachable == set(ep['lts']['states']), 'unreachable declared endpoint state')
    require(set(ep['projection']) == reachable, 'endpoint projection coverage differs')
    projection = {s: physical(ep['projection'][s]) for s in reachable}
    require(all(not ep['projection'][s]['testers'] for s in reachable), 'endpoint monitor outside scope')
    require(len(set(projection.values())) == len(projection), 'noninjective endpoint projection')
    require(projection[ep['lts']['initial']] == initial_phys, 'endpoint initial projection differs')
    require(set(projection.values()) == {p for p, _ in seen}, 'endpoint reachable product differs')
    edges = {(projection[s], a, projection[t]) for s, a, t in ep['lts']['edges']}
    require(edges == product_edges, 'endpoint complete Post relation differs')
    if version == 'new':
        require(set(ep['loadable']) == reachable, 'scope requires all endpoint states loadable')
        require(all(ep['projection'][s].get('goal_id') for s in reachable), 'missing endpoint goal IDs')
    return projection, {'states': len(reachable), 'edges': len(product_edges)}


def verify_policy(data, proof, old_projection, new_projection):
    plant = Plant(data)
    require(proof['decision'] == 'WIN', 'saved policy is not WIN')
    states = {q['id']: q for q in proof['states']}
    require(len(states) == len(proof['states']), 'duplicate policy state IDs')
    semantic = {key(q): q['id'] for q in states.values()}
    require(len(semantic) == len(states), 'duplicate semantic states outside this restricted construction')
    edges = [tuple(e) for e in proof['strategy_edges']]
    require(len(set(edges)) == len(edges), 'duplicate policy edges')
    out = defaultdict(lambda: defaultdict(set))
    for s, a, t in edges:
        require(s in states and t in states, 'policy edge has missing node')
        require(a in plant.actions, 'unknown policy action')
        out[s][a].add(t)
    all_pending = tuple(sorted(plant.updates))
    expected_entries = {(p, all_pending) for p in old_projection.values()}
    entries = {key(q) for q in states.values() if q['initial']}
    require(entries == expected_entries, 'not exactly all OLD endpoint entries')
    goal_targets = {}
    for sid, q in states.items():
        require(len(q['physical']) == len(plant.components), 'physical arity differs')
        require(not q['testers'] and q['safe'] is True, 'monitor/safety outside checked scope')
        require(isinstance(q['rank'], int) and q['rank'] >= 0, 'invalid rank')
        require(len(set(q['pending'])) == len(q['pending']), 'duplicate pending action')
        require(set(q['pending']) <= plant.updates, 'unknown pending action')
        for (v, s), c in zip(physical(q), plant.components):
            require(v in ('OLD', 'NEW') and s in c[v.lower()]['states'], 'invalid physical state')
        # Each transfer action is pending exactly when its complete block remains OLD.
        for a in plant.updates:
            versions = {v for (v, _), c in zip(physical(q), plant.components) if c['transfer_action'] == a}
            require(versions == ({'OLD'} if a in q['pending'] else {'NEW'}), 'pending/version inconsistency')
        matching = [s for s, p in new_projection.items() if p == physical(q)]
        goal = not q['pending'] and len(matching) == 1
        require(q['goal'] == goal, 'goal flag disagrees with fixed endpoint relation')
        if goal:
            require(matching[0] in data['endpoints']['new']['loadable'], 'goal is not loadable')
            require(q['rank'] == 0 and not out[sid], 'goal has nonzero rank or update-policy continuation')
            require(not any(plant.post(q, a) for a in plant.uc), 'handover is not UC-quiescent')
            goal_targets[sid] = {'endpoint_state': matching[0], 'goal_id': data['endpoints']['new']['projection'][matching[0]]['goal_id']}
    uc_buckets = uc_outcomes = selected_buckets = selected_outcomes = 0
    max_bucket = 0
    for sid, q in states.items():
        if q['goal']:
            continue
        require(out[sid], 'non-goal deadlock')
        enabled_uc = {a for a in plant.uc if plant.post(q, a)}
        require(enabled_uc <= set(out[sid]), 'enabled UC bucket omitted')
        require(not enabled_uc or set(out[sid]) <= plant.uc, 'control selected before UC quiescence')
        for a, targets in out[sid].items():
            expected = plant.post(q, a)
            observed = {key(states[t]) for t in targets}
            require(expected and observed == expected, 'selected action omits/adds semantic outcomes')
            require(all(states[t]['rank'] < q['rank'] for t in targets), 'rank does not strictly decrease')
            selected_buckets += 1; selected_outcomes += len(expected)
            max_bucket = max(max_bucket, len(expected))
            if a in plant.uc:
                uc_buckets += 1; uc_outcomes += len(expected)
    # Complete environment-closed reachability of the supplied policy, no search for a policy.
    reached = {q['id'] for q in states.values() if q['initial']}; todo = deque(reached)
    while todo:
        s = todo.popleft()
        for targets in out[s].values():
            for t in targets:
                if t not in reached:
                    reached.add(t); todo.append(t)
    require(reached == set(states), 'saved/expanded policy includes unreachable nodes')
    # DAG dynamic programming checks all finite paths and exact path-length bounds.
    minima = {}; maxima = {}; transfer_min = {}; transfer_max = {}
    for sid in sorted(states, key=lambda s: states[s]['rank']):
        if states[sid]['goal']:
            minima[sid] = maxima[sid] = transfer_min[sid] = transfer_max[sid] = 0
            continue
        continuations = [(a, t) for a, ts in out[sid].items() for t in ts]
        minima[sid] = 1 + min(minima[t] for _, t in continuations)
        maxima[sid] = 1 + max(maxima[t] for _, t in continuations)
        transfer_min[sid] = min((a in plant.updates) + transfer_min[t] for a, t in continuations)
        transfer_max[sid] = max((a in plant.updates) + transfer_max[t] for a, t in continuations)
        require(maxima[sid] <= states[sid]['rank'], 'rank underestimates completion bound')
    return {'states': len(states), 'edges': len(edges), 'entries': len(entries), 'goals': len(goal_targets),
            'uc_buckets': uc_buckets, 'uc_outcomes': uc_outcomes,
            'selected_buckets': selected_buckets, 'selected_outcomes': selected_outcomes,
            'maximum_outcomes_per_bucket': max_bucket,
            'max_entry_rank': max(q['rank'] for q in states.values() if q['initial']),
            'goal_targets': goal_targets, 'path_min': minima, 'path_max': maxima,
            'transfer_min': transfer_min, 'transfer_max': transfer_max}


def transform(fine, saved):
    n = len(fine['components'])
    states = copy.deepcopy(saved['states']); by = {q['id']: q for q in states}
    singleton = ['rho_' + str(i + 1) for i in range(n)]
    for q in states:
        q['pending'] = singleton[:] if q['pending'] else []
        q['memory'] = {'mode': 'saved', 'saved_state': q['id']}
        if not q['goal']:
            q['rank'] += n - 1
    ordinary_edges = [list(e) for e in saved['strategy_edges'] if e[1] != MERGED]
    transfers = [e for e in saved['strategy_edges'] if e[1] == MERGED]
    require(len(transfers) == 1, 'scope requires one saved merged edge per policy')
    s, _, t = transfers[0]
    require(by[t]['goal'], 'scope requires merged edge directly reaches saved goal')
    require(all(v == 'OLD' for v, _ in by[s]['physical']), 'merged source is not all OLD')
    edges = ordinary_edges[:]; next_id = max(by) + 1; current = s; chain = []
    for k, action in enumerate(singleton, 1):
        if k == n:
            target = t
        else:
            q = copy.deepcopy(by[s]); q['id'] = next_id; next_id += 1
            for j in range(k):
                q['physical'][j][0] = 'NEW'
            q['pending'] = singleton[k:]; q['rank'] = n - k
            q['initial'] = False; q['goal'] = False
            q['memory'] = {'mode': 'inside_saved_block', 'checkpoint': s,
                           'saved_target': t, 'completed_members': k,
                           'remaining_members': singleton[k:]}
            states.append(q); by[q['id']] = q; target = q['id']
        edges.append([current, action, target]); chain.append([current, action, target]); current = target
    expanded = {'schema': 'saved-threads-serial-policy-v1', 'decision': 'WIN',
                'states': states, 'strategy_edges': edges,
                'construction': {'source': 'saved merged policy only', 'order': singleton,
                                 'saved_edge': transfers[0], 'replacement_chain': chain,
                                 'ordinary_edges_copied_without_change': len(ordinary_edges)}}
    return expanded


def verify_correspondence(fine, saved, expanded, coarse_result, fine_result):
    n = len(fine['components'])
    old_by = {q['id']: q for q in saved['states']}; new_by = {q['id']: q for q in expanded['states']}
    old_ordinary = {tuple(e) for e in saved['strategy_edges'] if e[1] != MERGED}
    new_ordinary = {tuple(e) for e in expanded['strategy_edges'] if e[1] in fine['ordinary']}
    require(old_ordinary == new_ordinary, 'ordinary policy edges changed')
    chain = expanded['construction']['replacement_chain']
    require(len(chain) == n and [e[1] for e in chain] == ['rho_' + str(i + 1) for i in range(n)], 'wrong replacement order/length')
    source, _, target = expanded['construction']['saved_edge']
    require([e for e in saved['strategy_edges'] if e[1] == MERGED] ==
            [expanded['construction']['saved_edge']], 'recorded saved edge differs')
    require({tuple(e) for e in expanded['strategy_edges'] if e[1] not in fine['ordinary']} ==
            {tuple(e) for e in chain}, 'actual transfer edges differ from recorded replacement chain')
    require(chain[0][0] == source and chain[-1][2] == target, 'replacement endpoints differ')
    require(all(chain[i][2] == chain[i+1][0] for i in range(n-1)), 'replacement chain disconnected')
    require(coarse_result['goal_targets'] == fine_result['goal_targets'], 'fixed endpoint target changed')
    plant = Plant(fine)
    added = set(new_by) - set(old_by)
    require(len(added) == n - 1, 'wrong intermediate-state count')
    require({e[2] for e in chain[:-1]} == added, 'extra/missing phase state')
    for sid in added:
        q = new_by[sid]
        require(not any(plant.post(q, a) for a in plant.uc), 'UC interleaving present: this restricted chain transformer does not handle it')
        require(sum(e[0] == sid for e in expanded['strategy_edges']) == 1, 'phase branches unexpectedly')
        phase = q['memory']
        require(phase['mode'] == 'inside_saved_block' and phase['checkpoint'] == source and
                phase['saved_target'] == target and phase['remaining_members'] == q['pending'] and
                phase['completed_members'] + len(q['pending']) == n, 'finite-memory phase does not match block progress')
    for sid, q in old_by.items():
        require(physical(q) == physical(new_by[sid]), 'original physical node changed')
        if q['initial']:
            require(new_by[sid]['rank'] - q['rank'] == n-1, 'entry rank extension differs')
            require(coarse_result['transfer_min'][sid] == coarse_result['transfer_max'][sid] == 1, 'coarse complete path does not use exactly one block')
            require(fine_result['transfer_min'][sid] == fine_result['transfer_max'][sid] == n, 'expanded complete path does not use exactly n transfers')
            require(fine_result['path_min'][sid] - coarse_result['path_min'][sid] == n-1, 'minimum path overhead differs')
            require(fine_result['path_max'][sid] - coarse_result['path_max'][sid] == n-1, 'maximum path overhead differs')
    # Same ordinary graph and deterministic no-interleaving chain establish a
    # path bijection after contracting the chain, stronger than matching extrema.
    return {'contracted_ordinary_graph_identical': True, 'path_bijection_after_chain_contraction': True,
            'all_complete_paths_exact_extra_events': n - 1,
            'phase_states': len(added), 'phase_enabled_uc_buckets': 0,
            'same_saved_goal_and_unique_fixed_endpoint': True}


def check_case(fine, merged, saved):
    pairs = validate_inputs(fine, merged)
    old, old_stats = endpoint_check(fine, 'old')
    new, new_stats = endpoint_check(fine, 'new')
    coarse = verify_policy(merged, saved, old, new)
    expanded = transform(fine, saved)
    checked = verify_policy(fine, expanded, old, new)
    correspondence = verify_correspondence(fine, saved, expanded, coarse, checked)
    return expanded, {'local_transfer_pairs': pairs, 'old_endpoint': old_stats,
                      'new_endpoint': new_stats, 'saved_merged': coarse,
                      'expanded_fine': checked, 'correspondence': correspondence}


def negative_controls(fine, merged, saved):
    records = []
    expanded, _ = check_case(fine, merged, saved)
    old, _ = endpoint_check(fine, 'old'); new, _ = endpoint_check(fine, 'new')
    mutations = []
    q = copy.deepcopy(expanded)
    remove = next(e for e in q['strategy_edges'] if e[1] == 'arrival')
    q['strategy_edges'].remove(remove); mutations.append(('omitted_uncontrollable_outcome', fine, q, old, new))
    q = copy.deepcopy(expanded); next(s for s in q['states'] if s['initial'])['initial'] = False
    mutations.append(('missing_initial_entry', fine, q, old, new))
    q = copy.deepcopy(expanded); q['states'][-1]['rank'] = 99999
    mutations.append(('nondecreasing_rank', fine, q, old, new))
    q = copy.deepcopy(expanded); q['states'][-1]['physical'][0][1] = 'B_q0'
    mutations.append(('nonidentity_transfer_outcome', fine, q, old, new))
    d = copy.deepcopy(fine); goal = next(s for s in expanded['states'] if s['goal'])
    ep = next(s for s, p in new.items() if p == physical(goal)); d['endpoints']['new']['loadable'].remove(ep)
    mutations.append(('unloadable_fixed_endpoint', d, copy.deepcopy(expanded), old, new))
    for name, d, p, op, np in mutations:
        try:
            verify_policy(d, p, op, np)
            records.append({'control': name, 'status': 'FAIL', 'reason': 'corruption was accepted'})
        except Invalid as error:
            records.append({'control': name, 'status': 'PASS', 'reason': str(error)})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args(); root = args.root.resolve(); output = args.output or root / 'output'
    provenance = read(root / 'provenance.json')
    cases = provenance['cases']
    require({(c['n'], c['B']) for c in cases} == {(n,b) for n in range(2,7) for b in (1,2)} and len(cases) == 10,
            'cohort is not the complete prespecified ten saved cases')
    rows = []; analyses = []; controls = []
    for case in cases:
        row = {'id': case['id'], 'n': case['n'], 'B': case['B'], 'status': 'FAIL', 'failure': ''}
        try:
            files = {k: read(root / v['copied_file']) for k,v in case['files'].items()}
            fine, merged, saved = files['fine.json'], files['merged.json'], files['certificate.json']
            require(fine['parameters']['n'] == case['n'] and fine['parameters']['B'] == case['B'], 'case parameters differ')
            expanded, analysis = check_case(fine, merged, saved)
            saved_stats, fine_stats = analysis['saved_merged'], analysis['expanded_fine']
            recorded = files['saved_result.json']
            require(recorded['decision'] == 'WIN' and recorded['certificate_states'] == saved_stats['states'], 'saved result/policy mismatch')
            require(recorded['worst_completion_rank'] == saved_stats['max_entry_rank'], 'saved rank metadata mismatch')
            row.update(status='PASS', entries=saved_stats['entries'], saved_states=saved_stats['states'],
                       saved_edges=saved_stats['edges'], expanded_states=fine_stats['states'], expanded_edges=fine_stats['edges'],
                       uc_buckets=fine_stats['uc_buckets'], uc_outcomes=fine_stats['uc_outcomes'],
                       selected_buckets=fine_stats['selected_buckets'], selected_outcomes=fine_stats['selected_outcomes'],
                       max_outcomes_per_bucket=fine_stats['maximum_outcomes_per_bucket'],
                       saved_max_rank=saved_stats['max_entry_rank'], expanded_max_rank=fine_stats['max_entry_rank'],
                       exact_extra_events=case['n']-1, phase_uc_buckets=0, same_fixed_endpoint=True,
                       entries_check='PASS', all_uc_check='PASS', all_outcomes_check='PASS', rank_check='PASS',
                       endpoint_check='PASS', exact_overhead_check='PASS')
            analysis.update(id=case['id'], status='PASS'); analyses.append(analysis)
            write(output / 'policies' / (case['id'] + '.json'), expanded)
            for control in negative_controls(fine, merged, saved):
                control['id'] = case['id']; controls.append(control)
        except (Invalid, KeyError, ValueError, TypeError) as error:
            row['failure'] = str(error); analyses.append({'id': case['id'], 'status': 'FAIL', 'failure': str(error)})
        rows.append(row)
    output.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with (output / 'summary.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows)
    write(output / 'analysis.json', {'scope': 'Static saved-policy transformation; no new synthesis or timing measurements',
                                    'cases': analyses})
    write(output / 'negative_controls.json', controls)
    totals = {k: sum(r.get(k, 0) for r in rows) for k in ('entries','saved_states','saved_edges','expanded_states','expanded_edges','uc_buckets','uc_outcomes','selected_buckets','selected_outcomes')}
    summary = {'status': 'PASS' if all(r['status'] == 'PASS' for r in rows) and all(c['status'] == 'PASS' for c in controls) else 'FAIL',
               'cases': len(rows), 'passed': sum(r['status']=='PASS' for r in rows),
               'failed': sum(r['status']!='PASS' for r in rows),
               'negative_controls': len(controls), 'negative_controls_passed': sum(c['status']=='PASS' for c in controls),
               'totals': totals,
               'limitations': ['Ten related finite Threads backpressure abstractions, not ten independent applications.',
                               'OLD and NEW local LTSs are identical; each idle transfer is deterministic identity and requirements/precedence are empty.',
                               'No UC action is enabled at any inserted phase; this checks no nontrivial transfer/UC interleaving.',
                               'All checked action buckets have one outcome; full outcomes are checked but no nondeterministic transfer outcome is present.',
                               'The finite-memory controller stores the saved checkpoint and remaining block members; it is an explicit model policy, not a runtime deployment.',
                               'Event overhead is exactly n-1 before reaching the preserved endpoint; it is not execution time or a synthesis speedup.',
                               'No claim about E1 industrial policies, boundary merging, monitors/initializers, saturated-offer LOSS cases, or deployed behavior.']}
    write(output / 'summary.json', summary)
    print(json.dumps(summary, indent=2)); return 0 if summary['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Read-only Policy figure checks against saved inputs and the WIN certificate.

No candidate code, generator, solver, TeX build or new experiment is executed.
The seven displayed vertices are identified by their unique certificate ranks.
Band membership and command boundaries are derived independently of coordinates.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import re

import check_visual_evidence as base

require = base.require
BITS = ('old_audit', 'new_audit', 'old_role', 'new_role')
LABELS = {'Old audit': 'old_audit', 'New audit': 'new_audit',
          'Old role': 'old_role', 'New role': 'new_role'}
ACTIONS = {'service': 'service', r'start\\new audit': 'start_audit',
           r'stop\\old audit': 'stop_audit', r'stop\\old role': 'stop_role',
           r'identity\\transfer': 'rho_runtime', r'start\\new role': 'start_role'}
NUMBER = r'-?(?:\d+(?:\.\d*)?|\.\d+)'


def transition(tester, state, event):
    if state in tester['errors']:
        return state
    found = [target for source, action, target in tester['changes']
             if source == state and action == event]
    require(len(found) <= 1, 'policy_input', 'Monitor is not deterministic')
    return found[0] if found else state


def verify_saved_contract(fine, coarse, certificate):
    ordinary = ['log_old', 'log_new', 'service', 'access_old', 'access_new']
    require(fine['ordinary'] == fine['controllable'] == ordinary,
            'policy_input', 'Five ordinary events must all be controllable')
    require(fine['precedence'] == [] and len(fine['components']) == 1,
            'policy_input', 'One component and no supplied precedence')
    runtime = fine['components'][0]
    require(runtime['transfer_action'] == 'rho_runtime' and
            runtime['transfer'] == {'running': ['running']}, 'policy_input', 'Identity transfer')
    for version in ('old', 'new'):
        require(runtime[version] == {'initial': 'running', 'states': ['running'],
                'edges': [['running', event, 'running'] for event in ordinary]},
                'policy_input', 'Runtime self-loops for ' + version)
    requirements = {r['id']: r for r in fine['requirements']}
    require(set(requirements) == set(BITS) | {'coverage_and_exclusion'},
            'policy_input', 'Four lifetime monitors and one interval monitor')
    for version, opposite in (('old', 'new'), ('new', 'old')):
        audit = requirements[version + '_audit']['tester']
        role = requirements[version + '_role']['tester']
        require(audit['initial'] == 'unlogged' and set(audit['states']) == {'unlogged', 'logged', 'ERROR'}
                and audit['errors'] == ['ERROR'] and
                set(map(tuple, audit['changes'])) == {('unlogged', 'log_' + version, 'logged'),
                    ('logged', 'service', 'unlogged'), ('unlogged', 'service', 'ERROR')},
                'policy_input', version + ' audit transitions')
        require(role['initial'] == 'valid' and set(role['states']) == {'valid', 'ERROR'}
                and role['errors'] == ['ERROR'] and role['changes'] == [['valid', 'access_' + opposite, 'ERROR']],
                'policy_input', version + ' role transition')
    for rid, initialized in (('new_audit', 'unlogged'), ('new_role', 'valid')):
        require(requirements[rid]['activation']['entries'] == [
            {'physical': [[version, 'running']], 'tester_state': initialized, 'residual_state': initialized}
            for version in ('OLD', 'NEW')], 'policy_input', rid + ' activation')
    interval = requirements['coverage_and_exclusion']['tester']
    safe_bits = {''.join(map(str, (a, b, c, d))) for a in (0, 1) for b in (0, 1)
                 for c in (0, 1) for d in (0, 1) if (a or b) and not (c and d)}
    require(interval['initial'] == '1010' and set(interval['states']) == safe_bits | {'ERROR'}
            and interval['errors'] == ['ERROR'], 'policy_input', 'Coverage and role exclusion')
    for state in safe_bits:
        for event, index, value in (('stop_audit', 0, '0'), ('start_audit', 1, '1'),
                                    ('stop_role', 2, '0'), ('start_role', 3, '1')):
            next_bits = list(state); next_bits[index] = value; next_bits = ''.join(next_bits)
            require(transition(interval, state, event) == (next_bits if next_bits in safe_bits else 'ERROR'),
                    'policy_input', (state, event))
        require(all(transition(interval, state, event) == state for event in ordinary + ['rho_runtime']),
                'policy_input', 'Ordinary events and transfer preserve active bits')
    expected_initials = []
    for version in ('old', 'new'):
        endpoint = fine['endpoints'][version]
        edges = [['unlogged', 'log_' + version, 'logged'], ['logged', 'service', 'unlogged'],
                 ['unlogged', 'access_' + version, 'unlogged'], ['logged', 'access_' + version, 'logged']]
        require(endpoint['lts'] == {'initial': 'unlogged', 'states': ['unlogged', 'logged'], 'edges': edges},
                'policy_input', version + ' endpoint behavior')
        reachable_edges = [e for e in endpoint['controller']['edges'] if e[0] != 'alphabet_only']
        require(reachable_edges == edges and endpoint['controller']['initial'] == 'unlogged',
                'policy_input', version + ' endpoint controller')
        require(set(endpoint['projection']) == {'unlogged', 'logged'}, 'policy_input', 'Both endpoint states')
        for memory, projection in endpoint['projection'].items():
            require(projection['physical'] == [[version.upper(), 'running']] and
                    projection['testers'] == {version + '_audit': memory, version + '_role': 'valid'},
                    'policy_input', version + ' endpoint projection')
            if version == 'old':
                expected_initials.append((projection['physical'],
                    {**projection['testers'], 'coverage_and_exclusion': '1010'}))
        if version == 'new':
            require(endpoint['loadable'] == ['unlogged', 'logged'], 'policy_input', 'Both new targets loadable')
    require(certificate['decision'] == 'WIN' and len(certificate['states']) == 7
            and len(certificate['strategy_edges']) == 6, 'policy_certificate', 'Complete seven-state WIN policy')
    states = {s['id']: s for s in certificate['states']}
    require(len(states) == 7 and set(s['rank'] for s in states.values()) == set(range(7)),
            'policy_certificate', 'Unique ids and ranks')
    initial_states = [s for s in states.values() if s['initial']]
    require(len(initial_states) == 2 and all(any(s['physical'] == p and s['testers'] == t
            for s in initial_states) for p, t in expected_initials), 'policy_certificate', 'Both old entries')
    for state in states.values():
        actual_bits = ''.join('1' if rid in state['testers'] else '0' for rid in BITS)
        require(state['safe'] and state['testers']['coverage_and_exclusion'] == actual_bits
                and actual_bits in safe_bits and 'ERROR' not in state['testers'].values(),
                'policy_certificate', 'Safe monitor membership at ' + str(state['id']))
        target = any(state['physical'] == target['physical'] and
                     all(state['testers'].get(k) == v for k, v in target['testers'].items())
                     for target in fine['endpoints']['new']['projection'].values())
        require(state['goal'] == (not state['pending'] and target) and (state['rank'] == 0) == state['goal'],
                'policy_certificate', 'Terminal predicate and rank zero')
    for source, event, target in certificate['strategy_edges']:
        before, after = states[source], states[target]
        require(before['rank'] == after['rank'] + 1, 'policy_certificate', 'Every displayed event decreases rank')
        physical = deepcopy(before['physical'])
        testers = {rid: transition(requirements[rid]['tester'], state, event)
                   for rid, state in before['testers'].items()}
        pending = set(before['pending'])
        if event not in ordinary:
            require(event in pending, 'policy_certificate', 'Command pending')
            pending.remove(event)
            if event == runtime['transfer_action']:
                require(physical == [['OLD', 'running']], 'policy_certificate', 'Old physical source for transfer')
                physical = [['NEW', 'running']]
            else:
                affected = [r for r in requirements.values() if r.get('update_action') == event]
                require(len(affected) == 1, 'policy_certificate', 'Individual requirement command')
                req = affected[0]
                if req['role'] == 'old':
                    testers.pop(req['id'])
                else:
                    activation = [a for a in req['activation']['entries'] if a['physical'] == physical]
                    require(len(activation) == 1, 'policy_certificate', 'Unique supplied initializer')
                    testers[req['id']] = activation[0]['tester_state']
        require((physical, testers, pending) == (after['physical'], after['testers'], set(after['pending'])),
                'policy_certificate', (source, event, target))
    coarse_interval = next(r['tester'] for r in coarse['requirements'] if r['role'] == 'interval')
    require({r['id']: r.get('update_action') for r in coarse['requirements'] if r['role'] != 'interval'} ==
            {rid: 'ablation.merge.' + ('stops' if rid.startswith('old_') else 'starts') for rid in BITS},
            'policy_grouped', 'Both old stops and both new starts are grouped')
    require(coarse['precedence'] == [] and all(transition(coarse_interval, '1010', e) == 'ERROR'
            for e in ('ablation.merge.starts', 'ablation.merge.stops')),
            'policy_grouped', 'Either first grouped boundary is unsafe')
    require(all(transition(coarse_interval, '1010', e) == '1010' for e in ordinary + ['rho_runtime']),
            'policy_grouped', 'Other events cannot change active requirement membership')
    return states


def figure_loops(text):
    parsed = []
    for match in re.finditer(r'\\foreach\s+([^\n]+?)\s+in\s*', text):
        data, end = base.group(text, match.end())
        while text[end].isspace(): end += 1
        if text[end] == '{':
            body, end = base.group(text, end)
        else:
            end_body = text.index(';', end) + 1
            body, end = text[end:end_body], end_body
        parsed.append((match[1].strip(), data, body))
    require(len(parsed) == text.count(r'\foreach'), 'policy_parser', 'All loops parsed')
    return parsed


def verify_figure(source, fine, coarse, certificate):
    states = verify_saved_contract(fine, coarse, certificate)
    text = base.clean(source)
    require(not re.search(r'\\(?:if\w*|else|fi|newcommand|renewcommand|include|input)\b|opacity|clip', text),
            'policy_visibility', 'No hidden or external figure rendering')
    loops = figure_loops(text)
    require([row[0] for row in loops] == [r'\x/\r', r'\left/\right/\word', r'\y'],
            'policy_inventory', 'One state path, one edge path, four band baselines')
    require(base.norm(loops[0][2]) == base.norm(r'\node[policynode] (r\r) at (\x,0) {\r};') and
            base.norm(loops[1][2]) == base.norm(r'\draw[->] (r\left)--(r\right) node[midway,action,yshift=2pt] {\word};'),
            'policy_binding', 'Rank and action label bindings')
    require(base.norm(r'policynode/.style={draw,circle,minimum size=.33cm,inner sep=1pt,font=\footnotesize}') in base.norm(text),
            'policy_binding', 'Visible rank circles')
    by_rank = {s['rank']: s for s in states.values()}
    positions = {}
    for row in loops[0][1].split(','):
        x, rank = row.split('/'); rank, x = int(rank), Decimal(x)
        require(rank not in positions and x.is_finite(), 'policy_states', 'Unique finite state position')
        positions[rank] = x
    require(set(positions) == set(by_rank) and list(positions) == list(range(6, -1, -1)) and
            list(positions.values()) == sorted(set(positions.values())), 'policy_states', 'Seven ordered certificate ranks')
    edges, boundaries = [], {}
    for row in loops[1][1].split(','):
        left, right, label = row.strip().split('/', 2)
        word, end = base.group(label, 0)
        require(not label[end:].strip() and word in ACTIONS, 'policy_actions', 'Known visible action')
        left, right = int(left), int(right); action = ACTIONS[word]
        require(left in by_rank and right in by_rank, 'policy_actions', 'Known ranks')
        edges.append((by_rank[left]['id'], action, by_rank[right]['id']))
        boundaries[action] = (positions[left] + positions[right]) / 2
    require(Counter(edges) == Counter(map(tuple, certificate['strategy_edges'])),
            'policy_edges', 'All and only six saved strategy edges')
    annotations = re.findall(r'\\node\[font=\\footnotesize,align=center,anchor=north\]\s*at\s*\((' +
                             NUMBER + r'),-\.24\)\s*\{([^{}]+)\};', text)
    expected_annotations = {(positions[s['rank']], s['testers']['old_audit'])
                            for s in states.values() if s['initial']}
    expected_annotations.add((positions[0], r'fixed new\\target'))
    require(len(annotations) == 3 and {(Decimal(x), label) for x, label in annotations} == expected_annotations,
            'policy_state_annotations', 'Logged/unlogged entries and fixed goal labels bind to their vertices')
    label_pattern = (r'\\node\[bandlabel\]\s*at\s*\((' + NUMBER + r'),(' + NUMBER + r')\)\s*\{([^{}]+)\};')
    labels = {}
    for x, y, label in re.findall(label_pattern, text):
        require(label in LABELS and Decimal(y) not in labels and Decimal(x) < min(positions.values()),
                'policy_band_binding', 'Unique left-side active-requirement label')
        labels[Decimal(y)] = LABELS[label]
    require(set(labels.values()) == set(BITS), 'policy_band_inventory', 'Four labels')
    rectangles = re.findall(r'\\draw\[fill=([^,]+),draw=([^\]]+)\]\s*\((' + NUMBER + r'),(' + NUMBER +
                            r')\)\s*rectangle\s*\((' + NUMBER + r'),(' + NUMBER + r')\);', text)
    require(len(rectangles) == 4 and len(rectangles) == len(re.findall(r'\brectangle\b', text)),
            'policy_band_inventory', 'Four active intervals')
    bands = {}
    for fill, stroke, x1, y1, x2, y2 in rectangles:
        x1, y1, x2, y2 = map(Decimal, (x1, y1, x2, y2)); center = (y1 + y2) / 2
        require(center in labels and x1 < x2 and y2 - y1 == Decimal('.28'), 'policy_band_binding', 'Band-label geometry')
        rid = labels[center]; color = 'blue' if 'audit' in rid else 'orange'
        require(rid not in bands and fill == color + '!15' and stroke == color + '!60!black',
                'policy_band_binding', 'Audit/role color and unique band')
        bands[rid] = (x1, x2)
    for rank, x in positions.items():
        actual = ''.join('1' if bands[rid][0] <= x <= bands[rid][1] else '0' for rid in BITS)
        require(actual == by_rank[rank]['testers']['coverage_and_exclusion'],
                'policy_band_states', (rank, actual, by_rank[rank]['testers']['coverage_and_exclusion']))
    start, end = min(positions.values()), max(positions.values()) + Decimal('.2')
    expected_bands = {'old_audit': (start, boundaries['stop_audit']),
                      'new_audit': (boundaries['start_audit'], end),
                      'old_role': (start, boundaries['stop_role']),
                      'new_role': (boundaries['start_role'], end)}
    require(bands == expected_bands, 'policy_band_boundary', 'Band ends at the associated command midpoint')
    for literal in ('{logged}', '{unlogged}', r'{fixed new\\target}',
                    'the first start leaves both roles active', 'the first stop leaves no audit',
                    'Both roles inactive: allowed', 'New-audit start resets to unlogged',
                    'no service-continuity guarantee'):
        require(literal in text, 'policy_interpretation', literal)
    return {'states': 7, 'edges': 6, 'entry_ids': sorted(s['id'] for s in states.values() if s['initial']),
            'goal_ids': sorted(s['id'] for s in states.values() if s['goal']),
            'displayed_ids': [by_rank[r]['id'] for r in positions],
            'ranks': list(positions), 'active_bits': [by_rank[r]['testers']['coverage_and_exclusion'] for r in positions],
            'bands': {k: list(map(str, v)) for k, v in bands.items()},
            'new_audit_initializer': 'unlogged', 'new_role_initializer': 'valid',
            'ordinary_all_controllable': True, 'precedence': [], 'role_gap_permitted': True,
            'first_grouped_start_or_stop_unsafe': True, 'candidate_code_executed': False}


def verify(root):
    from read_saved_source import read_source
    logical = 'FSE2027_SUBMISSION_20260914/experiments/witness_20260929/e6/policy/v2/'
    def evidence(relative):
        return json.loads(read_source(root, logical + relative))
    result = verify_figure((root/'paper/source/figures/policy_lifetimes.tex').read_text(),
                          evidence('inputs/policy_2_fine.json'),
                          evidence('inputs/policy_2_coarse.json'),
                          evidence('raw/series/policy_fine_none_lazy/certificate.json'))
    return {'status': 'PASS', 'details': result}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.artifact_root.resolve()), indent=2))


if __name__ == '__main__':
    main()

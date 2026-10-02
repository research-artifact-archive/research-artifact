#!/usr/bin/env python3
"""Check all thirteen PC2 active suffixes in existing source and saved graphs.

This is restricted static analysis of one saved policy, not a model compiler,
solver, endpoint verifier, or general LTL/initializer correctness checker.
"""
import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path

BASE = Path('FSE2027_SUBMISSION_20260914/experiments/witness_20260929/e6/pc2_rolling/v2')
CERTIFICATE = BASE / 'validation/export/lazy_none/certificate.json'
SOURCE = BASE / 'inputs/ProductionCell_Arms2_Calibration.lts'
PUBLIC_CERTIFICATE = Path('results/granularity/e6/pc2_rolling/v2/validation/export/lazy_none/certificate.json')
PUBLIC_SOURCE = Path('results/granularity/e6/pc2_rolling/v2/inputs/ProductionCell_Arms2_Calibration.lts')
REQUIREMENTS = [
    'P_AVOID_STAMPING_1', 'P_AVOID_STAMPING_2', 'P_CAL_AVAILABILITY',
    'P_CLEAN_ONCE_1', 'P_CLEAN_ONCE_2', 'P_DRILL_ONCE_1', 'P_DRILL_ONCE_2',
    'P_NEW_OUT_IF_FINISHED_1', 'P_NEW_OUT_IF_FINISHED_2',
    'P_NEW_TOOL_ORDER_1', 'P_NEW_TOOL_ORDER_2', 'P_PAINT_ONCE_1', 'P_PAINT_ONCE_2',
]
CHAIN = [(20-i, 'startNewSpec_'+name, 19-i) for i, name in enumerate(REQUIREMENTS)]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compact(text):
    return re.sub(r'\s+', '', text)


def normalized(text):
    return re.sub(r'\[([12])\]', r'.\1', text)


def expression_tree(text):
    """Restricted propositional grammar, with right-associative implication."""
    text = normalized(compact(text))
    tokens = re.findall(r'->|&&|\|\||[!()]|[A-Za-z_]\w*\.[12]', text)
    require(''.join(tokens) == text, 'Unsupported invariant syntax: '+text)
    offset = 0

    def accept(token):
        nonlocal offset
        if offset < len(tokens) and tokens[offset] == token:
            offset += 1
            return True
        return False

    def unary():
        nonlocal offset
        if accept('!'):
            return ('!', unary())
        if accept('('):
            value = implication()
            require(accept(')'), 'Unbalanced invariant expression')
            return value
        require(offset < len(tokens) and re.fullmatch(r'[A-Za-z_]\w*\.[12]', tokens[offset]), 'Missing proposition')
        token = tokens[offset]
        offset += 1
        return ('atom', token)

    def conjunction():
        value = unary()
        while accept('&&'):
            value = ('&&', value, unary())
        return value

    def disjunction():
        value = conjunction()
        while accept('||'):
            value = ('||', value, conjunction())
        return value

    def implication():
        value = disjunction()
        if accept('->'):
            value = ('->', value, implication())
        return value

    tree = implication()
    require(offset == len(tokens), 'Trailing invariant syntax')
    return tree


def evaluate(tree, valuation):
    operator = tree[0]
    if operator == 'atom':
        require(tree[1] in valuation, 'Unregistered proposition '+tree[1])
        return bool(valuation[tree[1]])
    if operator == '!':
        return not evaluate(tree[1], valuation)
    left, right = evaluate(tree[1], valuation), evaluate(tree[2], valuation)
    return {'&&': left and right, '||': left or right, '->': (not left) or right}[operator]


def source_interpretation(source):
    code = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    require(re.search(r'^const N = 2\s*$', code, re.M) and re.search(r'^const K = 1\s*$', code, re.M), 'Unexpected source parameters')
    specs = re.findall(r'controllerSpec CLEAN_PAINT_DRILL_CAL\s*=\s*\{\s*safety\s*=\s*\{([^}]+)\}', code)
    require(len(specs) == 1, 'Missing or duplicate new controller safety specification')
    names = [s.strip() for s in specs[0].split(',')]
    require(len(names) == 13 and set(names) == set(REQUIREMENTS), 'New safety requirement set changed')
    expected = {'P_CAL_AVAILABILITY': '(!Calibrating[1] || !Calibrating[2])'}
    for arm in (1, 2):
        expected.update({
            f'P_AVOID_STAMPING_{arm}': f'(!stamp[{arm}])',
            f'P_CLEAN_ONCE_{arm}': f'(clean[{arm}] -> !Cleaned[{arm}])',
            f'P_DRILL_ONCE_{arm}': f'(drill[{arm}] -> !Drilled[{arm}])',
            f'P_PAINT_ONCE_{arm}': f'(paint[{arm}] -> !Painted[{arm}])',
            f'P_NEW_OUT_IF_FINISHED_{arm}': f'(out[{arm}] -> (Drilled[{arm}] && Cleaned[{arm}] && Painted[{arm}]))',
            f'P_NEW_TOOL_ORDER_{arm}': f'((DrillPending[{arm}] -> (Painted[{arm}] && Cleaned[{arm}])) && (PaintPending[{arm}] -> (Cleaned[{arm}] && !Drilled[{arm}])) && (CleanPending[{arm}] -> (!Painted[{arm}] && !Drilled[{arm}])))',
        })
    formulas, trees = {}, {}
    for name in REQUIREMENTS:
        declarations = re.findall(r'^ltl_property '+name+r'\s*=\s*\[\]([^\n]+)$', code, re.M)
        require(len(declarations) == 1, 'Missing or duplicate invariant '+name)
        expression = declarations[0].strip()
        if re.fullmatch(r'\w+', expression):
            aliases = re.findall(r'^assert '+expression+r'\s*=\s*([^\n]+)$', code, re.M)
            require(len(aliases) == 1, 'Missing or duplicate invariant assertion '+name)
            expression = aliases[0].strip()
        require(compact(expression) == compact(expected[name]), 'Source invariant changed: '+name)
        formulas[name], trees[name] = expression, expression_tree(expression)
    atoms = set(re.findall(r'[A-Za-z_]\w*\.[12]', normalized(' '.join(formulas.values()))))
    fluent_names = sorted({a.split('.')[0] for a in atoms if a[0].isupper()})
    event_names = sorted({a.split('.')[0] for a in atoms if a[0].islower()})
    registry = []
    for name in fluent_names:
        declarations = re.findall(r'^fluent '+name+r'\[i:Arms\]\s*=\s*<([^\n]+)>\s*$', code, re.M)
        require(len(declarations) == 1, 'Missing, duplicate, or non-default-initial fluent '+name)
        depth, start, pieces = 0, 0, []
        for offset, char in enumerate(declarations[0]):
            depth += (char == '{') - (char == '}')
            require(depth >= 0, 'Malformed fluent action sets')
            if char == ',' and depth == 0:
                pieces.append(declarations[0][start:offset]); start = offset+1
        pieces.append(declarations[0][start:])
        require(depth == 0 and len(pieces) == 2, 'Malformed fluent declaration')
        for arm in (1, 2):
            actions = []
            for piece in pieces:
                action_set = [normalized(x.strip().replace('[i]', f'[{arm}]')) for x in piece.strip().strip('{}').split(',')]
                require(all(re.fullmatch(r'\w+\.[12]', x) for x in action_set), 'Unsupported fluent action')
                actions.append(action_set)
            registry.append({'name': f'{name}.{arm}', 'kind': 'declared_fluent', 'initial': 0, 'set': actions[0], 'reset': actions[1]})
    for name in event_names:
        for arm in (1, 2):
            registry.append({'name': f'{name}.{arm}', 'kind': 'event_proposition', 'initial': 0, 'set': [f'{name}.{arm}'], 'reset': ['other ordinary event']})
    require(len(registry) == 24 and len(fluent_names) == 7 and len(event_names) == 5, 'Unexpected observer registry')
    require({r['name'] for r in registry} == atoms, 'Observer registry is not the exact formula proposition set')
    for arm in (1, 2):
        cal = next(r for r in registry if r['name'] == f'Calibrating.{arm}')
        require(cal['set'] == [f'beginCalibration.{arm}'] and cal['reset'] == [f'calibrated.{arm}'], 'Calibration fluent update changed')
    # The fixed old physical process has no calibration request in its alphabet.
    old_processes = re.findall(r'//Old Model\s*(.*?)//New Model', source, re.S)
    require(len(old_processes) == 1 and 'beginCalibration' not in old_processes[0], 'Old plant can request calibration or source boundary changed')
    require('||OLD_ENV=(forall[i:Arms]PRODUCTION_CELL_OLD(i)).' in compact(code), 'Old environment changed')
    return formulas, trees, registry


def ordinary(event):
    return re.fullmatch(r'\w+\.[12](?:\.\d+)?', event) is not None


def observer_step(vector, event, registry):
    result = list(vector)
    if ordinary(event):
        for index, record in enumerate(registry):
            if record['kind'] == 'event_proposition':
                result[index] = int(event in record['set'])
            elif event in record['set']:
                result[index] = 1
            elif event in record['reset']:
                result[index] = 0
    return result


def reach(roots, edges):
    adjacency = defaultdict(list)
    for source, _, target in edges:
        adjacency[source].append(target)
    seen, queue = set(roots), deque(roots)
    while queue:
        for target in adjacency[queue.popleft()]:
            if target not in seen:
                seen.add(target); queue.append(target)
    return seen


def parse_pre(description):
    match = re.fullmatch(r'PRE\((\d+):\[(\d+)@\[([0-9, ]*)\], (\d+)\]:\{(.*)\}\)', description)
    require(match is not None, 'Unsupported saved PRE description')
    vector = [int(v) for v in match[3].split(', ')]
    pairs = [pair.split('=') for pair in match[5].split(', ')]
    require(len(vector) == 24 and all(v in (0, 1) for v in vector), 'Invalid PRE observer vector')
    require(all(len(pair) == 2 for pair in pairs), 'Invalid PRE monitor encoding')
    testers = {name: int(value) for name, value in pairs}
    require(len(testers) == len(pairs), 'Duplicate PRE monitor')
    return {'controller': int(match[1]), 'physical': [['OLD', int(match[2]), vector], ['OLD', int(match[4]), []]], 'testers': testers}


def mid_description(state):
    physical = ', '.join(version+'('+str(raw)+('@['+', '.join(map(str, vector))+']' if vector else '')+')' for version, raw, vector in state['physical'])
    return 'MID((['+physical+'], {'+', '.join(k+'='+str(v) for k, v in state['testers'].items())+'}, ['+', '.join(state['pending'])+']))'


def analyze(data, source):
    formulas, trees, registry = source_interpretation(source)
    states = {s['id']: s for s in data['states']}
    edges = [tuple(e) for e in data['strategy_edges']]
    entries = {q for q, s in states.items() if s['initial']}
    goals = {q for q, s in states.items() if s['goal']}
    require(len(states) == len(data['states']), 'Duplicate saved state')
    require(len(edges) == len(set(edges)), 'Duplicate policy edge')
    require(data['decision'] == 'WIN', 'Saved policy is not WIN')
    require((len(states), len(edges), len(entries)) == (381, 522, 126), 'Saved policy population changed')
    require(goals == {7}, 'Saved goal set changed')
    outgoing, incoming = defaultdict(list), defaultdict(list)
    for q, state in states.items():
        require(type(state['rank']) is int and state['rank'] >= 0, 'Invalid natural rank')
        require(state['safe'] is True, 'Saved unsafe state')
        require(len(state['physical']) == 2 and len(state['physical'][0][2]) == 24 and state['physical'][1][2] == [], 'Invalid physical observer shape')
        require(all(type(v) is int and v in (0, 1) for v in state['physical'][0][2]), 'Invalid observer bit')
    for a, event, b in edges:
        require(a in states and b in states, 'Policy edge leaves saved domain')
        require(a not in goals, 'Goal has outgoing edge')
        require(states[a]['rank'] > states[b]['rank'], 'Nondecreasing rank')
        require(observer_step(states[a]['physical'][0][2], event, registry) == states[b]['physical'][0][2], 'Source observer replay disagrees on policy edge')
        outgoing[a].append((a, event, b)); incoming[b].append((a, event, b))
    require(all(q in goals or outgoing[q] for q in states), 'Non-goal deadlock')
    require(states[7]['rank'] == 0, 'Goal rank is nonzero')
    require(reach(entries, edges) == set(states), 'Saved domain differs from entry-reachable closure')
    require(not entries.intersection(range(7, 21)), 'An entry bypasses part of the start chain')
    require([e for e in edges if e[1].startswith('startNewSpec_')] == CHAIN, 'Start chain changed')
    require([e for e in edges if e[0] in range(7, 21)] == CHAIN, 'Extra or missing active-suffix edge')
    require(not any(e.startswith('beginCalibration.') for _, e, _ in edges), 'Policy contains a calibration request')
    for edge in CHAIN:
        require(incoming[edge[2]] == [edge], 'A chain successor has an incoming bypass')

    # Independently replay the saved old prefix graph and bind every update entry
    # to its actual old state through the stored hotSwapIn edge.
    linked = data['linked_state_descriptions']
    require(len(linked) == len(set(linked)), 'Duplicate linked state description')
    pre = {i: parse_pre(t) for i, t in enumerate(linked) if t.startswith('PRE(')}
    linked_edges = [tuple(e) for e in data['linked_edges']]
    require(len(linked_edges) == len(set(linked_edges)), 'Duplicate linked edge')
    require(all(0 <= a < len(linked) and 0 <= b < len(linked) for a, _, b in linked_edges), 'Linked edge leaves domain')
    pre_edges = [e for e in linked_edges if e[0] in pre and e[2] in pre]
    initial = [q for q, s in pre.items() if s['controller'] == 0 and s['physical'] == [['OLD', 0, [0]*24], ['OLD', 0, []]] and all(v == 0 for v in s['testers'].values())]
    require((len(pre), len(pre_edges), len(initial)) == (126, 348, 1), 'Old prefix population or initial tuple changed')
    require(reach(initial, pre_edges) == set(pre), 'Old prefix domain is not initial-reachable')
    require(not any(e.startswith('beginCalibration.') for _, e, _ in pre_edges), 'Old prefix contains a calibration request')
    for a, event, b in pre_edges:
        require(ordinary(event), 'Unexpected old-prefix boundary event')
        require(observer_step(pre[a]['physical'][0][2], event, registry) == pre[b]['physical'][0][2], 'Source observer replay disagrees on old edge')
    def signature(state):
        return json.dumps([state['physical'], {k: v for k, v in state['testers'].items() if k.startswith('old:')}], sort_keys=True)
    pre_signatures = {signature(s): q for q, s in pre.items()}
    require(len(pre_signatures) == len(pre), 'Ambiguous old entry tuple')
    mid_indices = {t: i for i, t in enumerate(linked) if t.startswith('MID(')}
    entry_pre = {}
    for q in sorted(entries):
        old = pre_signatures.get(signature(states[q]))
        mid = mid_indices.get(mid_description(states[q]))
        require(old is not None and mid is not None and (old, 'hotSwapIn', mid) in linked_edges, 'Entry lacks its matching old hot-swap predecessor')
        entry_pre[q] = old
    require(set(entry_pre.values()) == set(pre), 'Entries do not cover all saved old tuples')
    cal_indices = [i for i, r in enumerate(registry) if r['name'].startswith('Calibrating.')]
    require(all(s['physical'][0][2][i] == 0 for s in pre.values() for i in cal_indices), 'Nonzero calibration fluent in old prefix')
    require(all(s['physical'][0][2][i] == 0 for s in states.values() for i in cal_indices), 'Nonzero calibration fluent in saved policy')

    active_records = []
    for count, q in enumerate(range(20, 6, -1)):
        state = states[q]
        expected_testers = {'update_time:R_CAL_READY:0': 0}
        expected_testers.update({f'new:{name}:{i}': 0 for i, name in enumerate(REQUIREMENTS[:count])})
        require(state['physical'] == [['NEW', 1, [0]*24], ['NEW', 1, []]], 'Chain physical/observer tuple changed')
        require(state['rank'] == q-7 and state['testers'] == expected_testers, 'Chain rank or exact monitor set changed')
        require(state['pending'] == ['startNewSpec_'+name for name in REQUIREMENTS[count:]], 'Pending start sequence changed')
        valuation = {r['name']: bit for r, bit in zip(registry, state['physical'][0][2])}
        require(all(evaluate(trees[name], valuation) for name in REQUIREMENTS), 'A source invariant is false on the chain')
    for i, (a, event, b) in enumerate(CHAIN):
        without = [edge for edge in edges if edge != (a, event, b)]
        require(not (reach(entries, without) & goals), 'A maximal completion can avoid a start')
        active_records.append({'requirement': REQUIREMENTS[i], 'source_invariant': formulas[REQUIREMENTS[i]], 'start_edge': [a, event, b], 'active_states_through_handover': list(range(b, 6, -1)), 'installed_monitor': f'new:{REQUIREMENTS[i]}:{i}', 'monitor_state_through_handover': 0, 'source_invariant_true_on_all_active_states': True, 'ordinary_or_transfer_edges_after_activation': [], 'every_maximal_saved_run_crosses_start': True})
    require(data['goal_matches'] == {'7': 'new-00000009'}, 'Handover target changed')
    final_mid = mid_indices.get(mid_description(states[8]))
    post_targets = [b for a, event, b in linked_edges if a == final_mid and event == CHAIN[-1][1]]
    require(len(post_targets) == 1 and linked[post_targets[0]].startswith('POST('), 'Final start lacks a unique linked endpoint successor')
    endpoint = parse_pre(linked[post_targets[0]].replace('POST(', 'PRE(', 1))
    endpoint['physical'] = [['NEW', raw, vector] for _, raw, vector in endpoint['physical']]
    require(endpoint['physical'] == states[7]['physical'] and endpoint['testers'] == {k: v for k, v in states[7]['testers'].items() if k.startswith('new:')}, 'Handover physical, observer, or new monitor alignment failed')
    require(data['certificate_checker'].startswith('PASS') and data['link_checker'].startswith('PASS'), 'Stored checker status is not PASS')
    return {
        'purpose': 'Static source and graph analysis of existing PC2 exports; no synthesis, compiler, solver, experiment, or changed input.',
        'source_certificate': CERTIFICATE.as_posix(), 'source_lts': SOURCE.as_posix(),
        'scope': 'All thirteen new requirements of this one saved PC2-Rolling policy at their reached activation tuples, from every saved entry.',
        'saved_population': {'states': len(states), 'edges': len(edges), 'entries': len(entries), 'goals': sorted(goals)},
        'graph_checks': {'entry_reachable_domain_exact': True, 'closed_domain': True, 'natural_strictly_decreasing_ranks': True, 'non_goal_deadlocks': 0, 'goal_terminal_and_rank_zero': True, 'entry_on_start_chain': False, 'chain_successors_have_only_preceding_incoming_edge': True, 'all_maximal_runs_cross_all_thirteen_starts': True},
        'observer_interpretation': {'registry': registry, 'declared_fluent_coordinates': 14, 'event_proposition_coordinates': 10, 'source_observer_edges_checked': len(edges)+len(pre_edges), 'all_chain_observers_zero': True},
        'old_prefix_and_calibration': {'old_states': len(pre), 'old_edges': len(pre_edges), 'old_initial': initial[0], 'old_domain_initial_reachable': True, 'old_source_has_no_calibration_request': True, 'old_requests': 0, 'policy_requests': 0, 'source_calibration_initial_values': [0, 0], 'all_old_and_policy_calibration_values_zero': True, 'every_entry_bound_to_old_hot_swap_predecessor': True, 'entry_to_old_state': entry_pre, 'argument': 'The old source plant has no beginCalibration action. Its initially false calibration fluents stay false on every saved old edge; all old states are initial-reachable. Exact physical/old-monitor signatures and hotSwapIn edges bind every policy entry to an old state. Replay of all 522 policy edges then preserves those two false bits, including ordinary calibrated events that reset them.'},
        'start_chain': [list(e) for e in CHAIN], 'active_obligations': active_records,
        'handover': {'goal': 7, 'target': 'new-00000009', 'physical': states[7]['physical'], 'new_monitors': {k: v for k, v in states[7]['testers'].items() if k.startswith('new:')}, 'linked_post_state': post_targets[0], 'linked_post_controller': endpoint['controller'], 'linked_endpoint_physical_observers_and_new_monitors_equal': True, 'post_handover_assumption': 'The supplied verified fixed new endpoint and continuation-preserving handover; endpoint semantics are not independently verified by this script.'},
        'stored_checks': {key: data[key] for key in ['certificate_checker', 'link_checker']},
        'not_checked': ['Completeness of exported modeled outcomes', 'Frontend or compiler correctness', 'Full Rolling initializer or every permitted activation tuple', 'All 138 NEW occurrences', 'History-inclusive pre-activation safety', 'Runtime conformance', 'Independent verification of the fixed new endpoint'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=next((p for p in Path(__file__).resolve().parents if (p / CERTIFICATE).is_file() or (p / PUBLIC_CERTIFICATE).is_file()), Path.cwd()))
    parser.add_argument('--certificate', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    certificate = args.certificate or args.repository / (CERTIFICATE if (args.repository / CERTIFICATE).is_file() else PUBLIC_CERTIFICATE)
    source = args.source or args.repository / (SOURCE if (args.repository / SOURCE).is_file() else PUBLIC_SOURCE)
    result = analyze(json.loads(certificate.read_text(encoding='utf-8')), source.read_text(encoding='utf-8'))
    text = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    else:
        print(text, end='')


if __name__ == '__main__':
    main()

"""Author post-outcome checker; reconstructs controller and native work separately."""
from pathlib import Path
from functools import lru_cache
import copy
import hashlib
import itertools
import json
import sys

KINDS = ('K_DIR', 'V_PARENT', 'V_LINK', 'V_UNLINK', 'V_NODE', 'V_CELL')
SCHEDULES = {
    'none': [],
    'k_dir_full': [('K', 1, 'K_DIR', 2, 'FULL')],
    'v_parent_full': [('V', 1, 'V_PARENT', 2, 'FULL')],
    'v_node_full': [('V', 1, 'V_NODE', 4, 'FULL')],
    'v_cell_full': [('V', 1, 'V_CELL', 2, 'FULL')],
    'v_end_full': [('V', 1, 'END', 1, 'FULL')],
    'k_end_split': [('K', 1, 'END', 1, 'START'), ('K', 2, 'END', 1, 'COMPLETE')],
    'v_end_split': [('V', 1, 'END', 1, 'START'), ('V', 2, 'END', 1, 'COMPLETE')],
    'v_node_split': [('V', 1, 'V_NODE', 4, 'START'), ('V', 2, 'V_NODE', 4, 'COMPLETE')],
    'v_two_end_split': [('V', 1, 'END', 1, 'START'), ('V', 2, 'END', 1, 'COMPLETE'),
                        ('V', 3, 'END', 1, 'START'), ('V', 4, 'END', 1, 'COMPLETE')],
    'cross_stage': [('K', 1, 'END', 1, 'START'), ('V', 1, 'END', 1, 'COMPLETE'),
                    ('V', 2, 'END', 1, 'START'), ('V', 3, 'END', 1, 'COMPLETE')],
    'k_full_v_split': [('K', 1, 'END', 1, 'FULL'), ('V', 1, 'END', 1, 'START'),
                       ('V', 2, 'END', 1, 'COMPLETE')]
}
QUOTAS = {name: sum(cut[4] in ('START', 'FULL') for cut in cuts) for name, cuts in SCHEDULES.items()}
POLICIES = ('curve_protected_tie', 'curve_fast_tie', 'local_budget', 'upstream2',
            'unknown_budget_threshold', 'always_protected')


def check(row):
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    require(row['status'] == 'SUCCESS', 'native execution unsuccessful')
    require((row['n'], row['m'], row['r'], row['h']) == (31, 31, 16, 5), 'input shape mismatch')
    require(row['schedule'] in QUOTAS and row['policy'] in POLICIES, 'unknown cell')
    q, lam, policy = QUOTAS[row['schedule']], row['lambda'], row['policy']
    require(lam in (1, 3, 10) and q == row['q_bound'], 'input price or quota mismatch')
    require(row['id'] == f"{lam}_{row['schedule']}_{policy}", 'identity mismatch')
    caps = (32, 160)
    require(row['w_caps'] == list(caps), 'controller caps changed')

    @lru_cache(None)
    def value(j, b):
        if j == 2:
            return 0
        return min((1 + lam) * caps[j] + value(j + 1, b), fast_value(j, b))

    def fast_value(j, b):
        return caps[j] + (value(j + 1, b) if b == 0
                          else max(value(j + 1, b), value(j, b - 1)))

    require(row['model_value'] == (-1 if not policy.startswith('curve_') else value(0, 2 * q)),
            'model DP value mismatch')
    profile_file = Path(__file__).resolve().parent / f'profile_{lam}.txt'
    expected_hash = '' if not policy.startswith('curve_') else hashlib.sha256(profile_file.read_bytes()).hexdigest()
    require(row['profile_sha256'] == expected_hash, 'native imported bytes differ from fixed profile')
    require(row['profile_load_nanoseconds'] >= 0, 'negative import time')
    if not policy.startswith('curve_'):
        require(row['profile_load_nanoseconds'] == 0, 'local baseline unexpectedly loaded curves')

    def desired(j, budget):
        if policy == 'local_budget':
            return budget <= lam
        if policy == 'upstream2':
            return attempts[j] < 2
        if policy == 'unknown_budget_threshold':
            return failures[j] < lam
        if policy == 'always_protected':
            return False
        protect = (1 + lam) * caps[j] + value(j + 1, budget)
        attempt = fast_value(j, budget)
        return attempt < protect if policy == 'curve_protected_tie' else attempt <= protect

    # Independent static-tree DFS.
    order, stack = [], [0]
    while stack:
        node = stack.pop()
        if node < 31:
            order.append(node)
            stack.extend((2 * node + 2, 2 * node + 1))
    require(len(row['rows']) == 16, 'wrong viewport size')
    epochs = []
    for expected, (node, parent, sentinel) in zip(order[:16], row['rows']):
        require(node == expected, 'wrong DFS row/order')
        require(parent == (-2147483648 if node == 0 else (node - 1) // 2), 'wrong parent')
        require((sentinel - node) % 1000 == 0, 'not a source value')
        epochs.append((sentinel - node) // 1000)
    require(len(set(epochs)) == 1, 'mixed epochs in output')

    stages, bodies, checks, writers, decisions = [], [], [], [], []
    active = pending = None
    budget, cycles, completed_cycles = 2 * q, 0, 0
    failures = [0, 0]
    attempts = [0, 0]
    successes = [0, 0]
    cycle_open = False
    clock = None
    expected_body = None
    successful_v_epoch = None
    cuts = SCHEDULES[row['schedule']]
    issued = [False] * len(cuts)
    last_hook = None
    pending_writer = None
    for idx, event in enumerate(row['events']):
        require(len(event) == 6, 'malformed event')
        stage, kind, a, b, c, d = event
        j = 0 if stage == 'K' else 1
        require(stage in ('K', 'V', 'W'), 'unknown stage')
        if kind == 'STAGE':
            require(active is None and pending is None, 'overlapping stage')
            stages.append(stage)
        elif kind == 'POLICY':
            expected_value = -1 if not policy.startswith('curve_') else value(j, budget)
            require((a, c, d) == (budget, failures[j], expected_value), 'policy state/value mismatch')
            require(b in (0, 1) and bool(b) == desired(j, budget), 'incorrect policy choice')
        elif kind == 'DECISION':
            require(a == attempts[j] and b in (0, 1), 'attempt count mismatch')
            require(bool(b) == desired(j, budget), 'decision differs from specified strategy')
            expected_body = 0 if b else 1
            decisions.append({'stage': stage, 'budget': budget, 'fast': bool(b)})
        elif kind in ('BEFORE_LOCK', 'DRAIN_FOR_LOCK'):
            require(active is None and pending is None, 'lock requested before prior body resolved')
            if kind == 'DRAIN_FOR_LOCK':
                require(cycle_open and pending_writer is None, 'drain without an open cycle')
                pending_writer = 'COMPLETE'
        elif kind == 'BEGIN':
            require(active is None and pending is None and successes[j] == 0, 'overlapping or repeated job')
            require(stages and stages[-1] == stage, 'body in wrong stage')
            require(c in (0, 1) and c == expected_body, 'body mode differs from decision')
            require(b in (0, 1) and (not b or a % 2 == 0), 'invalid usePrev clock')
            require(clock is None or a == clock, 'unrecorded clock change before body')
            require(not c or not cycle_open, 'protected body while writer owns cycle')
            clock = a
            active = {'stage': stage, 'before': a, 'use_prev': b, 'protected': c,
                      'begin_index': idx, 'begin_epoch': completed_cycles, 'exception': False, 'work': {k: 0 for k in KINDS}}
            if not c:
                attempts[j] += 1
            expected_body = None
        elif kind in KINDS:
            require(active is not None and active['stage'] == stage, 'work outside body')
            require(a > 0 and b == active['protected'], 'wrong charge or mode')
            require((stage == 'K') == kind.startswith('K_'), 'wrong work type for stage')
            active['work'][kind] += a
            require(active['work']['K_DIR'] <= 32 and active['work']['V_PARENT'] <= 32
                    and active['work']['V_LINK'] <= 32 and active['work']['V_UNLINK'] == 0
                    and active['work']['V_NODE'] <= 32 and active['work']['V_CELL'] <= 64,
                    'source-derived prefix cap violated')
            require(sum(active['work'].values()) <= caps[j], 'prefix total cap violated')
            last_hook = (stage, attempts[j], kind, active['work'][kind], active['protected'])
        elif kind == 'INCONSISTENT_EXCEPTION':
            require(active is not None and not active['protected'] and not active['exception'],
                    'unexpected/duplicate inconsistency exception')
            require((a, b, c, d) == (1, 0, 0, 0), 'bad exception marker')
            active['exception'] = True
        elif kind == 'CUT':
            require(0 <= a < len(cuts) and not issued[a], 'unknown/repeated cut')
            cut_stage, cut_attempt, cut_kind, threshold, action = cuts[a]
            require(last_hook is not None and last_hook[:3] == (cut_stage, cut_attempt, cut_kind)
                    and last_hook[3] >= threshold and last_hook[4] == 0, 'cut did not match body prefix')
            require(stage == cut_stage and b == cut_attempt and c == last_hook[3] and d == 0,
                    'cut metadata mismatch')
            require(pending_writer is None, 'overlapping writer requests')
            pending_writer = action
            issued[a] = True
        elif kind == 'SKIP_CLOSED_CYCLE':
            require(not cycle_open and pending_writer == 'COMPLETE' and (b, c, d) == (0, 0, 0),
                    'illegal completed-cycle skip')
            require(0 <= a < len(cuts) and issued[a] and cuts[a][4] == 'COMPLETE', 'unknown skipped cut')
            pending_writer = None
        elif kind == 'END':
            require(active is not None and active['stage'] == stage, 'unpaired END')
            require((a, b, c) == (active['before'], active['use_prev'], active['protected']), 'END metadata mismatch')
            require(d in (-1, 1) and (d == -1) == active['exception'],
                    'body termination does not match typed inconsistency exception')
            require(not c or d == 1, 'protected body failed')
            active['returned'] = d
            last_hook = (stage, attempts[j], 'END', 1, c)
            work = active['work']
            require(work['K_DIR'] <= 32 and work['V_PARENT'] <= 32 and work['V_LINK'] <= 32
                    and work['V_UNLINK'] == 0 and work['V_NODE'] <= 32 and work['V_CELL'] <= 64,
                    'individual source cap violated')
            active['selected_work'] = sum(work.values())
            require(active['selected_work'] <= caps[j], 'total body cap violated')
            active['cap'] = caps[j]
            bodies.append(active)
            if c:
                require(clock == a, 'writer changed clock in protected body')
                successes[j] += 1
                if j == 1:
                    successful_v_epoch = active['begin_epoch']
            else:
                pending = active
            active = None
        elif kind == 'CHECK':
            require(pending is not None and pending['stage'] == stage, 'CHECK without fast body')
            require((a, c) == (pending['before'], pending['use_prev']) and b == clock, 'CHECK clock metadata mismatch')
            require(d in (0, 1, 3), 'invalid CHECK flags')
            require(bool(d & 1) == (pending['returned'] == 1), 'body result and CHECK flag mismatch')
            consistent = a // 2 == b // 2 and (a % 2 == b % 2 or not c)
            require(bool(d & 2) == consistent, 'native CHECK differs from recorded clock consistency')
            require(not pending['exception'] or not consistent, 'aborted prefix despite consistent clock')
            if not consistent:
                require(any(pending['begin_index'] < w['index'] < idx for w in writers),
                        'failure without actual writer action')
                failures[j] += 1
                budget -= 1
                require(budget >= 0, '2q quota exceeded')
            else:
                successes[j] += 1
                if j == 1:
                    successful_v_epoch = pending['begin_epoch']
            checks.append({'stage': stage, 'failed': not consistent, 'before': a, 'after': b})
            pending = None
        elif kind in ('START', 'COMPLETE', 'FULL'):
            require(stage == 'W' and a == clock, 'unrecorded writer clock change')
            require(kind == pending_writer, 'writer action differs from fixed cut/drain request')
            pending_writer = None
            if kind == 'START':
                require(not cycle_open and a % 2 == 1 and b == a + 1, 'invalid cycle start')
                cycles += 1
                cycle_open = True
            elif kind == 'COMPLETE':
                require(cycle_open and a % 2 == 0 and b == a + 1, 'invalid cycle completion')
                completed_cycles += 1
                cycle_open = False
                require(c == d == b // 2, 'notification step mismatch')
            else:
                require(not cycle_open and a % 2 == 1 and b == a + 2, 'invalid full cycle')
                cycles += 1
                completed_cycles += 1
                require(c == d == b // 2, 'notification step mismatch')
            clock = b
            writers.append({'index': idx, 'kind': kind, 'before': a, 'after': b})
        else:
            require(False, 'unknown event kind: ' + kind)
    require(issued == row['issued_cuts'] and pending_writer is None, 'cut execution ledger mismatch')
    # Every reached eligible fixed cut must have run. Suppressed/unreached cuts remain in the denominator.
    for cut_index, (cut_stage, cut_attempt, cut_kind, threshold, action) in enumerate(cuts):
        candidates = [body for body in bodies if body['stage'] == cut_stage and not body['protected']]
        reached = len(candidates) >= cut_attempt and (cut_kind == 'END'
                    or candidates[cut_attempt - 1]['work'][cut_kind] >= threshold)
        require(issued[cut_index] == reached, 'eligible cut omitted or unreachable cut executed')
    require(active is None and pending is None and stages == ['K', 'V'] and successes == [1, 1],
            'incomplete pipeline or repeated job')
    require(not cycle_open and cycles == completed_cycles == row['q_executed'] <= q, 'cycle ledger mismatch')
    require(epochs[0] == successful_v_epoch and 0 <= epochs[0] <= cycles, 'wrong source epoch for successful V body')
    actual_work = sum(x['selected_work'] for x in bodies)
    protected_work = sum(x['selected_work'] for x in bodies if x['protected'])
    charged_cap = sum(x['cap'] * (1 + lam * x['protected']) for x in bodies)
    cost = actual_work + lam * protected_work
    require(cost <= charged_cap, 'actual cost exceeds charged caps')
    if policy.startswith('curve_'):
        require(charged_cap <= value(0, 2 * q), 'compiled execution exceeds model guarantee')
    return {'id': row['id'], 'policy': policy, 'schedule': row['schedule'], 'lambda': lam,
            'q_bound': q, 'cycles': cycles, 'failures': sum(failures), 'fast_attempts': sum(attempts),
            'protected_bodies': sum(x['protected'] for x in bodies), 'selected_work': actual_work,
            'protected_work': protected_work, 'weighted_cost': cost, 'charged_cap': charged_cap,
            'model_value': value(0, 2 * q), 'aborted_bodies': sum(x['exception'] for x in bodies), 'issued_cuts': issued, 'bodies': bodies, 'checks': checks, 'decisions': decisions}


def main(directory):
    directory = Path(directory)
    output = directory / (sys.argv[2] if len(sys.argv) > 2 else 'check01')
    output.mkdir(exist_ok=False)
    rows = [json.loads(line) for line in (directory / 'RAW.jsonl').read_text().splitlines()]
    expected = {f'{lam}_{schedule}_{policy}' for lam, schedule, policy in
                itertools.product((1, 3, 10), QUOTAS, POLICIES)}
    assert len(rows) == len(expected) == 216 and {r['id'] for r in rows} == expected
    results, errors = [], []
    for row in rows:
        try:
            results.append(check(row))
        except Exception as error:
            errors.append({'id': row['id'], 'error': str(error)})
    controls = []
    if not errors:
        base = next(row for row in rows if row['id'] == '3_v_end_split_curve_fast_tie')
        for mutation in ('mixed_epoch', 'deleted_update', 'excess_work', 'wrong_policy', 'changed_budget'):
            row = copy.deepcopy(base)
            if mutation == 'mixed_epoch':
                row['rows'][0][2] -= 1000
            elif mutation == 'deleted_update':
                row['events'] = [e for e in row['events'] if e[1] != 'START']
            elif mutation == 'excess_work':
                next(e for e in row['events'] if e[1] == 'V_CELL')[2] = 1000
            elif mutation == 'wrong_policy':
                event = next(e for e in row['events'] if e[1] == 'POLICY')
                event[3] = 1 - event[3]
            else:
                next(e for e in row['events'] if e[1] == 'POLICY')[2] += 1
            (output / ('CONTROL_' + mutation + '.json')).write_text(json.dumps(row) + '\n')
            try:
                check(row)
                controls.append({'mutation': mutation, 'rejected': False})
            except ValueError as error:
                controls.append({'mutation': mutation, 'rejected': True, 'reason': str(error)})
    report = {'classification': 'author post-outcome checker, not independent evaluation or source proof',
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'raw_sha256': hashlib.sha256((directory / 'RAW.jsonl').read_bytes()).hexdigest(),
              'denominator': 216, 'checked': len(results), 'errors': errors,
              'controls': controls, 'results': results}
    (output / 'TRACE_CHECK.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('denominator', 'checked', 'errors', 'controls')}, indent=2))
    if errors or not all(c['rejected'] for c in controls):
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv[1])

"""Author post-outcome checker; reconstructs controller and native work separately."""
from pathlib import Path
from functools import lru_cache
import copy
import hashlib
import itertools
import json
import sys

KINDS = ('K_DIR', 'V_PARENT', 'V_LINK', 'V_UNLINK', 'V_NODE', 'V_CELL')
QUOTAS = {'none': 0, 'k_full': 1, 'v_full': 1, 'v_split': 1, 'k_split': 1,
          'v_two_split': 2, 'k_full_v_split': 2}
POLICIES = ('compiled', 'upstream', 'threshold', 'protected')


def check(row):
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    require(row['status'] == 'SUCCESS', 'native execution unsuccessful')
    require((row['n'], row['m'], row['r'], row['h']) == (31, 3, 16, 5), 'input shape mismatch')
    require(row['schedule'] in QUOTAS and row['policy'] in POLICIES, 'unknown cell')
    q, lam, policy = QUOTAS[row['schedule']], row['lambda'], row['policy']
    require(lam in (1, 3, 10) and q == row['q_bound'], 'input price or quota mismatch')
    require(row['id'] == f"{lam}_{row['schedule']}_{policy}", 'identity mismatch')
    caps = (4, 176)
    require(row['w_caps'] == list(caps), 'controller caps changed')

    @lru_cache(None)
    def value(j, b):
        if j == 2:
            return 0
        return min((1 + lam) * caps[j] + value(j + 1, b), fast_value(j, b))

    def fast_value(j, b):
        return caps[j] + (value(j + 1, b) if b == 0
                          else max(value(j + 1, b), value(j, b - 1)))

    require(row['model_value'] == value(0, 2 * q), 'model DP value mismatch')
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
    for idx, event in enumerate(row['events']):
        require(len(event) == 6, 'malformed event')
        stage, kind, a, b, c, d = event
        j = 0 if stage == 'K' else 1
        require(stage in ('K', 'V', 'W'), 'unknown stage')
        if kind == 'STAGE':
            require(active is None and pending is None, 'overlapping stage')
            stages.append(stage)
        elif kind == 'POLICY':
            require(policy != 'upstream' and (a, c, d) == (budget, failures[j], value(j, budget)),
                    'policy state/value mismatch')
            desired = (fast_value(j, budget) <= (1 + lam) * caps[j] + value(j + 1, budget)
                       if policy == 'compiled' else failures[j] < lam if policy == 'threshold' else False)
            require(b in (0, 1) and bool(b) == desired, 'incorrect policy choice')
        elif kind == 'DECISION':
            require(a == attempts[j] and b in (0, 1), 'attempt count mismatch')
            desired = (a < 2 if policy == 'upstream' else
                       fast_value(j, budget) <= (1 + lam) * caps[j] + value(j + 1, budget)
                       if policy == 'compiled' else failures[j] < lam if policy == 'threshold' else False)
            require(bool(b) == desired, 'decision differs from specified strategy')
            expected_body = 0 if b else 1
            decisions.append({'stage': stage, 'budget': budget, 'fast': bool(b)})
        elif kind in ('BEFORE_LOCK', 'DRAIN_FOR_LOCK'):
            require(active is None and pending is None, 'lock requested before prior body resolved')
            if kind == 'DRAIN_FOR_LOCK':
                require(cycle_open, 'drain without an open cycle')
        elif kind == 'BEGIN':
            require(active is None and pending is None and successes[j] == 0, 'overlapping or repeated job')
            require(stages and stages[-1] == stage, 'body in wrong stage')
            require(c in (0, 1) and c == expected_body, 'body mode differs from decision')
            require(b in (0, 1) and (not b or a % 2 == 0), 'invalid usePrev clock')
            require(clock is None or a == clock, 'unrecorded clock change before body')
            require(not c or not cycle_open, 'protected body while writer owns cycle')
            clock = a
            active = {'stage': stage, 'before': a, 'use_prev': b, 'protected': c,
                      'begin_index': idx, 'begin_epoch': completed_cycles, 'work': {k: 0 for k in KINDS}}
            if not c:
                attempts[j] += 1
            expected_body = None
        elif kind in KINDS:
            require(active is not None and active['stage'] == stage, 'work outside body')
            require(a > 0 and b == active['protected'], 'wrong charge or mode')
            require((stage == 'K') == kind.startswith('K_'), 'wrong work type for stage')
            active['work'][kind] += a
        elif kind == 'END':
            require(active is not None and active['stage'] == stage, 'unpaired END')
            require((a, b, c) == (active['before'], active['use_prev'], active['protected']), 'END metadata mismatch')
            require(d == 1, 'body did not return success; outside fixed normal domain')
            work = active['work']
            require(work['K_DIR'] <= 4 and work['V_PARENT'] <= 24 and work['V_LINK'] <= 28
                    and work['V_UNLINK'] <= work['V_LINK'] and work['V_NODE'] <= 32
                    and work['V_CELL'] <= 64, 'individual source cap violated')
            require(work['V_PARENT'] + work['V_LINK'] + work['V_UNLINK'] <= 80,
                    'directive work cap violated')
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
            require(d in (1, 3), 'non-normal CHECK flags')
            consistent = a // 2 == b // 2 and (a % 2 == b % 2 or not c)
            require(bool(d & 2) == consistent, 'native CHECK differs from recorded clock consistency')
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
    require(active is None and pending is None and stages == ['K', 'V'] and successes == [1, 1],
            'incomplete pipeline or repeated job')
    require(not cycle_open and cycles == completed_cycles == row['q_executed'] <= q, 'cycle ledger mismatch')
    require(epochs[0] == successful_v_epoch and 0 <= epochs[0] <= cycles, 'wrong source epoch for successful V body')
    actual_work = sum(x['selected_work'] for x in bodies)
    protected_work = sum(x['selected_work'] for x in bodies if x['protected'])
    charged_cap = sum(x['cap'] * (1 + lam * x['protected']) for x in bodies)
    cost = actual_work + lam * protected_work
    require(cost <= charged_cap, 'actual cost exceeds charged caps')
    if policy == 'compiled':
        require(charged_cap <= value(0, 2 * q), 'compiled execution exceeds model guarantee')
    return {'id': row['id'], 'policy': policy, 'schedule': row['schedule'], 'lambda': lam,
            'q_bound': q, 'cycles': cycles, 'failures': sum(failures), 'fast_attempts': sum(attempts),
            'protected_bodies': sum(x['protected'] for x in bodies), 'selected_work': actual_work,
            'protected_work': protected_work, 'weighted_cost': cost, 'charged_cap': charged_cap,
            'model_value': value(0, 2 * q), 'bodies': bodies, 'checks': checks, 'decisions': decisions}


def main(directory):
    directory = Path(directory)
    output = directory / 'check01'
    output.mkdir(exist_ok=False)
    rows = [json.loads(line) for line in (directory / 'RAW.jsonl').read_text().splitlines()]
    expected = {f'{lam}_{schedule}_{policy}' for lam, schedule, policy in
                itertools.product((1, 3, 10), QUOTAS, POLICIES)}
    assert len(rows) == len(expected) == 84 and {r['id'] for r in rows} == expected
    results, errors = [], []
    for row in rows:
        try:
            results.append(check(row))
        except Exception as error:
            errors.append({'id': row['id'], 'error': str(error)})
    controls = []
    if not errors:
        base = next(row for row in rows if row['id'] == '3_v_split_compiled')
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
              'denominator': 84, 'checked': len(results), 'errors': errors,
              'controls': controls, 'results': results}
    (output / 'TRACE_CHECK.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('denominator', 'checked', 'errors', 'controls')}, indent=2))
    if errors or not all(c['rejected'] for c in controls):
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv[1])

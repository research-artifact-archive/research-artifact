"""Post-outcome author trace checker, independent payload reconstruction.

This checks the six recorded schedules; it is not a universal source proof.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys

EXPECTED_Q = {'none': 0, 'k_before': 1, 'k_after': 1, 'v_before': 1, 'v_after': 1, 'both': 2}
KINDS = ('K_DIR', 'V_PARENT', 'V_LINK', 'V_UNLINK', 'V_NODE', 'V_CELL')


def check(row):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(row['id'] in EXPECTED_Q, 'unknown case')
    require(row['status'] == 'SUCCESS', 'execution did not succeed')
    n, m, r = row['n'], row['m'], row['r']
    require((n, m, r) == (31, 3, 16), 'fixed input shape mismatch')
    q = EXPECTED_Q[row['id']]
    require(row['q_executed'] == row['q_planned'] == q, 'cycle denominator mismatch')
    # Independently traverse the declared source tree; every explicit key expands all descendants.
    order = []
    stack = [0]
    while stack:
        node = stack.pop()
        if node < n:
            order.append(node)
            stack.extend([2 * node + 2, 2 * node + 1])
    require(len(row['rows']) == r, 'wrong row count')
    epoch = None
    for (node, parent, sentinel), expected in zip(row['rows'], order[:r]):
        require(node == expected, 'returned hierarchy order or identity mismatch')
        require(parent == (-2147483648 if node == 0 else (node - 1) // 2), 'parent mismatch')
        require((sentinel - node) % 1000 == 0, 'sentinel is not an actual version value')
        current = (sentinel - node) // 1000
        require(0 <= current <= q, 'unissued version')
        require(epoch is None or epoch == current, 'mixed source epochs')
        epoch = current

    stage_order, cycles, bodies, checks = [], [], [], []
    active = None
    completed_body = None
    # N-based loose caps avoid claiming an unverified tight height formula. These checks
    # hold for the observed bodies only; source proofs are a separate obligation.
    caps = {'K_DIR': m + 1, 'V_PARENT': (m + 1) * (n + 1),
            'V_LINK': (m + 1) * (n + 2), 'V_UNLINK': (m + 1) * (n + 2),
            'V_NODE': n + 1, 'V_CELL': 4 * r}
    for index, event in enumerate(row['events']):
        require(len(event) == 6, 'malformed event')
        stage, kind, a, b, c, d = event
        if kind == 'STAGE':
            require(active is None, 'stage entered during a body')
            stage_order.append(stage)
        elif kind == 'BEGIN':
            require(active is None, 'overlapping foreground bodies')
            require(stage_order and stage_order[-1] == stage, 'body outside current stage')
            active = {'stage': stage, 'before': a, 'previous': b, 'protected': c,
                      'begin': index, 'counts': {key: 0 for key in KINDS}}
        elif kind in KINDS:
            require(active is not None and active['stage'] == stage, 'work outside body')
            require(a > 0 and b == active['protected'], 'bad work charge or protected flag')
            require((stage == 'K') == kind.startswith('K_'), 'wrong stage work')
            active['counts'][kind] += a
        elif kind == 'END':
            require(active is not None and active['stage'] == stage, 'unpaired body end')
            require((a, b, c) == (active['before'], active['previous'], active['protected']),
                    'body metadata changed')
            require(d in (-1, 0, 1), 'unknown body return category')
            for key, count in active['counts'].items():
                require(count <= caps[key], 'observed body exceeds selected-operation cap: ' + key)
            active.update(end=index, returned=d)
            bodies.append(active)
            completed_body, active = active, None
        elif kind == 'CHECK':
            require(completed_body is not None and completed_body['stage'] == stage, 'check without body')
            require((a, c) == (completed_body['before'], completed_body['previous']), 'check metadata changed')
            require(d in (0, 1, 2, 3), 'unknown check flags')
            failed = not bool(d & 2)
            witnesses = [cycle for cycle in cycles if
                         completed_body['begin'] < cycle['index'] < index and cycle['before'] >= a and
                         cycle['after'] <= b]
            if failed:
                require(witnesses, 'inconsistency without a recorded actual intervening cycle')
                require(a // 2 != b // 2 or (c and a != b), 'clock does not explain whole-cycle failure')
            checks.append({'stage': stage, 'failed': failed, 'before': a, 'after': b,
                           'witness_cycles': [x['index'] for x in witnesses]})
            completed_body = None
        elif kind == 'CYCLE':
            require(stage == 'W' and b == a + 2, 'invalid whole update cycle clock change')
            require(c == d == b // 2, 'source/key notification steps do not match completed cycle')
            if cycles:
                require(a == cycles[-1]['after'], 'unrecorded clock changes')
            cycles.append({'index': index, 'before': a, 'after': b})
        else:
            require(False, 'unknown event kind')
    require(active is None and stage_order == ['K', 'V'], 'pipeline incomplete or K reran after V')
    require(len(cycles) == q, 'missing cycle events')
    require(len(checks) == len(bodies), 'first group expected all bodies to be concurrent and checked')
    failures = sum(x['failed'] for x in checks)
    require(failures <= 2 * q, 'conditional2q failure bound violated')
    require(all(any(x['stage'] == stage and not x['failed'] for x in checks) for stage in ('K', 'V')),
            'stage has no successful consistency check')
    return {'id': row['id'], 'status': 'SUCCESS', 'cycles': q, 'failures': failures,
            'epoch': epoch, 'bodies': bodies, 'checks': checks}


def main(directory):
    directory = Path(directory)
    rows = [json.loads(line) for line in (directory / 'RAW.jsonl').read_text().splitlines()]
    assert {row['id'] for row in rows} == set(EXPECTED_Q) and len(rows) == len(EXPECTED_Q)
    results = [check(row) for row in rows]
    base = next(row for row in rows if row['id'] == 'v_after')
    controls = []
    for mutation in ('mixed_epoch', 'deleted_update', 'excess_cells'):
        row = copy.deepcopy(base)
        if mutation == 'mixed_epoch':
            row['rows'][0][2] += 1000
        elif mutation == 'deleted_update':
            row['events'] = [event for event in row['events'] if event[1] != 'CYCLE']
        else:
            next(event for event in row['events'] if event[1] == 'V_CELL')[2] = 1000
        try:
            check(row)
            controls.append({'mutation': mutation, 'rejected': False})
        except ValueError as error:
            controls.append({'mutation': mutation, 'rejected': True, 'reason': str(error)})
        (directory / ('CONTROL_' + mutation + '.json')).write_text(json.dumps(row) + '\n')
    report = {'classification': 'post-outcome author checker; not pre-registered final evaluation',
              'source_bound_proved_by_this_checker': False,
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'results': results, 'controls': controls}
    assert all(control['rejected'] for control in controls)
    (directory / 'TRACE_CHECK.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'checked_cases': len(results), 'observed_failures': sum(x['failures'] for x in results),
                      'controls': controls}, indent=2))


if __name__ == '__main__':
    main(sys.argv[1])

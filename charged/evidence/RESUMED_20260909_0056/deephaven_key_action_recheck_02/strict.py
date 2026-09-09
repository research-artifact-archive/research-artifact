"""Additional fixed-harness synchronization and completed-body checks."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'deephaven_key_action_01/attempt01'
SOURCE = OLD / 'sources/check_trace.py'
spec = importlib.util.spec_from_file_location('retained_deephaven_key_checker', SOURCE)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def check(row):
    result = legacy.check(row)

    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    phase, stage = 'STAGE_K', None
    writer = None
    due = []
    active = pending = None
    clock = base_step = None
    completed, started = 0, 0
    opened = False
    attempts = {'K': 0, 'V': 0}
    key_epoch = value_epoch = None
    cuts = legacy.SCHEDULES[row['schedule']]
    issued = [False] * len(cuts)
    full_bodies = 0

    def make_due(kind, count, protected):
        if protected:
            return []
        return [(i, count) for i, cut in enumerate(cuts) if not issued[i]
                and cut[:3] == (stage, attempts[stage], kind) and count >= cut[3]]

    def consistent(before, current, previous):
        return before // 2 == current // 2 and (before % 2 == current % 2 or not previous)

    def successful(epoch):
        nonlocal key_epoch, value_epoch, phase
        if stage == 'K':
            key_epoch, phase = epoch, 'STAGE_V'
        else:
            value_epoch, phase = epoch, 'DONE'

    for index, event in enumerate(row['events']):
        require(type(event) is list and len(event) == 6, 'malformed event array')
        owner, kind, a, b, c, d = event
        require(type(owner) is str and type(kind) is str and all(type(x) is int for x in (a, b, c, d)),
                'event payload types')
        if writer is not None:
            state, action, origin, before = writer
            if state == 'WAIT_SKIP':
                require(owner == stage and kind == 'SKIP_CLOSED_CYCLE' and (a, b, c, d) == (origin, 0, 0, 0),
                        'writer skip differs from current cut')
                writer = None
            elif state == 'WAIT_START':
                require(owner == 'W' and kind == 'START', 'foreground continued while START request pending')
                require(not opened and a == before == clock and a % 2 == 1 and b == a + 1,
                        'START clock/phase')
                require(c == d == a // 2, 'START notification step')
                clock, opened, started, writer = b, True, started + 1, None
            elif state == 'WAIT_KEY':
                require(owner == 'W' and kind == 'KEY_UPDATE', 'foreground continued while refresh request pending')
                require(a == completed + 1 and (b, c, d) == (3, 4 if a % 2 else 3, 3), 'KEY_UPDATE epoch/actions')
                require((action == 'COMPLETE') == opened, 'KEY_UPDATE cycle phase')
                writer = ('WAIT_RETURN', action, origin, before)
            else:
                require(state == 'WAIT_RETURN' and owner == 'W' and kind == action,
                        'foreground continued after mutation before writer return')
                require(a == before == clock and c == d == b // 2, 'writer completion clock/notifications')
                if action == 'FULL':
                    require(not opened and a % 2 == 1 and b == a + 2, 'FULL phase')
                    started += 1
                else:
                    require(action == 'COMPLETE' and opened and a % 2 == 0 and b == a + 1, 'COMPLETE phase')
                completed, clock, opened, writer = completed + 1, b, False, None
            continue

        if due:
            cut_id, count = due.pop(0)
            require(owner == stage and kind == 'CUT' and (a, b, c, d) == (cut_id, attempts[stage], count, 0),
                    'eligible cut did not fire immediately at its hook')
            require(not issued[cut_id], 'repeated cut')
            issued[cut_id] = True
            action = cuts[cut_id][4]
            if action == 'COMPLETE' and not opened:
                writer = ('WAIT_SKIP', action, cut_id, clock)
            elif action == 'START':
                require(not opened, 'nested START request')
                writer = ('WAIT_START', action, cut_id, clock)
            else:
                require(action in ('FULL', 'COMPLETE') and (action == 'COMPLETE') == opened, 'refresh request phase')
                writer = ('WAIT_KEY', action, cut_id, clock)
            continue

        require(owner in ('K', 'V') and kind not in ('CUT', 'SKIP_CLOSED_CYCLE'), 'unrequested writer/cut event')
        if phase in ('STAGE_K', 'STAGE_V'):
            expected = phase[-1]
            require(owner == expected and kind == 'STAGE' and (a, b, c, d) == (0, 0, 0, 0), 'stage entry sequence')
            stage, phase = expected, 'POLICY'
            continue
        require(owner == stage, 'event belongs to another foreground stage')
        if phase == 'POLICY':
            require(kind == 'POLICY', 'missing/extra policy event')
            phase = 'DECISION'
        elif phase == 'DECISION':
            require(kind == 'DECISION' and a == attempts[stage] and b in (0, 1) and c == d == 0, 'decision sequence/payload')
            phase = 'BEGIN_FAST' if b else 'BEFORE_LOCK'
        elif phase == 'BEFORE_LOCK':
            require(kind == 'BEFORE_LOCK' and a == b == c == d == 0, 'missing protected lock entry')
            phase = 'DRAIN' if opened else 'BEGIN_PROTECTED'
        elif phase == 'DRAIN':
            require(kind == 'DRAIN_FOR_LOCK' and a == b == c == d == 0 and opened, 'missing/extra protected drain')
            writer = ('WAIT_KEY', 'COMPLETE', 'DRAIN', clock)
            phase = 'BEGIN_PROTECTED'
        elif phase in ('BEGIN_FAST', 'BEGIN_PROTECTED'):
            require(kind == 'BEGIN' and c == (phase == 'BEGIN_PROTECTED') and d == 0, 'body entry sequence/payload')
            require(b == int(opened) and opened == (a % 2 == 0), 'usePrev differs from frozen source choice')
            require(not c or not opened, 'protected body in Updating phase')
            if clock is None:
                require(not opened and completed == 0, 'initial body not Idle epoch0')
                clock, base_step = a, a // 2
            require(a == clock and a // 2 - b - base_step == completed, 'body epoch/clock mismatch')
            active = dict(before=a, use_prev=b, protected=c, epoch=completed,
                          work={k: 0 for k in legacy.KINDS}, exception=False)
            if not c:
                attempts[stage] += 1
            phase = 'BODY'
        elif phase in ('BODY', 'EXCEPTION_END'):
            if phase == 'EXCEPTION_END':
                require(kind == 'END', 'foreground work after inconsistency exception')
            if kind in legacy.KINDS:
                require(phase == 'BODY' and b == active['protected'] and c == d == 0 and a > 0,
                        'body work payload')
                active['work'][kind] += a
                due = make_due(kind, active['work'][kind], active['protected'])
            elif kind == 'INCONSISTENT_EXCEPTION':
                require(not active['protected'] and not active['exception'] and (a, b, c, d) == (1, 0, 0, 0),
                        'exception placement/payload')
                require(not consistent(active['before'], clock, active['use_prev']),
                        'exception justified only by a future writer')
                active['exception'], phase = True, 'EXCEPTION_END'
            else:
                require(kind == 'END' and (a, b, c) == (active['before'], active['use_prev'], active['protected']),
                        'body end sequence/payload')
                require(d == (-1 if active['exception'] else 1), 'body return differs from exception path')
                if d == 1:
                    if stage == 'K':
                        expected_work = dict(zip(legacy.KINDS, (4, 0, 0, 0, 0, 0)))
                    else:
                        require(key_epoch is not None, 'V started before successful captured K')
                        expected_work = dict(zip(legacy.KINDS, (0, 4, 4, 0, 17 if key_epoch % 2 else 32, 64)))
                    require(active['work'] == expected_work, 'normally returned body has missing/extra selected work')
                    full_bodies += 1
                due = make_due('END', 1, active['protected'])
                pending, active = active, None
                if c:
                    successful(pending['epoch'])
                    pending = None
                else:
                    phase = 'CHECK'
        elif phase == 'CHECK':
            require(kind == 'CHECK' and (a, b, c) == (pending['before'], clock, pending['use_prev']), 'fast check sequence')
            if d == 3:
                successful(pending['epoch'])
            else:
                require(d in (0, 1), 'illegal fast result flags')
                phase = 'POLICY'
            pending = None
        else:
            require(False, 'extra event after pipeline completion')
    require(phase == 'DONE' and active is None and pending is None and writer is None and not due, 'incomplete trace state')
    require(not opened and started == completed == row['q_executed'] and issued == row['issued_cuts'], 'writer/cut terminal state')
    require((key_epoch, value_epoch) == (row['captured_key_epoch'], row['captured_value_epoch']), 'capture epoch mismatch')
    result.update(strict_completed_body_count=full_bodies, strict_synchronization_checked=True,
                  strict_scope='fixed harness event order, body totals and captured epochs; not full Java WORK reachability')
    return result

"""Author-side mutation/structure checker. Only reference.py supplies the oracle."""
import collections
import copy
import json
import sys

from reference import SortingReference, top


class CheckFailure(AssertionError):
    def __init__(self, name, actual=None, expected=None):
        super().__init__(name)
        self.detail = dict(check=name, actual=actual, expected=expected)


def eq(actual, expected, name):
    if actual != expected:
        raise CheckFailure(name, actual, expected)


def require(value, name, details=None):
    if not value:
        raise CheckFailure(name, details, True)


def full(obj):
    # Every target array holds immutable int/bool entries; heaps are two such arrays.
    # Copy all six arrays, preserving the complete dict and counters, without a
    # Python recursive deepcopy visit for every immutable scalar in every query.
    return {key: [list(heap) for heap in value] if key == 'heaps'
            else list(value) if type(value) is list else copy.deepcopy(value)
            for key, value in obj.__dict__.items()}


class Checker:
    def __init__(self, Filter, target_file, raw):
        self.Filter = Filter
        self.target_file = target_file
        self.raw = raw
        self.counts = collections.Counter()
        self.context = {}
        self.operation_maxima = collections.defaultdict(int)

    def emit(self, row):
        self.raw.write(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n')
        self.counts['raw_rows'] += 1

    def state(self, f, r):
        n = len(r.future) + len(r.completed)
        eq(f.n, n, 'n')
        eq(f.k, r.k, 'k')
        eq(f.incurred, r.incurred, 'incurred')
        eq(f.viable(), r.viable(), 'viability')
        eq(f.total, r.ceiling(), 'maintained top sum vs sorted oracle')
        eq(f.sizes, [n - r.k, r.k], 'heap sizes')
        require(0 <= r.k <= len(r.completed), 'physical k')
        eq(f.values, [r.completed[i] if i in r.completed else r.future[i] for i in range(n)], 'values')
        eq(f.done, [i in r.completed for i in range(n)], 'done')
        for name in ('values', 'done', 'side', 'pos'):
            eq(len(getattr(f, name)), n, name + ' capacity')
        seen = []
        for side in (0, 1):
            arr, size = f.heaps[side], f.sizes[side]
            eq(len(arr), n, 'heap capacity')
            eq(arr[size:], [-1] * (n - size), 'inactive heap sentinels')
            for at in range(size):
                job = arr[at]
                require(type(job) is int and 0 <= job < n, 'active valid job', job)
                seen.append(job)
                eq((f.side[job], f.pos[job]), (side, at), 'reciprocal handle')
                if at:
                    parent = arr[(at - 1) // 2]
                    a, b = (f.values[parent], parent), (f.values[job], job)
                    require(a <= b if side else a >= b, 'heap ordering', [side, at, a, b])
        eq(sorted(seen), list(range(n)), 'exactly one active copy of each job')
        high = [f.values[i] for i in f.heaps[1][:f.sizes[1]]]
        low = [f.values[i] for i in f.heaps[0][:f.sizes[0]]]
        if high and low:
            require(min(high) >= max(low), 'top/rest boundary value ordering', [min(high), max(low)])
        eq(sum(high), f.total, 'top-heap sum')
        self.counts['structural_states'] += 1

    def construct(self, case, measured=False):
        r = SortingReference.from_case(case)
        future, completed = dict(r.future), dict(r.completed)
        before = copy.deepcopy((future, completed))
        call = lambda: self.Filter(future, completed, r.k, r.incurred)
        if measured:
            f, metrics = self.measure(call)
            metrics['comparisons'], metrics['swaps'] = f.comparisons, f.swaps
        else:
            f, metrics = call(), None
        eq((future, completed), before, 'constructor inputs unchanged')
        self.state(f, r)
        self.counts['constructors_valid'] += 1
        if metrics is not None:
            self.bounds(f, metrics, 'constructor', initial_k=r.k)
        return f, r, metrics

    def measure(self, call):
        counts = collections.Counter()
        def tracer(frame, event, arg):
            if frame.f_code.co_filename != self.target_file:
                return None
            if event == 'call':
                counts['calls:' + frame.f_code.co_name] += 1
            elif event == 'line':
                counts['line_events'] += 1
            return tracer
        require(sys.gettrace() is None, 'no preexisting trace')
        sys.settrace(tracer)
        try:
            value = call()
        finally:
            sys.settrace(None)
        return value, dict(counts)

    def bounds(self, f, m, kind, initial_k=None):
        n, L = f.n, max(1, f.n.bit_length())
        c, s = m['comparisons'], m['swaps']
        repairs = m.get('calls:_up', 0) + m.get('calls:_down', 0)
        eq(m.get('calls:_better', 0), c, 'traced comparisons match counter')
        eq(m.get('calls:_swap', 0), s, 'traced swaps match counter')
        if kind == 'query':
            eq((c, s, repairs, m.get('calls:_pop', 0), m.get('calls:_push', 0)),
               (0, 0, 0, 0, 0), 'constant query has no heap operations')
            limit = 96
        elif kind == 'complete':
            require(c <= 12 * L + 12, 'completion comparison bound', [c, L])
            require(s <= 8 * L + 8, 'completion swap bound', [s, L])
            require(repairs <= 7, 'completion repair bound', repairs)
            require(m.get('calls:_pop', 0) <= 3, 'completion pop bound', m)
            require(m.get('calls:_push', 0) <= 3, 'completion push bound', m)
            limit = 256 * L + 128
        else:
            k = initial_k
            require(c <= 2 * n + 3 * k * L, 'constructor comparison bound', [c, n, k, L])
            require(s <= n + 2 * k * L, 'constructor swap bound', [s, n, k, L])
            limit = 64 * n + 128 * k * L + 128
        require(m.get('line_events', 0) <= limit, kind + ' source-line bound', [m, limit])
        m['L'], m['line_event_limit'] = L, limit
        for key in ('comparisons', 'swaps', 'line_events'):
            self.operation_maxima[kind + ':' + key] = max(self.operation_maxima[kind + ':' + key], m.get(key, 0))
        self.operation_maxima[kind + ':repairs'] = max(self.operation_maxima[kind + ':repairs'], repairs)
        self.counts['operation_bound_checks_' + kind] += 1

    def query(self, f, r, job, body, measured=False):
        self.context.update(job=job, body=body, reference_state=r.state())
        before = full(f)
        def call():
            return f.limits(job, body), f.permissions(job, body)
        if measured:
            (limits, permissions), metrics = self.measure(call)
            metrics['comparisons'] = f.comparisons - before['comparisons']
            metrics['swaps'] = f.swaps - before['swaps']
            self.bounds(f, metrics, 'query')
        else:
            (limits, permissions), metrics = call(), None
        eq(full(f), before, 'queries leave entire object unchanged')
        expected = r.limits(job, body)
        eq(limits, expected, 'limits vs explicit sorted X')
        eq(permissions, r.permissions(job, body), 'permissions')
        eq(any(permissions.values()), r.viable(), 'mode availability iff viable')
        self.counts['query_pairs'] += 1
        return dict(job=job, body=body, limits=limits, permissions=permissions, operations=metrics)

    def transition(self, f, r, job, body, mode, mismatch, clone=True, measured=False):
        if clone:
            f, r = copy.deepcopy(f), copy.deepcopy(r)
        before = full(f)
        allowed = r.permissions(job, body)[mode]
        self.context.update(action=[job, body, mode, mismatch], reference_state=r.state(),
                            target_before=before)
        if not allowed:
            try:
                f.complete(job, body, mode, mismatch)
            except ValueError:
                pass
            else:
                raise CheckFailure('unsafe action accepted', [job, body, mode, mismatch], 'ValueError')
            eq(full(f), before, 'forbidden action does not mutate anything')
            self.counts['forbidden_actions_rejected'] += 1
            return f, r, dict(mode=mode, mismatch=mismatch, result='rejected-unchanged')
        if measured:
            _, metrics = self.measure(lambda: f.complete(job, body, mode, mismatch))
            metrics['comparisons'] = f.comparisons - before['comparisons']
            metrics['swaps'] = f.swaps - before['swaps']
            self.bounds(f, metrics, 'complete')
        else:
            f.complete(job, body, mode, mismatch)
            metrics = None
        r.complete(job, body, mode, mismatch)
        self.state(f, r)
        require(r.viable(), 'permitted successor remains viable')
        self.counts['permitted_actions_completed'] += 1
        self.counts['action_' + mode + '_' + str(mismatch)] += 1
        return f, r, dict(mode=mode, mismatch=mismatch, result='completed',
                          k=r.k, incurred=r.incurred, top=r.ceiling(), operations=metrics)

    def initial(self, case):
        f, r, _ = self.construct(case)
        self.counts['initial_viable' if r.viable() else 'initial_unsafe'] += 1
        row = dict(id=case['id'], state=r.state(), viable=r.viable(), top=r.ceiling(), queries=[])
        for job in sorted(r.future):
            for body in case['bodies']:
                q = self.query(f, r, job, body)
                q['actions'] = []
                row['queries'].append(q)
                self.context['partial_row'] = row
                for mode, outcome in [('fresh', None), ('cached', False), ('cached', True)]:
                    _, _, result = self.transition(f, r, job, body, mode, outcome)
                    q['actions'].append(result)
        self.emit(row)

    def policies(self, case):
        f, r, _ = self.construct(case)
        def visit(f, r, path):
            self.state(f, r)
            self.counts['policy_prefixes'] += 1
            self.context['path'] = path
            if not r.future:
                eq(f.total, top(list(r.completed.values()), r.k), 'terminal sorted completed benchmark')
                require(r.incurred <= top(list(r.completed.values()), r.k), 'terminal charged bound')
                self.counts['policy_leaves'] += 1
            self.emit(dict(id=case['id'], path=path, state=r.state(), top=r.ceiling(), terminal=not r.future))
            for job in sorted(r.future):
                body = case['bodies'][job]
                q = self.query(f, r, job, body)
                for mode, outcome in [('fresh', None), ('cached', False), ('cached', True)]:
                    if q['permissions'][mode]:
                        child, refchild, _ = self.transition(f, r, job, body, mode, outcome)
                        self.counts['policy_edges'] += 1
                        visit(child, refchild, path + [[job, mode, outcome]])
        visit(f, r, [])

    def named(self, case):
        self.initial(case)
        if case.get('replay'):
            f, r, _ = self.construct(case)
            for index, action in enumerate(case['replay']):
                if index == 2:
                    eq(r.state(), dict(future=[(2, 3)], completed=[(0, 2), (1, 2)], k=1, incurred=3),
                       'required reachable A state')
                    q = self.query(f, r, 2, 1)
                    eq(q['limits'], {'cached': 2, 'fresh': 3}, 'A exact limits')
                    eq(q['permissions'], {'cached': False, 'fresh': True}, 'A exact permissions')
                    for outcome in (False, True):
                        _, _, result = self.transition(f, r, 2, 1, 'cached', outcome)
                        self.emit(dict(id=case['id'], replay_index=index, diagnostic=result))
                self.query(f, r, action[0], action[1])
                f, r, result = self.transition(f, r, *action, clone=False)
                self.emit(dict(id=case['id'], replay_index=index, action=action, state=r.state(), result=result))
            eq((r.k, r.incurred, r.ceiling()), (1, 4, 4), 'A final state')

    def invalid(self, case):
        if case['kind'] == 'constructor':
            args = [dict(case['future']), dict(case['completed']), case['k'], case['incurred']]
            before = copy.deepcopy(args)
            try:
                self.Filter(*args)
            except ValueError:
                pass
            else:
                raise CheckFailure('invalid constructor accepted', case, 'ValueError')
            eq(args, before, 'rejected constructor input dictionaries unchanged')
            self.counts['invalid_constructors_rejected'] += 1
        else:
            f, r, _ = self.construct(case)
            before = full(f)
            self.context['target_before'] = before
            try:
                getattr(f, case['call'])(*case['args'])
            except ValueError:
                pass
            else:
                raise CheckFailure('invalid action accepted', case, 'ValueError')
            eq(full(f), before, 'invalid action leaves full object unchanged')
            self.state(f, r)
            self.counts['invalid_actions_rejected'] += 1
        self.emit(dict(id=case['id'], name=case['name'], result='ValueError-inputs-and-state-unchanged'))

    def streams(self, case):
        f, r, init_metrics = self.construct(case, measured=True)
        self.emit(dict(id=case['id'], phase='constructor', n=f.n, k=f.k, incurred=f.incurred,
                       top=f.total, persistent_array_slots=6*f.n, operations=init_metrics))
        for index, job in enumerate(case['order']):
            self.context['stream_index'] = index
            body = case['bodies'][job]
            q = self.query(f, r, job, body, measured=True)
            prefer = 'fresh' if case['profile'] == 'half_completed_fresh' or (
                case['profile'] == 'alternating' and index % 2) else 'cached'
            mode = prefer if q['permissions'][prefer] else ('cached' if prefer == 'fresh' else 'fresh')
            outcome = None if mode == 'fresh' else case['outcomes'][index]
            require(q['permissions'][mode], 'selected allowed stream mode')
            f, r, result = self.transition(f, r, job, body, mode, outcome, clone=False, measured=True)
            self.counts['stream_steps'] += 1
            self.emit(dict(id=case['id'], phase='step', index=index, query=q, completion=result))
        eq(len(r.future), 0, 'stream completes all remaining jobs')
        if case['profile'] == 'all_mismatch':
            eq(f.k, f.n, 'reachable terminal k=n after every cached mismatch')
        self.emit(dict(id=case['id'], phase='terminal', n=f.n, k=f.k, incurred=f.incurred, top=f.total))

    def execute(self, case):
        self.context = dict(case=case)
        self.counts['inputs_started'] += 1
        getattr(self, case['family'])(case)
        self.counts['inputs_completed'] += 1

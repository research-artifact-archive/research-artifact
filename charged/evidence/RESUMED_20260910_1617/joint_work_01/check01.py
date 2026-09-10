"""Exploratory exact finite check; protocol fixed before this implementation ran."""
from pathlib import Path
from functools import lru_cache
from itertools import product, permutations
from collections import Counter
import datetime, hashlib, json, time, traceback

D = Path(__file__).resolve().parent
START = time.monotonic()
DEADLINE = START + 600


def bounded():
    if time.monotonic() > DEADLINE:
        raise TimeoutError('600-second whole-attempt cap')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def top(w, b):
    return sum(sorted(w, reverse=True)[:b])


def insert(front, vector, witness):
    if any(all(x <= y for x, y in zip(v, vector)) for v in front):
        return
    for v in list(front):
        if all(x <= y for x, y in zip(vector, v)):
            del front[v]
    front[vector] = witness


class Oracle:
    def __init__(self, w, edges):
        self.w = tuple(w)
        self.n = len(w)
        self.pred = [0] * self.n
        self.edges = tuple(tuple(e) for e in edges)
        for i, j in edges:
            self.pred[j] |= 1 << i
        self.full = (1 << self.n) - 1
        self.known = lru_cache(None)(self._known)
        self.unaware = lru_cache(None)(self._unaware)

    def ready(self, s):
        return [i for i in range(self.n) if s & (1 << i) and not self.pred[i] & s]

    def _known(self, s, b):
        bounded()
        if not s:
            return {(0, 0): None}
        if b == 0:
            i = self.ready(s)[0]
            return {(0, 0): {'i': i, 'mode': 'cheap', 'next': self.known(s ^ (1 << i), 0)[(0, 0)]}}
        out = {}
        for i in self.ready(s):
            rem = s ^ (1 << i)
            wi = self.w[i]
            same = self.known(rem, b)
            spent = self.known(rem, b - 1)
            for (e, ell), tree in same.items():
                insert(out, (e, wi + ell), {'i': i, 'mode': 'fresh', 'next': tree})
            for (e0, l0), t0 in same.items():
                for (e1, l1), t1 in spent.items():
                    insert(out, (max(e0, wi + e1), max(l0, wi + l1)),
                           {'i': i, 'mode': 'cached', 'match': t0, 'mismatch': t1})
        return out

    def _unaware(self, s, d, ell):
        bounded()
        if ell > top(self.w, d):
            return {}
        if not s:
            return {(0,) * (self.n + 1): None}
        out = {}
        for i in self.ready(s):
            rem = s ^ (1 << i)
            wi = self.w[i]
            for curve, tree in self.unaware(rem, d, ell + wi).items():
                insert(out, curve, {'i': i, 'mode': 'fresh', 'next': tree})
            matches = self.unaware(rem, d, ell)
            mismatches = self.unaware(rem, d + 1, ell + wi)
            for c0, t0 in matches.items():
                for c1, t1 in mismatches.items():
                    curve = (c0[0],) + tuple(max(c0[b], wi + c1[b - 1]) for b in range(1, self.n + 1))
                    insert(out, curve, {'i': i, 'mode': 'cached', 'match': t0, 'mismatch': t1})
        return out


def trace_policy(tree, w, edges, budget):
    """Separate forward interpreter, with actual counted work and call costs."""
    leaves = []

    def walk(t, seen, d, work, protected, calls, path):
        if t is None:
            assert len(seen) == len(w), ('incomplete', seen)
            leaves.append({'writes': d, 'W': work, 'L': protected, 'Q': calls, 'path': path})
            return
        i, mode = t['i'], t['mode']
        assert i not in seen and all(a in seen for a, b in edges if b == i), ('not enabled', i, seen)
        nxt = seen | {i}
        if mode == 'fresh':
            walk(t['next'], nxt, d, work + w[i], protected + w[i], calls + 1, path + [[i, 'fresh']])
        elif mode == 'cheap':
            assert d == budget, ('unsafe cheap', d, budget)
            walk(t['next'], nxt, d, work + w[i], protected, calls + 1, path + [[i, 'cheap-match']])
        elif mode == 'cached':
            walk(t['match'], nxt, d, work + w[i], protected, calls + 1, path + [[i, 'cached-match']])
            if d < budget:
                walk(t['mismatch'], nxt, d + 1, work + 2 * w[i], protected + w[i], calls + 1, path + [[i, 'cached-mismatch']])
        else:
            raise AssertionError(('unknown mode', mode))

    walk(tree, set(), 0, 0, 0, 0, [])
    return leaves


def schedule_value(order, w, cap):
    cumulative = 0
    result = 0
    for i in order:
        if w[i] > cap:
            cumulative += w[i]
            tail = 0
        else:
            tail = w[i]
        result = max(result, cumulative + tail)
    return result


def lawler(w, edges, cap):
    remain, backward = set(range(len(w))), []
    while remain:
        sinks = [i for i in remain if not any(a == i and b in remain for a, b in edges)]
        i = min(sinks, key=lambda i: (w[i] if w[i] <= cap else 0, i))
        backward.append(i)
        remain.remove(i)
    return list(reversed(backward))


def order_policy(order, w, cap, consumed=False):
    if not order:
        return None
    i, rest = order[0], order[1:]
    if consumed:
        return {'i': i, 'mode': 'cheap', 'next': order_policy(rest, w, cap, True)}
    if w[i] > cap:
        return {'i': i, 'mode': 'fresh', 'next': order_policy(rest, w, cap)}
    return {'i': i, 'mode': 'cached', 'match': order_policy(rest, w, cap),
            'mismatch': order_policy(rest, w, cap, True)}


def ascending_policy(w, b):
    def build(order, remaining_writes):
        if not order:
            return None
        i, rest = order[0], order[1:]
        if remaining_writes == 0:
            return {'i': i, 'mode': 'cheap', 'next': build(rest, 0)}
        if len(order) <= remaining_writes:
            return {'i': i, 'mode': 'fresh', 'next': build(rest, remaining_writes)}
        return {'i': i, 'mode': 'cached', 'match': build(rest, remaining_writes),
                'mismatch': build(rest, remaining_writes - 1)}
    return build(sorted(range(len(w)), key=lambda i: (w[i], i)), b)


def formula_extra(w, b):
    return 0 if b >= len(w) else top(w, b + 1) - max(w)


def inputs():
    for n in range(1, 5):
        possible = [(i, j) for i in range(n) for j in range(i + 1, n)]
        for mask in range(1 << len(possible)):
            edges = [e for k, e in enumerate(possible) if mask & (1 << k)]
            for w in product((1, 2, 4), repeat=n):
                yield f'n{n}-g{mask}-w' + ''.join(map(str, w)), w, edges


COUNTS = {}
FILES = {}


def record(group, case_id, inp, action):
    counts = COUNTS.setdefault(group, Counter())
    out = FILES.get(group)
    if out is None:
        out = FILES[group] = (D / (group + '.jsonl')).open('x')
    row = {'case': case_id, 'input': inp}
    if time.monotonic() > DEADLINE:
        row.update(status='NOT_EXECUTED', reason='whole-attempt cap already expired')
    else:
        try:
            row['result'] = action()
            row['status'] = 'SUCCESS'
        except TimeoutError:
            row.update(status='TIMEOUT', error=traceback.format_exc())
        except AssertionError:
            row.update(status='FAILURE', error=traceback.format_exc())
        except Exception:
            row.update(status='INVALID', error=traceback.format_exc())
    counts[row['status']] += 1
    out.write(json.dumps(row, separators=(',', ':')) + '\n')
    out.flush()


def known_case(oracle, b):
    front = oracle.known(oracle.full, b)
    checked = []
    for (extra, ell), tree in sorted(front.items()):
        paths = trace_policy(tree, oracle.w, oracle.edges, b)
        actual = (max(t['W'] for t in paths) - sum(oracle.w), max(t['L'] for t in paths))
        assert actual == (extra, ell), (actual, extra, ell, paths)
        assert all(t['Q'] == oracle.n for t in paths)
        checked.append({'E': extra, 'L': ell, 'policy': tree, 'paths': paths})
    assert min(l for e, l in front) == top(oracle.w, b), (oracle.w, b, list(front))
    return {'frontier': checked, 'states': oracle.known.cache_info().currsize}


def cap_case(oracle, cap):
    w, edges = oracle.w, oracle.edges
    order = lawler(w, edges, cap)
    value = schedule_value(order, w, cap)
    brute = []
    for perm in permutations(range(len(w))):
        pos = {i: k for k, i in enumerate(perm)}
        if all(pos[a] < pos[b] for a, b in edges):
            brute.append((schedule_value(perm, w, cap), perm))
    optimal = min(v for v, p in brute)
    front = oracle.known(oracle.full, 1)
    feasible = [(e, l) for e, l in front if e <= cap]
    actual = min(l for e, l in feasible)
    tree = order_policy(order, w, cap)
    paths = trace_policy(tree, w, edges, 1)
    assert optimal == value == actual, (optimal, value, actual, order, list(front), brute)
    assert max(t['L'] for t in paths) == value, (value, paths)
    assert max(t['W'] for t in paths) <= sum(w) + cap, (cap, paths)
    assert all(t['Q'] == len(w) for t in paths)
    return {'L': value, 'order': order, 'brute_orders': len(brute), 'policy': tree, 'paths': paths}


def corollary_case(oracle):
    w, edges = oracle.w, oracle.edges
    maxima = [i for i, wi in enumerate(w) if wi == max(w)]
    unique_sink = len(maxima) == 1 and not any(a == maxima[0] for a, b in edges)
    expected = (sorted(w, reverse=True)[1] if len(w) > 1 else 0) if unique_sink else max(w)
    actual = min(e for e, ell in oracle.known(oracle.full, 1) if ell <= max(w))
    assert actual == expected, (w, edges, expected, actual)
    return {'E': actual, 'L': max(w), 'unique_maximum_sink': unique_sink}


def unaware_case(oracle):
    curves = oracle.unaware(oracle.full, 0, 0)
    expected = tuple(top(oracle.w, b) for b in range(oracle.n + 1))
    assert sorted(curves) == [expected], (expected, sorted(curves))
    tree = curves[expected]
    paths = trace_policy(tree, oracle.w, oracle.edges, oracle.n)
    for t in paths:
        assert t['L'] <= top(oracle.w, t['writes']) and t['Q'] == oracle.n, t
    observed = tuple(max(t['W'] - sum(oracle.w) for t in paths if t['writes'] <= b) for b in range(oracle.n + 1))
    assert observed == expected, (expected, observed, paths)
    return {'E_curve': expected, 'policy': tree, 'paths': paths, 'states': oracle.unaware.cache_info().currsize}


def independent_case(oracle, b):
    w = oracle.w
    front = oracle.known(oracle.full, b)
    cap = top(w, b)
    expected = formula_extra(w, b)
    actual = min(e for e, ell in front if ell <= cap)
    paths = trace_policy(ascending_policy(w, b), w, (), b)
    actual_policy = max(t['W'] for t in paths) - sum(w)
    assert actual == expected == actual_policy, (w, b, expected, actual, actual_policy, list(front), paths)
    assert max(t['L'] for t in paths) <= cap and all(t['Q'] == len(w) for t in paths), paths
    return {'E': actual, 'L_cap': cap, 'paths': paths}


def main():
    receipt = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'protocol_sha256': sha(D / 'FINITE_PROTOCOL01.md'), 'script_sha256': sha(Path(__file__)),
               'wall_cap_seconds': 600, 'canonical_finite_class_only': True}
    (D / 'ATTEMPT01_START.json').write_text(json.dumps(receipt, indent=2) + '\n')
    for index, (cid, w, edges) in enumerate(inputs(), 1):
        oracle = Oracle(w, edges)
        base = {'works': w, 'edges': edges}
        for b in range(len(w) + 1):
            record('known_frontiers01', cid + f'-B{b}', dict(base, B=b), lambda b=b: known_case(oracle, b))
        for cap in sorted({0, *w}):
            record('one_write_caps01', cid + f'-M{cap}', dict(base, M=cap), lambda cap=cap: cap_case(oracle, cap))
        record('one_write_corollary01', cid, base, lambda: corollary_case(oracle))
        if len(w) <= 3:
            record('unaware_curves01', cid, base, lambda: unaware_case(oracle))
        if index % 500 == 0:
            print(json.dumps({'graphs_done': index, 'counts': COUNTS, 'seconds': time.monotonic() - START}), flush=True)
    for n in range(1, 6):
        for w in product((1, 2, 4), repeat=n):
            oracle = Oracle(w, ())
            cid = 'w' + ''.join(map(str, w))
            for b in range(n + 1):
                record('independent01', cid + f'-B{b}', {'works': w, 'B': b}, lambda b=b: independent_case(oracle, b))
            record('saturation01', cid, {'works': w, 'B': n + 1}, lambda: independent_case(oracle, n + 1))
    fixtures = [('singleton', (1,), []), ('independent8_16', (8, 16), []),
                ('chain8_16', (8, 16), [(0, 1)]), ('chain16_8', (8, 16), [(1, 0)]),
                ('tied4_4_1', (4, 4, 1), [])]
    for cid, w, edges in fixtures:
        oracle = Oracle(w, edges)
        record('fixtures01', cid, {'works': w, 'edges': edges},
               lambda: {'known': known_case(oracle, 1), 'caps': [cap_case(oracle, m) for m in sorted({0, *w})],
                        'corollary': corollary_case(oracle), 'unaware': unaware_case(oracle)})
    expected_counts = {'known_frontiers01': 26844, 'one_write_caps01': 18390, 'one_write_corollary01': 5421,
                       'unaware_curves01': 237, 'independent01': 2004, 'saturation01': 363, 'fixtures01': 5}
    for out in FILES.values():
        out.close()
    receipt.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), counts=COUNTS,
                   planned_counts=expected_counts, seconds=time.monotonic() - START,
                   output_hashes={g + '.jsonl': sha(D / (g + '.jsonl')) for g in FILES})
    receipt['denominators_match'] = all(sum(COUNTS[g].values()) == n for g, n in expected_counts.items())
    receipt['status'] = 'SUCCESS' if receipt['denominators_match'] and all(set(c) == {'SUCCESS'} for c in COUNTS.values()) else 'NON_SUCCESS'
    (D / 'SUMMARY01.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()

"""Author-side all-budget verification of packed output.

Uses existing general curve arithmetic, NOT the run-packing implementation.
Reconstructs each fixed-order suffix by the proved one-job Bellman operator,
then checks the emitted threshold and root curve on every affine interval.
Trusts the mathematical operator and sorted-order optimality theorems plus
Python arithmetic and imported curve utilities. It is not an independent
theorem proof or a source-application conformance check. It reconstructs all
suffix profiles; naive curve utilities can take quadratic time per suffix,
despite linear packed output. The input is checked independently here.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'dependency_curves_01'))
import curves
import checker as ideal_checker


def packed_profile(runs):
    out = []; start = 0; value = 0; previous = None
    for height, count in runs:
        assert type(height) is int and height > 0
        assert type(count) is int and count > 0
        assert previous is None or previous > height
        out.append((start, value, height))
        start += count; value += height * count; previous = height
    out.append((start, value, 0))
    return out


def all_equal_on(f, g, lo, hi):
    """Equality on integer budgets lo<=b<hi; hi=None means an infinite tail."""
    points = {lo}
    if hi is not None:
        if lo >= hi: return 0
        points.add(hi - 1)
    for h in [f, g]:
        for x, _, _ in h:
            for b in (x - 1, x):
                if b >= lo and (hi is None or b < hi): points.add(b)
    for b in points: assert curves.at(f, b) == curves.at(g, b), (b, f, g)
    if hi is None: assert f[-1][2] == g[-1][2]
    return len(points)


def check(compiled):
    if compiled['route'] == 'ideal': return ideal_checker.check(compiled)
    case = compiled['input']; cp = case['cp']; order = compiled['order']; n = len(cp)
    assert sorted(order) == list(range(n))
    assert len(compiled['protect_at_budget']) == n
    assert all(type(c) is int and c > 0 and type(p) is int and p >= 0 for c, p in cp)
    rank = [None] * n
    for k, j in enumerate(order): rank[j] = k
    assert all(cp[a][0] <= cp[b][0] for a, b in zip(order, order[1:]))
    assert len({tuple(e) for e in case['edges']}) == len(case['edges'])
    for a, b in case['edges']:
        assert type(a) is int and type(b) is int and 0 <= a < n and 0 <= b < n
        assert rank[a] < rank[b] and cp[a][0] <= cp[b][0]
    f = curves.ZERO; checked_points = 0; peak = 1; suffix_segments = 0
    for k in range(n - 1, -1, -1):
        c, p = cp[order[k]]; threshold = compiled['protect_at_budget'][k]
        assert type(threshold) is int and threshold >= 0
        protected = curves.shift_value(f, p); fast = curves.floor_slopes(f, c)
        f = curves.lower(protected, fast)
        checked_points += all_equal_on(f, fast, 0, threshold)
        checked_points += all_equal_on(f, protected, threshold, None)
        peak = max(peak, len(f)); suffix_segments += len(f)
    supplied = packed_profile(compiled['value_slopes'])
    checked_points += all_equal_on(f, supplied, 0, None)
    assert compiled['normal_cost'] == sum(c for c, p in cp)
    return dict(violations=[], domain='ALL_NONNEGATIVE_INTEGER_BUDGETS',
                basis='sorted-topological corollary and general Bellman curve operator',
                checked_suffixes=n, checked_points=checked_points,
                peak_profile_segments=peak, suffix_segments=suffix_segments,
                independent_packing_reimplementation=False, independent_theorem_proof=False)

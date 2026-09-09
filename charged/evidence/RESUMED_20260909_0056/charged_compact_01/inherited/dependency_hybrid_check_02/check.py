"""All-budget root-cap certificate verification, without importing any solver.

Soundness uses the directly checked sorted-order Bellman identities; global
optimality additionally uses the sorted-topological corollary. See PROOF_DRAFT.
No packing, suffix-curve construction, or numerical-budget expansion is used.
Python assertions must be enabled; this is an author research implementation.
"""
from bisect import bisect_left


class Curve:
    def __init__(self, runs):
        self.lengths = []; self.areas = []; self.heights = []; length = area = 0
        for row in runs:
            assert isinstance(row, (list, tuple)) and len(row) == 2
            h, count = row
            assert type(h) is int and h > 0 and type(count) is int and count > 0
            assert not self.heights or self.heights[-1] > h
            length += count; area += h * count
            self.lengths.append(length); self.areas.append(area); self.heights.append(h)
        self.total = area

    def value(self, b):
        assert type(b) is int and b >= 0
        if b == 0: return 0
        i = bisect_left(self.lengths, b)
        if i == len(self.lengths): return self.total
        before_b = self.lengths[i - 1] if i else 0
        before_v = self.areas[i - 1] if i else 0
        return before_v + self.heights[i] * (b - before_b)

    def marginal(self, b):
        assert type(b) is int and b >= 1
        i = bisect_left(self.lengths, b)
        return 0 if i == len(self.lengths) else self.heights[i]

    def reaches(self, mass):
        assert type(mass) is int and 0 <= mass <= self.total
        if mass == 0: return 0
        i = bisect_left(self.areas, mass)
        before_b = self.lengths[i - 1] if i else 0
        before_v = self.areas[i - 1] if i else 0
        return before_b + (mass - before_v + self.heights[i] - 1) // self.heights[i]


def check(compiled):
    assert compiled['schema'] == 'dag-retry-ordered-cursor-v1'
    assert compiled['route'] == 'ordered' and compiled['completion_state'] == 'cursor'
    assert type(compiled['runtime_synthesis_calls']) is int and compiled['runtime_synthesis_calls'] == 0
    case = compiled['input']; cp = case['cp']; n = len(cp)
    for row in cp:
        assert isinstance(row, (list, tuple)) and len(row) == 2
        c, p = row
        assert type(c) is int and c > 0 and type(p) is int and p >= 0
    order = compiled['order']; assert len(order) == n; rank = [None] * n
    for k, j in enumerate(order):
        assert type(j) is int and 0 <= j < n and rank[j] is None
        rank[j] = k
        if k: assert cp[order[k - 1]][0] <= cp[j][0]
    seen = set()
    for edge in case['edges']:
        assert isinstance(edge, (list, tuple)) and len(edge) == 2
        a, b = edge
        assert type(a) is int and type(b) is int and 0 <= a < n and 0 <= b < n
        assert (a, b) not in seen and rank[a] < rank[b]
        seen.add((a, b))
    assert type(compiled['normal_cost']) is int and compiled['normal_cost'] == sum(c for c, p in cp)
    thresholds = compiled['protect_at_budget']; assert len(thresholds) == n
    assert all(type(t) is int and t >= 0 for t in thresholds)
    curve = Curve(compiled['value_slopes']); z = sum(p for c, p in cp)
    assert curve.total == z
    points = 0; positive = 0
    for k, j in enumerate(order):
        c, p = cp[j]; a = z - p
        if p == 0:
            assert thresholds[k] == 0
            continue
        u = curve.reaches(a); v = curve.reaches(z)
        assert 0 <= u <= v and v >= 1
        assert thresholds[k] == v
        if u >= 2:
            assert curve.marginal(u - 1) >= c, ('prefix', k)
            points += 1
        if u >= 1:
            assert min(curve.value(u), z) == min(z, max(a, c + curve.value(u - 1))), ('child_cap_boundary', k)
            points += 1
        lo = max(1, u + 1); hi = v - 1
        if lo <= hi:
            assert curve.marginal(lo) == c and curve.marginal(hi) == c, ('middle', k)
            points += 2
        assert z <= c + curve.value(v - 1), ('parent_cap_boundary', k)
        points += 1; positive += 1; z = a
    assert z == 0
    return dict(violations=[], domain='ALL_NONNEGATIVE_INTEGER_BUDGETS',
                checked_suffixes=n, positive_premium_suffixes=positive,
                local_boundary_checks=points, root_runs=len(curve.heights),
                canonical_protection_first_thresholds=True,
                basis='direct Bellman equations for root caps; sorted-topological corollary',
                solver_imports=False, independent_theorem_proof=False)

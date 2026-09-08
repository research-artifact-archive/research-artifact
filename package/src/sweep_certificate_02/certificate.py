"""Full integer Bellman certificate scan by affine lower bounds and zero coverage.

No constructor imports or cheapest-fast simplification. This checks a supplied
ideal-state certificate under the proved primitive-to-Bellman correspondence.
"""
if not __debug__:
    raise RuntimeError('assertions-enabled Python is required')
from pathlib import Path
import heapq
import importlib.util
import itertools

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'sweep_complete_shape', ROOT.parent / 'final_evaluation_dag_01/structure.py')
shape = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shape)


def zero(a, d, span):
    """Zero set of a+d*t on integers 0..span, represented as one interval."""
    if d == 0:
        return (0, span) if a == 0 else None
    numerator = -a
    if numerator % d:
        return None
    point = numerator // d
    return (point, point) if 0 <= point <= span else None


def nonpositive(a, d, span):
    """Closed integer interval where a+d*t<=0, or None."""
    if d == 0:
        return (0, span) if a <= 0 else None
    if d > 0:
        upper = min(span, (-a) // d)
        return (0, upper) if upper >= 0 else None
    lower = max(0, -((-a) // (-d)))
    return (lower, span) if lower <= span else None


def intersect(a, b):
    if a is None or b is None:
        return None
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo <= hi else None


def interval_identity(protected, fast, span, selected_fast=None):
    """Whether min(protected lines, fast two-line maxima)==0 for every integer.

    Returns a concrete offending offset and kind on failure. The caller has
    subtracted its supplied own-value line from every constituent action line.
    """
    assert type(span) is int and span >= 0 and (protected or fast)
    assert selected_fast is None or (type(selected_fast) is int and 0 <= selected_fast < len(fast))
    zeros = []
    for a, d in protected:
        if a < 0:
            return dict(ok=False, offset=0, kind='protected_below_value')
        if a+d*span < 0:
            return dict(ok=False, offset=span, kind='protected_below_value')
        z = zero(a, d, span)
        if z is not None:
            zeros.append(z)
    for fast_index, ((a, d), (b, e)) in enumerate(fast):
        points = {0, span}
        if d != e:
            numerator, denominator = b-a, d-e
            if denominator < 0:
                numerator, denominator = -numerator, -denominator
            floor = numerator // denominator
            ceil = -((-numerator) // denominator)
            points.update(t for t in [floor, ceil] if 0 <= t <= span)
        for t in points:
            if max(a+d*t, b+e*t) < 0:
                return dict(ok=False, offset=t, kind='fast_below_value')
        if selected_fast is not None and fast_index != selected_fast:
            continue
        both = intersect(nonpositive(a, d, span), nonpositive(b, e, span))
        for line in [(a, d), (b, e)]:
            z = intersect(both, zero(*line, span))
            if z is not None:
                zeros.append(z)
    through = -1
    for lo, hi in sorted(zeros):
        if lo > through+1:
            return dict(ok=False, offset=through+1, kind='no_action_attains_value')
        through = max(through, hi)
        if through >= span:
            return dict(ok=True, zero_intervals=len(zeros))
    return dict(ok=False, offset=through+1, kind='no_action_attains_value')


class Cursor:
    def __init__(self, profile, shift=0):
        self.profile = profile
        self.shift = shift
        self.index = 0

    def line(self, budget):
        x = budget-self.shift
        assert x >= 0
        while self.index+1 < len(self.profile) and self.profile[self.index+1][0] <= x:
            self.index += 1
        start, value, slope = self.profile[self.index]
        return value+(x-start)*slope, slope


def check(data):
    structure = shape.check(data)
    curves = data['curves']
    cp = data['input']['cp']
    intervals = actions = zero_intervals = 0
    for key, profile in curves.items():
        mask = int(key)
        if not mask:
            continue
        available = data['actions'][key]['available']
        children = [curves[str(mask ^ (1 << j))] for j in available]
        own, prior = Cursor(profile), Cursor(profile, shift=1)
        child_cursors = [Cursor(child) for child in children]
        starts = [[1]]
        starts += [[x for x, _, _ in profile if x >= 1], [x+1 for x, _, _ in profile]]
        starts += [[x for x, _, _ in child if x >= 1] for child in children]
        boundaries = [x for x, _ in itertools.groupby(heapq.merge(*starts))]
        for index, lo in enumerate(boundaries):
            hi = boundaries[index+1]-1 if index+1 < len(boundaries) else None
            v, slope = own.line(lo)
            previous, previous_slope = prior.line(lo)
            protected = []
            fast = []
            tail_slopes = [slope, previous_slope]
            for j, cursor in zip(available, child_cursors):
                child, child_slope = cursor.line(lo)
                tail_slopes.append(child_slope)
                protected.append((cp[j][1]+child-v, child_slope-slope))
                fast.append(((child-v, child_slope-slope),
                             (cp[j][0]+previous-v, previous_slope-slope)))
            if hi is None:
                assert all(x == 0 for x in tail_slopes), ('nonconstant tail', key)
            stored = available.index(data['actions'][key]['fast'])
            result = interval_identity(protected, fast, 0 if hi is None else hi-lo, stored)
            intervals += 1
            actions += 2*len(available)
            if not result['ok']:
                return dict(violations=[dict(mask=mask, budget=lo+result['offset'],
                     kind=result['kind'])], checked_states=structure['states'],
                     intervals=intervals, action_intervals=actions,
                     domain='ALL_NONNEGATIVE_INTEGER_BUDGETS_BY_ZERO_COVERAGE')
            zero_intervals += result['zero_intervals']
    return dict(violations=[], checked_states=structure['states'],
        intervals=intervals, action_intervals=actions, zero_intervals=zero_intervals,
        shape=structure, domain='ALL_NONNEGATIVE_INTEGER_BUDGETS_BY_ZERO_COVERAGE',
        full_ready_action_set=True, constructor_imports=False,
        directly_checked_stored_policy_attainment=True,
        independent_theorem_proof=False)

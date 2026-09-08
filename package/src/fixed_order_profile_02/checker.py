"""Independent structural and full Bellman check of persistent order artifacts.

No constructor imports. Expands one/two suffix profiles at a time. The total
number of visited suffix runs can be quadratic; this is not a logarithmic
certificate checker. Reuses the previously verified affine zero-set primitive.
"""
from pathlib import Path
import heapq
import importlib.util
import itertools

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('order_affine_checker', ROOT.parent/'sweep_certificate_02/certificate.py')
affine = importlib.util.module_from_spec(spec); spec.loader.exec_module(affine)


def structure(data):
    assert data['schema'] == 'retry-persistent-order-v1'
    assert data['route'] == 'persistent_order'
    cp = data['input']['cp']; n = len(cp); order = data['order']
    assert all(type(row) is list and len(row) == 2 and type(row[0]) is int
               and row[0] > 0 and type(row[1]) is int and row[1] >= 0 for row in cp)
    assert len(order) == n and all(type(x) is int for x in order)
    assert sorted(order) == list(range(n))
    positions = {job: k for k, job in enumerate(order)}
    seen = set(); predecessors = [set() for _ in cp]
    for edge in data['input']['edges']:
        assert type(edge) is list and len(edge) == 2
        a, b = edge
        assert type(a) is int and type(b) is int and 0 <= a < n and 0 <= b < n
        assert positions[a] < positions[b] and (a, b) not in seen
        seen.add((a, b)); predecessors[b].add(a)
    # In a topological order, uniqueness is equivalent to every consecutive
    # pair being an edge (a path between consecutive jobs cannot be longer).
    unique = all((a, b) in seen for a, b in zip(order, order[1:]))
    assert type(data['unique_topological_order']) is bool
    assert data['unique_topological_order'] == unique
    assert data['normal_cost'] == sum(c for c, _ in cp)
    nodes = data['nodes']; roots = data['roots']; thresholds = data['protect_at_budget']
    assert len(roots) == n+1 and len(thresholds) == n and roots[-1] == -1
    assert all(type(i) is int and -1 <= i < len(nodes) for i in roots)
    assert all(type(t) is int and t >= 0 for t in thresholds)
    for index, row in enumerate(nodes):
        assert type(row) is list and len(row) == 10 and all(type(v) is int for v in row)
        h, count, left, right, height, length, area, first, last, runs = row
        assert h > 0 and count > 0 and -1 <= left < index and -1 <= right < index
        a = None if left == -1 else nodes[left]; b = None if right == -1 else nodes[right]
        assert a is None or a[8] > h
        assert b is None or h > b[7]
        lh = 0 if a is None else a[4]; rh = 0 if b is None else b[4]
        assert abs(lh-rh) <= 1 and height == max(lh, rh)+1
        assert length == count+(0 if a is None else a[5])+(0 if b is None else b[5])
        assert area == h*count+(0 if a is None else a[6])+(0 if b is None else b[6])
        assert first == (h if a is None else a[7]) and last == (h if b is None else b[8])
        assert runs == 1+(0 if a is None else a[9])+(0 if b is None else b[9])
    reached = set(); todo = list(roots)
    while todo:
        index = todo.pop()
        if index == -1 or index in reached: continue
        reached.add(index); todo.extend(nodes[index][2:4])
    assert reached == set(range(len(nodes)))
    premium = 0
    for cursor in range(n-1, -1, -1):
        premium += cp[order[cursor]][1]
        root = roots[cursor]
        assert (0 if root == -1 else nodes[root][6]) == premium
        assert (0 if root == -1 else nodes[root][9]) <= 2*(n-cursor)
        assert (cp[order[cursor]][1] == 0) == (thresholds[cursor] == 0)
    return dict(nodes=len(nodes), jobs=n, unique_order=unique)


def profile(data, root):
    nodes = data['nodes']; stack = []; out = []; start = value = 0
    while root != -1 or stack:
        while root != -1:
            stack.append(root); root = nodes[root][2]
        root = stack.pop(); row = nodes[root]
        out.append((start, value, row[0])); start += row[1]; value += row[0]*row[1]
        root = row[3]
    out.append((start, value, 0))
    return out


def check(data):
    shape = structure(data); visited = intervals = 0
    child = [(0, 0, 0)]
    for cursor in range(len(data['order'])-1, -1, -1):
        own = profile(data, data['roots'][cursor]); visited += len(own)
        c, p = data['input']['cp'][data['order'][cursor]]
        threshold = data['protect_at_budget'][cursor]
        now = affine.Cursor(own); before = affine.Cursor(own, 1); after = affine.Cursor(child)
        streams = [[1]] + [[x for x, _, _ in own if x >= 1],
                          [x+1 for x, _, _ in own],
                          [x for x, _, _ in child if x >= 1]]
        if threshold >= 1: streams.append([threshold])
        boundaries = [x for x, _ in itertools.groupby(heapq.merge(*streams))]
        for k, lo in enumerate(boundaries):
            hi = boundaries[k+1]-1 if k+1 < len(boundaries) else None
            span = 0 if hi is None else hi-lo
            v, vs = now.line(lo); old, os = before.line(lo); f, fs = after.line(lo)
            if hi is None: assert vs == os == fs == 0
            protected = (p+f-v, fs-vs)
            fast = ((f-v, fs-vs), (c+old-v, os-vs))
            result = affine.interval_identity([protected], [fast], span)
            intervals += 1
            if not result['ok']:
                return dict(violations=[dict(cursor=cursor,budget=lo+result['offset'],kind=result['kind'])])
            if lo >= threshold:
                assert protected[0] == 0 and (span == 0 or protected[1] == 0), ('stored_protect_not_optimal', cursor,lo)
            else:
                assert protected[0] > 0 and protected[0]+span*protected[1] > 0, ('not_first_protect_threshold',cursor,lo)
                selected = affine.interval_identity([], [fast], span)
                assert selected['ok'], ('stored_fast_not_optimal',cursor,lo,selected)
        child = own
    return dict(violations=[], shape=shape, suffix_profile_entries=visited+1,
                affine_intervals=intervals, domain='ALL_NONNEGATIVE_INTEGER_BUDGETS',
                stored_thresholds_checked=True, constructor_imports=False,
                complexity='linear in streamed suffix profiles, worst-case quadratic in job count')

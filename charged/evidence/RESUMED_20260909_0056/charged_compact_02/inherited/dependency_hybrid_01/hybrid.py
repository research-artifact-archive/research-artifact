"""Cost-compatible DAG specialization; unchanged ideal-curve fallback.

The packed route is a cursor policy for its own executions, not a table for
arbitrary externally supplied completion sets. Input cp entries are (c,p).
Packing is adapted from quantitative_progress/adaptive_retry_control/compiler.py;
the new order is cost-sorted AND topological, including equal-cost ties.
"""
import heapq
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'dependency_curves_01'))
import curves


def order_if_compatible(case):
    cp = case['cp']; n = len(cp)
    if any(len(row) != 2 or type(row[0]) is not int or row[0] <= 0
           or type(row[1]) is not int or row[1] < 0 for row in cp):
        raise ValueError('expected integer c>0 and p>=0')
    children = [[] for _ in cp]; indegree = [0] * n; seen = set()
    compatible = True
    for edge in case['edges']:
        if len(edge) != 2 or any(type(v) is not int or not 0 <= v < n for v in edge):
            raise ValueError('malformed edge')
        a, b = edge
        if (a, b) in seen: raise ValueError('duplicate edge')
        seen.add((a, b)); children[a].append(b); indegree[b] += 1
        compatible &= cp[a][0] <= cp[b][0]
    ready = [(cp[i][0], i) for i in range(n) if not indegree[i]]
    heapq.heapify(ready); order = []
    while ready:
        _, i = heapq.heappop(ready); order.append(i)
        for j in children[i]:
            indegree[j] -= 1
            if not indegree[j]: heapq.heappush(ready, (cp[j][0], j))
    if len(order) != n: raise ValueError('cyclic input')
    if compatible:
        assert all(cp[a][0] <= cp[b][0] for a, b in zip(order, order[1:]))
        return order
    return None


def pack(case, order):
    thresholds = [0] * len(order); runs = []; length = 0

    def append(height, count):
        nonlocal length
        if not count: return
        assert height > 0 and count > 0
        if runs and runs[-1][0] == height: runs[-1][1] += count
        else:
            assert not runs or runs[-1][0] > height
            runs.append([height, count])
        length += count

    for k in range(len(order) - 1, -1, -1):
        c, p = case['cp'][order[k]]
        if p == 0: continue
        if runs and runs[-1][0] < c:
            r, count = runs.pop(); assert count == 1; length -= 1
            pay = min(p, c - r); append(r + pay, 1); p -= pay
            if p == 0: thresholds[k] = length; continue
        whole, rem = divmod(p, c); append(c, whole)
        if rem: append(rem, 1)
        thresholds[k] = length
    return dict(schema='dag-retry-ordered-cursor-v1', input=case,
                route='ordered', order=order, protect_at_budget=thresholds,
                value_slopes=runs, completion_state='cursor',
                normal_cost=sum(c for c, p in case['cp']), runtime_synthesis_calls=0)


def compile_case(case):
    order = order_if_compatible(case)
    if order is not None: return pack(case, order)
    result = curves.compile_case(case); result['route'] = 'ideal'
    return result


def value(compiled, budget):
    if type(budget) is not int or budget < 0: raise ValueError('budget')
    if compiled['route'] == 'ideal':
        return curves.at(compiled['curves'][compiled['full']], budget)
    total = 0
    for h, count in compiled['value_slopes']:
        used = min(budget, count); total += h * used; budget -= used
        if not budget: break
    return total


def choose(compiled, state, budget):
    """state is a cursor for ordered route, an unfinished mask for ideal route.

    Successful or protected execution advances the cursor; failed validation
    leaves it unchanged and consumes a budget unit. The executor must still
    enforce completed-parent readiness and the concrete attempt contract.
    """
    if type(budget) is not int or budget < 0: raise ValueError('budget')
    if compiled['route'] == 'ideal': return curves.choose(compiled, state, budget)
    if type(state) is not int or not 0 <= state < len(compiled['order']):
        raise ValueError('cursor')
    return compiled['order'][state], ('protected' if budget >= compiled['protect_at_budget'][state] else 'fast')


def load(data):
    if data['route'] == 'ideal':
        data['curves'] = {int(k): v for k, v in data['curves'].items()}
        data['actions'] = {int(k): v for k, v in data['actions'].items()}
    return data

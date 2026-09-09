"""Requested-value peak oracle for the charged three-mode recurrence.

Adapted from the retained zero-fee memoized peak oracle. No allocation bounds,
ordered-job rules or zero-fee packing shortcuts are used here.
"""
from functools import lru_cache


def solve_many(case, budgets):
    if not __debug__:
        raise RuntimeError('assertions must be enabled')
    jobs = case['jobs']
    n = len(jobs)
    full = (1 << n) - 1
    prices = []
    for w, p, g, v, r in jobs:
        assert w > 0 and min(p, g, v, r) >= 0
        m = min(v, g + r)
        delta = g + r - m
        prices.append((w + m, p + delta, delta, w + p))
    pred = [sum(1 << u for u, v in case['edges'] if v == i) for i in range(n)]
    memo = {}
    nodes = {}
    stats = dict(peak_probes=0, cache_hits=0, evaluated_nodes=0)

    @lru_cache(None)
    def available(mask):
        result = [i for i in range(n) if mask & (1 << i) and not pred[i] & mask]
        assert not mask or result, 'cyclic dependency graph'
        return result

    def name(mask, budget):
        return f'{mask}:{budget}'

    def value(mask, budget):
        key = name(mask, budget)
        if key in memo:
            stats['cache_hits'] += 1
            return memo[key]
        node = dict(mask=mask, budget=budget)
        if not mask or not budget:
            result = 0
            node.update(kind='zero', value=0)
        else:
            ready = available(mask)
            i = min(ready, key=lambda j: (prices[j][0], j))
            child = mask ^ (1 << i)
            cost = prices[i][0]
            upper = []
            for j in ready:
                c, premium, delta, inside = prices[j]
                successor = mask ^ (1 << j)
                same = value(successor, budget)
                previous = value(successor, budget - 1)
                upper.extend((premium + same, delta + max(same, inside + previous)))
            lo, hi = 0, budget + 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                stats['peak_probes'] += 1
                slope = value(child, mid) - value(child, mid - 1)
                if slope >= cost:
                    lo = mid
                else:
                    hi = mid
            peak = lo
            point = value(child, peak)
            if peak:
                value(child, peak - 1)
            if peak < budget:
                value(child, peak + 1)
            result = min(min(upper), point + cost * (budget - peak))
            node.update(kind='peak', value=result, job=i, peak=peak)
        nodes[key] = node
        memo[key] = result
        stats['evaluated_nodes'] += 1
        return result

    values = [value(full, b) for b in budgets]
    needed = set()
    todo = [name(full, b) for b in budgets]
    while todo:
        key = todo.pop()
        if key in needed:
            continue
        needed.add(key)
        node = nodes[key]
        if node['kind'] == 'zero':
            continue
        mask, b, i, peak = (node[k] for k in ('mask', 'budget', 'job', 'peak'))
        for j in available(mask):
            todo.extend((name(mask ^ (1 << j), b), name(mask ^ (1 << j), b - 1)))
        child = mask ^ (1 << i)
        todo.append(name(child, peak))
        if peak:
            todo.append(name(child, peak - 1))
        if peak < b:
            todo.append(name(child, peak + 1))
    artifact = dict(schema='charged-requested-values-certificate-v1', input=case,
                    budgets=budgets, values=values, nodes={key: nodes[key] for key in sorted(needed)})
    stats.update(memo_states=len(memo), certificate_nodes=len(needed), reachable_masks=available.cache_info().currsize)
    return dict(values=values, artifact=artifact, stats=stats)

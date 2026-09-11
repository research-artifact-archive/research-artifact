"""Independent exhaustive policy/leaf evaluator in actual charges only.

No Top operator, candidate quantities, normalization, existing filter or game DP.
Policy structure and every trace were fixed without cost evaluation.
"""

def evaluate(game, cat):
    costs = game['costs']
    n, k = cat['n'], game['k']
    assert len(costs) == n and 0 <= k <= cat['D'].bit_count()
    assert all(0 <= a <= b and 0 <= f <= b for a,f,b in costs)
    subsets = []
    for mask in range(1 << n):
        actual = sum(costs[i][2] if mask >> i & 1 else costs[i][0] for i in range(n))
        subsets.append([mask,mask.bit_count(),actual])
    curve = [max(row[2] for row in subsets if row[1] <= budget) for budget in range(n+3)]
    records, modes = [], {}
    for pid,policy in enumerate(cat['policies']):
        leaves = []
        for trace in policy['leaves']:
            actual = mismatches = 0
            for i,outcome in trace:
                if outcome == 'F':
                    actual += costs[i][1]
                elif outcome == 'M':
                    actual += costs[i][0]
                elif outcome == 'B':
                    actual += costs[i][2]
                    mismatches += 1
                else:
                    raise ValueError('unknown outcome')
            benchmark = curve[k+mismatches]
            leaves.append([actual,mismatches,benchmark,benchmark-actual])
        limit = min(row[3] for row in leaves)
        records.append([pid,limit,leaves])
        root = policy['root']
        if root[0] != 'T':
            key = f'{root[1]}:{root[0]}'
            modes[key] = max(modes.get(key,limit),limit)
    return dict(id=game['id'],benchmark_subsets=subsets,benchmark_curve=curve,
                policies=records,state_limit=max(row[1] for row in records),mode_limits=modes)

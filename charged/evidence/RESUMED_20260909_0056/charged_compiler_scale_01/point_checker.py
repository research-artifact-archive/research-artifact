"""Independent charged point-certificate checker; imports no solver/compiler."""


def check(artifact):
    if not __debug__:
        raise RuntimeError('assertions must be enabled')
    assert type(artifact) is dict and set(artifact) == {'schema', 'input', 'budgets', 'values', 'nodes'}
    assert artifact['schema'] == 'charged-requested-values-certificate-v1'
    case = artifact['input']
    assert type(case) is dict and set(case) == {'jobs', 'edges'}
    jobs, edges = case['jobs'], case['edges']
    assert type(jobs) is list and jobs
    n = len(jobs)
    assert all(type(row) is list and len(row) == 5 and all(type(x) is int and x >= 0 for x in row)
               and row[0] > 0 for row in jobs)
    assert type(edges) is list
    pred = [set() for _ in jobs]
    seen_edges = set()
    for edge in edges:
        assert type(edge) is list and len(edge) == 2
        u, v = edge
        assert type(u) is int and type(v) is int and 0 <= u < n and 0 <= v < n and u != v
        assert (u, v) not in seen_edges
        seen_edges.add((u, v))
        pred[v].add(u)
    done = set()
    while len(done) < n:
        ready = {i for i in range(n) if i not in done and pred[i] <= done}
        assert ready, 'cycle'
        done.update(ready)
    prices = []
    for w, p, g, v, r in jobs:
        cheapest_call = min(v, g + r)
        extra_callback = g + r - cheapest_call
        prices.append((w + cheapest_call, p + extra_callback, extra_callback, w + p))
    budgets = artifact['budgets']
    assert type(budgets) is list and budgets and all(type(b) is int and b >= 0 for b in budgets)
    assert type(artifact['values']) is list and len(artifact['values']) == len(budgets)
    assert all(type(value) is int and value >= 0 for value in artifact['values'])
    limit = max(budgets)
    full = (1 << n) - 1
    nodes = artifact['nodes']
    assert type(nodes) is dict
    visited = {}
    counts = dict(zero=0, peak=0)

    def get(mask, b):
        key = f'{mask}:{b}'
        if key in visited:
            return visited[key]
        assert key in nodes, ('missing node', key)
        node = nodes[key]
        assert type(node) is dict and type(node['mask']) is int and node['mask'] == mask
        assert type(node['budget']) is int and node['budget'] == b
        assert 0 <= mask <= full and 0 <= b <= limit
        unfinished = {i for i in range(n) if mask & (1 << i)}
        completed = set(range(n)) - unfinished
        assert all(pred[i] <= completed for i in completed), 'not a reachable unfinished set'
        actual = node['value']
        assert type(actual) is int and actual >= 0
        allowed = {'mask', 'budget', 'kind', 'value'}
        kind = node['kind']
        if kind == 'zero':
            assert not mask or not b
            expected = 0
        elif kind == 'peak':
            allowed |= {'job', 'peak'}
            assert mask and b
            ready = [i for i in sorted(unfinished) if pred[i] <= completed]
            i, k = node['job'], node['peak']
            assert type(i) is int and i == min(ready, key=lambda j: (prices[j][0], j))
            assert type(k) is int and 0 <= k <= b
            child = mask ^ (1 << i)
            c = prices[i][0]
            point = get(child, k)
            if k:
                assert point - get(child, k - 1) >= c, ('left peak inequality', key)
            if k < b:
                assert get(child, k + 1) - point <= c, ('right peak inequality', key)
            alternatives = []
            for j in ready:
                cost, premium, delta, inside = prices[j]
                successor = mask ^ (1 << j)
                same = get(successor, b)
                previous = get(successor, b - 1)
                alternatives.append(premium + same)
                alternatives.append(delta + max(same, inside + previous))
            expected = min(min(alternatives), point + c * (b - k))
        else:
            raise AssertionError(('unknown proof node', kind))
        assert set(node) == allowed and actual == expected, (key, actual, expected)
        visited[key] = actual
        counts[kind] += 1
        return actual

    values = [get(full, b) for b in budgets]
    assert values == artifact['values']
    assert set(visited) == set(nodes), 'extraneous certificate nodes'
    return dict(values=values, nodes=len(visited), kinds=counts,
                certificate_scope='REQUESTED_ROOT_VALUES',
                relies_on='charged concavity, cheapest-fast reduction and reflected-recurrence cap theorem',
                compiler_or_solver_imported=False)

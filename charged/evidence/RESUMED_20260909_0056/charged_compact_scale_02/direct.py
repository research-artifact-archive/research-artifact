"""Budget-row recurrence with elementary equality pruning; shares bounds helper only."""
import bounds


def solve_many(case, budgets):
    jobs, edges = case['jobs'], case['edges']
    n = len(jobs)
    full = (1 << n) - 1
    elementary, threshold_for = bounds.prepare(jobs)
    threshold = threshold_for(full)
    root_bounds = {b: elementary(full, b) for b in budgets}
    answers = {b: low for b, (low, high) in root_bounds.items() if low == high}
    preanswered = len(answers)
    remaining = [b for b in budgets if b not in answers]
    # Validate DAG without enumerating its unfinished subsets, including all-saturated queries.
    pred=[0]*n;children=[[] for _ in jobs];indegree=[0]*n
    for u,v in edges:
        pred[v]|=1<<u;children[u].append(v);indegree[v]+=1
    ready=[i for i in range(n) if not indegree[i]];visited=0
    while ready:
        u=ready.pop();visited+=1
        for v in children[u]:
            indegree[v]-=1
            if not indegree[v]:ready.append(v)
    assert visited==n,'cyclic dependency graph'
    if not remaining:
        return dict(values=[answers[b] for b in budgets],
                    stats=dict(states=0, rows=0, cells=0, fixed_point_reached=False,
                               bounds_preanswered=preanswered, root_saturation_threshold=threshold),
                    certificate_scope='VALUES_ONLY_NO_INDEPENDENT_CERTIFICATE')
    available = {}
    pending = [full]
    states = {full}
    while pending:
        mask = pending.pop()
        ready = [i for i in range(n) if mask & (1 << i)
                 and not pred[i] & mask]
        assert not mask or ready
        available[mask] = ready
        for i in ready:
            child = mask ^ (1 << i)
            if child not in states:
                states.add(child)
                pending.append(child)
    order = sorted(states - {0})
    previous = {mask: 0 for mask in states}
    requested = set(remaining)
    if 0 in requested:
        answers[0] = 0
    b = 0
    saturated = False
    cells = 0
    equality_cells = 0
    while b < max(remaining):
        b += 1
        current = {0: 0}
        for mask in order:
            low, high = elementary(mask, b)
            if low == high:
                current[mask] = low
                cells += 1
                equality_cells += 1
                continue
            choices = []
            for i in available[mask]:
                w, p, g, v, r = jobs[i]
                m = min(v, g + r)
                delta = g + r - m
                child = mask ^ (1 << i)
                same = current[child]
                choices.append(p + delta + same)
                choices.append(max(same, w + m + previous[mask]))
                choices.append(delta + max(same, w + p + previous[child]))
            current[mask] = min(choices)
            cells += 1
        if b in requested:
            answers[b] = current[full]
        if current == previous:
            saturated = True
            for query in budgets:
                if query > b:
                    if query not in answers:
                        answers[query] = current[full]
            break
        previous = current
    return dict(values=[answers[b] for b in budgets],
                stats=dict(states=len(states), rows=b, cells=cells, equality_cells=equality_cells, fixed_point_reached=saturated,
                           bounds_preanswered=preanswered, root_saturation_threshold=threshold),
                certificate_scope='VALUES_ONLY_NO_INDEPENDENT_CERTIFICATE')



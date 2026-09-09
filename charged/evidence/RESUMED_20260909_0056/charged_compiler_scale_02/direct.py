"""Budget-row Bellman solver, independent of the curve/peak implementations."""


def solve_many(case, budgets):
    jobs, edges = case['jobs'], case['edges']
    n = len(jobs)
    full = (1 << n) - 1
    total = sum(p + g + r - min(v, g + r) for w, p, g, v, r in jobs)
    minimum = min(w + min(v, g + r) for w, p, g, v, r in jobs)
    threshold = 0 if total == 0 else n - 1 + (total + minimum - 1) // minimum
    answers = {b: total for b in budgets if b >= threshold}
    preanswered = len(answers)
    remaining = [b for b in budgets if b not in answers]
    # Validate DAG without enumerating its unfinished subsets, including all-saturated queries.
    done = set()
    while len(done) < n:
        ready = {i for i in range(n) if i not in done and all(u in done for u, v in edges if v == i)}
        assert ready
        done.update(ready)
    if not remaining:
        return dict(values=[answers[b] for b in budgets],
                    stats=dict(states=0, rows=0, cells=0, fixed_point_reached=False,
                               saturation_preanswered=preanswered, root_saturation_threshold=threshold),
                    certificate_scope='VALUES_ONLY_NO_INDEPENDENT_CERTIFICATE')
    available = {}
    pending = [full]
    states = {full}
    while pending:
        mask = pending.pop()
        ready = [i for i in range(n) if mask & (1 << i)
                 and not any(v == i and mask & (1 << u) for u, v in edges)]
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
    while b < max(remaining):
        b += 1
        current = {0: 0}
        for mask in order:
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
                stats=dict(states=len(states), rows=b, cells=cells, fixed_point_reached=saturated,
                           saturation_preanswered=preanswered, root_saturation_threshold=threshold),
                certificate_scope='VALUES_ONLY_NO_INDEPENDENT_CERTIFICATE')


"""Explicit three-mode AND-OR graph for the retained generic solver backend."""
from collections import defaultdict
from pathlib import Path
import importlib.util

SOURCE = Path(__file__).resolve().parent.parent / 'charged_guaranteed_02/explore.py'


def solve_many(case, budgets):
    spec = importlib.util.spec_from_file_location('charged_generic_retained_backend', SOURCE)
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    n = len(case['jobs'])
    full = (1 << n) - 1
    roots = [(full, budget) for budget in budgets]
    states = set(roots)
    pending = list(roots)
    actions, owners = [], []
    outgoing, backward = defaultdict(list), defaultdict(list)
    goals = set()
    while pending:
        mask, b = pending.pop()
        state = (mask, b)
        if not mask:
            goals.add(state)
            continue
        ready = [i for i in range(n) if mask & (1 << i)
                 and not any(v == i and mask & (1 << u) for u, v in case['edges'])]
        assert ready
        for i in ready:
            w, p, g, v, r = case['jobs'][i]
            m = min(v, g + r)
            delta = g + r - m
            child = mask ^ (1 << i)
            alternatives = [('protected', [((child, b), p + delta)]),
                            ('cheap', [((child, b), 0)] + ([((mask, b - 1), w + m)] if b else [])),
                            ('cached', [((child, b), delta)] + ([((child, b - 1), delta + w + p)] if b else []))]
            for mode, branches in alternatives:
                index = len(actions)
                actions.append(dict(job=i, mode=mode, edges=branches))
                owners.append(state)
                outgoing[state].append(index)
                for target, cost in branches:
                    backward[target].append((index, cost))
                    if target not in states:
                        states.add(target)
                        pending.append(target)
    values, policy, rank = backend.solve_validate((states, roots, actions, owners, outgoing, backward, goals))
    return dict(values=[values[root] for root in roots],
                stats=dict(states=len(states), actions=len(actions), edges=sum(len(a['edges']) for a in actions),
                           maximum_selected_rank=rank),
                certificate_scope='GENERIC_BELLMAN_AND_SELECTED_POLICY_TERMINATION_CHECKED')

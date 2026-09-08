"""Independent B=1 order/mode certificate scan; no solver/compiler imports."""
from functools import lru_cache


def validate_case(case):
    cp = case['cp']; n = len(cp)
    assert all(len(x) == 2 and type(x[0]) is int and x[0] > 0
               and type(x[1]) is int and x[1] >= 0 for x in cp)
    edges = case['edges']
    assert all(len(e) == 2 and all(type(x) is int and 0 <= x < n for x in e)
               and e[0] != e[1] for e in edges)
    assert len({tuple(e) for e in edges}) == len(edges)
    pred = [set(u for u, v in edges if v == i) for i in range(n)]
    done = set(); order = []
    while len(done) < n:
        ready = [i for i in range(n) if i not in done and pred[i] <= done]
        assert ready, 'cyclic graph'
        i = min(ready); done.add(i); order.append(i)
    return pred, order


def scan(case, certificate):
    pred, _ = validate_case(case)
    assert len(certificate) == len(case['cp'])
    done = set(); paid = 0; worst = 0; failures = []
    for i, mode in certificate:
        assert type(i) is int and 0 <= i < len(pred) and i not in done
        assert pred[i] <= done, (i, done, pred[i])
        c, p = case['cp'][i]
        if mode == 'P': paid += p
        elif mode == 'F':
            worst = max(worst, paid + c)
            failures.append([i, paid + c])
        else: raise AssertionError(mode)
        done.add(i)
    return dict(value=max(worst, paid), no_failure=paid, failure_costs=failures)


def subset_dp(case):
    """Independent exhaustive B=1 recurrence, all ready jobs and both modes."""
    pred, _ = validate_case(case); cp = case['cp']; n = len(cp)
    masks = [sum(1 << j for j in ps) for ps in pred]; choices = {}
    @lru_cache(None)
    def value(mask):
        if not mask: return 0
        candidates = []
        for i, (c, p) in enumerate(cp):
            if mask >> i & 1 and not masks[i] & mask:
                child = value(mask ^ (1 << i))
                candidates.extend([(child + p, i, 'P'), (max(c, child), i, 'F')])
        choice = min(candidates); choices[mask] = choice
        return choice[0]
    mask = (1 << n) - 1; answer = value(mask); certificate = []
    while mask:
        _, i, mode = choices[mask]; certificate.append([i, mode]); mask ^= 1 << i
    assert scan(case, certificate)['value'] == answer
    return answer, certificate, value.cache_info().currsize

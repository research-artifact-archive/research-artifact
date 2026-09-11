"""Candidate formulas only; called after the independent game's raw is flushed."""

def top(k, values):
    return sum(sorted(values,reverse=True)[:k])

def compare(game,cat,raw):
    n,k,D = cat['n'],game['k'],cat['D']
    done = [i for i in range(n) if D >> i & 1]
    future = [i for i in range(n) if not D >> i & 1]
    a,f,b = [list(x) for x in zip(*game['costs'])] if n else ([],[],[])
    q = [b[i]-a[i] for i in range(n)]
    p = [f[i]-a[i] for i in range(n)]
    d = [max(a[i]-f[i],0) for i in range(n)]
    t = [b[i]-max(a[i],f[i]) for i in range(n)]
    base = sum(a[i] for i in done)
    state = base + sum(d[i] for i in future) + top(k,[q[i] for i in done]+[t[i] for i in future])
    failures = []
    for budget,got in enumerate(raw['benchmark_curve']):
        expected = sum(a)+top(budget,q)
        if got != expected:
            failures.append(['benchmark',budget,got,expected])
    if raw['state_limit'] != state:
        failures.append(['state',raw['state_limit'],state])
    modes = {}
    for i in cat['ready']:
        others = [j for j in future if j != i]
        x = [q[j] for j in done]+[t[j] for j in others]
        r = base+sum(d[j] for j in others)
        modes[f'{i}:C'] = r+top(k,x)
        modes[f'{i}:F'] = r+top(k,x+[q[i]])-p[i]
        if max(raw['mode_limits'][f'{i}:C'],raw['mode_limits'][f'{i}:F']) != raw['state_limit']:
            failures.append(['per_ready_attainment',i])
    if set(modes) != set(raw['mode_limits']):
        failures.append(['mode_keys'])
    for key,expected in modes.items():
        if raw['mode_limits'].get(key) != expected:
            failures.append(['mode',key,raw['mode_limits'].get(key),expected])
    probes = {0}
    for limit in [state,*modes.values(),raw['state_limit'],*raw['mode_limits'].values()]:
        probes.update(max(0,limit+delta) for delta in (-1,0,1))
    negative_ell_probes = 0
    for actual_prefix in sorted(probes):
        negative_ell_probes += actual_prefix-base < 0
        if (actual_prefix <= state) != (actual_prefix <= raw['state_limit']):
            failures.append(['viability_probe',actual_prefix])
        for key in modes:
            if (actual_prefix <= modes[key]) != (actual_prefix <= raw['mode_limits'][key]):
                failures.append(['mode_probe',actual_prefix,key])
    return dict(id=game['id'],candidate_state_limit=state,candidate_mode_limits=modes,
                actual_prefix_probes=sorted(probes),negative_ell_probes=negative_ell_probes,
                failures=failures)

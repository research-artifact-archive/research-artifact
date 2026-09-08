"""Exact optional-interval formulation of the B=1 certificate objective."""
import json, time
from ortools.sat.python import cp_model
import certificate


def extract(case, starts, protected):
    """Move zero-length jobs inside intervals to their left endpoint."""
    _, topo = certificate.validate_case(case)
    rank = {i: k for k, i in enumerate(topo)}
    cp = case['cp']; n = len(cp)
    intervals = sorted((starts[i], starts[i] + cp[i][1], i)
                       for i in range(n) if protected[i] and cp[i][1] > 0)
    assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))
    normalized = starts[:]
    for i in range(n):
        if not protected[i] or cp[i][1] == 0:
            for start, end, _ in intervals:
                if start < starts[i] < end:
                    normalized[i] = start; break
    order = sorted(range(n), key=lambda i: (normalized[i],
                   int(bool(protected[i] and cp[i][1] > 0)), rank[i]))
    return [[i, 'P' if protected[i] else 'F'] for i in order]


def solve(case, seconds=5.0):
    start = time.perf_counter()
    certificate.validate_case(case)
    cp = case['cp']; n = len(cp); P = sum(p for c, p in cp)
    model = cp_model.CpModel()
    h = [model.new_bool_var(f'h{i}') for i in range(n)]
    t = [model.new_int_var(0, P, f't{i}') for i in range(n)]
    e = [model.new_int_var(0, P, f'e{i}') for i in range(n)]
    K = model.new_int_var(0, P, 'K'); intervals = []
    for i, (c, p) in enumerate(cp):
        model.add(e[i] == t[i] + p * h[i])
        if p:
            intervals.append(model.new_optional_interval_var(t[i], p, e[i], h[i], f'I{i}'))
        else: model.add(h[i] == 1)
        model.add(t[i] + c <= K).only_enforce_if(h[i].Not())
    model.add_no_overlap(intervals)
    for u, v in case['edges']: model.add(e[u] <= t[v])
    model.add(K >= sum(p * h[i] for i, (c, p) in enumerate(cp)))
    model.minimize(K)
    build_seconds = time.perf_counter() - start
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 20260908
    before = time.perf_counter(); status = solver.solve(model)
    solve_seconds = time.perf_counter() - before
    row = dict(status='INVALID', solver_status=solver.status_name(status),
               build_seconds=build_seconds, solve_seconds=solve_seconds,
               lower_bound=solver.best_objective_bound,
               solver_wall_seconds=solver.wall_time,
               conflicts=solver.num_conflicts, branches=solver.num_branches,
               solver_stats=solver.response_stats(), solution_info=solver.solution_info())
    before = time.perf_counter()
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        starts = [solver.value(x) for x in t]
        protected = [solver.value(x) for x in h]
        order_modes = extract(case, starts, protected)
        report = certificate.scan(case, order_modes)
        model_value = solver.value(K)
        assert report['value'] <= model_value, (report, model_value)
        if status == cp_model.OPTIMAL: assert report['value'] == model_value
        row.update(status='SUCCESS' if status == cp_model.OPTIMAL else 'TIMEOUT',
                   model_value=model_value, value=report['value'],
                   certificate=order_modes, certificate_report=report,
                   starts=starts, protected=protected)
    elif status == cp_model.UNKNOWN: row['status'] = 'TIMEOUT'
    elif status == cp_model.INFEASIBLE:
        row.update(status='FAILURE', reason='all-protected order is feasible')
    row['extract_check_seconds'] = time.perf_counter() - before
    before = time.perf_counter()
    encoded = json.dumps(row, sort_keys=True, separators=(',', ':')).encode()
    row['serialization_seconds'] = time.perf_counter() - before
    row['serialized_bytes'] = len(encoded)
    row['total_seconds'] = time.perf_counter() - start
    return row

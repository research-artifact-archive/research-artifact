from pathlib import Path
from collections import defaultdict
import datetime, hashlib, heapq, itertools, json, random, sys, time

ROOT = Path(__file__).resolve().parent
HARD_STOP = datetime.datetime(2026, 9, 8, 1, tzinfo=datetime.timezone.utc).timestamp()
U, C, L, LC, D = range(5)


def write(name, value):
    with (ROOT / name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def prepare():
    rng = random.Random(202609072025)
    cases, seen = [], set()
    while len(cases) < 384:
        jobs = tuple((rng.randint(1, 20), rng.randint(0, 10)) for _ in range(rng.randint(2, 4)))
        if jobs in seen:
            continue
        seen.add(jobs)
        cases.append(dict(id=f'fractional-{len(cases):04d}', jobs=jobs, budget=6,
                          provenance='author-generated-exploration', previously_observed=False))
    write('INPUTS.json', cases)
    write('MANIFEST.json', {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                           for name in ['PLAN.md', 'explore.py', 'INPUTS.json']})


def graph(jobs, B):
    states = [(s, b) for b in range(B+1) for s in itertools.product(range(5), repeat=len(jobs))]
    actions, owners, outgoing, backwards = [], [], {}, defaultdict(list)
    goals = set()
    for state in states:
        s, b = state
        outgoing[state] = []
        if all(x == D for x in s):
            goals.add(state)
            continue
        held = sum(jobs[i][1] for i, x in enumerate(s) if x in (L, LC))

        def add(i, name, base, success, failures=()):
            targets = [(success, b)] + [(f, b-1) for f in failures if b > 0]
            edges = []
            for target, budget in targets:
                ns = list(s)
                ns[i] = target
                edges.append(((tuple(ns), budget), base * (10+held)))
            aid = len(actions)
            actions.append(dict(job=i, name=name, edges=edges))
            owners.append(state)
            outgoing[state].append(aid)
            for target, cost in edges:
                backwards[target].append((aid, cost))

        for i, x in enumerate(s):
            w, alpha = jobs[i]
            if x == U:
                add(i, 'prepare', w, C)
                add(i, 'acquire', 1, L, [U])
            elif x == C:
                add(i, 'cas', 1, D, [C, U])
                add(i, 'conditional_acquire', 1, LC, [C, U])
                add(i, 'discard', 0, U)
            elif x == L:
                add(i, 'prepare_locked', w, LC)
                add(i, 'release', 1, U)
            elif x == LC:
                add(i, 'commit_locked', 1, D)
                add(i, 'release_cached', 1, C)
                add(i, 'discard_locked', 0, L)
    return states, actions, owners, outgoing, backwards, goals


def solve(g):
    states, actions, owners, outgoing, backwards, goals = g
    remaining = [len(a['edges']) for a in actions]
    acc = [0] * len(actions)
    values, policy = {}, {}
    heap = [(0, goal, -1) for goal in goals]
    heapq.heapify(heap)
    while heap:
        value, state, via = heapq.heappop(heap)
        if state in values:
            continue
        values[state] = value
        policy[state] = via
        for aid, cost in backwards[state]:
            remaining[aid] -= 1
            acc[aid] = max(acc[aid], value+cost)
            if remaining[aid] == 0:
                heapq.heappush(heap, (acc[aid], owners[aid], aid))
    return values, policy


def validate(g, values, policy):
    states, actions, owners, outgoing, backwards, goals = g
    assert len(values) == len(states), 'expected all states winning'
    for state in states:
        if state in goals:
            assert values[state] == 0
            continue
        qs = [max(cost + values[target] for target, cost in actions[aid]['edges'])
              for aid in outgoing[state]]
        assert values[state] == min(qs), ('Bellman defect', state, values[state], qs)
        aid = policy[state]
        assert aid in outgoing[state]
        assert values[state] == max(cost + values[target] for target, cost in actions[aid]['edges'])
    # Separate forward-rank definition for the selected finite controller.
    ranked = set(goals)
    rounds = 0
    while len(ranked) < len(states):
        added = {state for state in states if state not in ranked and
                 all(target in ranked for target, cost in actions[policy[state]]['edges'])}
        assert added, 'selected policy can fail to terminate'
        ranked.update(added)
        rounds += 1
    return rounds


def h17(jobs, B):
    n = len(jobs)
    vals = [[0]*(1 << n) for _ in range(B+1)]
    for b in range(1, B+1):
        for mask in range(1, 1 << n):
            candidates = []
            for i, (w, alpha) in enumerate(jobs):
                if mask & (1 << i):
                    rest = mask ^ (1 << i)
                    candidates.append(max(vals[b][rest], 10*(w+1)+vals[b-1][mask]))
                    p = 10+alpha*(w+1)
                    candidates.append(max(p+vals[b][rest], 10+vals[b-1][mask]))
            vals[b][mask] = min(candidates)
    baseline = sum(10*(w+1) for w, alpha in jobs)
    return [baseline+row[-1] for row in vals]


def run():
    for name, h in json.loads((ROOT/'MANIFEST.json').read_text()).items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == h
    cases = json.loads((ROOT/'INPUTS.json').read_text())
    start = time.monotonic()
    write('RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                  timeout_seconds=30, hard_stop_utc='2026-09-08T01:00:00Z'))
    counts = dict(SUCCESS=0, FAILURE=0, TIMEOUT=0, INVALID=0)
    gaps = comparisons = total_states = total_actions = 0
    with (ROOT/'RAW.jsonl').open('x') as f:
        for case in cases:
            row = dict(input=case)
            if time.monotonic()-start >= 30 or time.time() >= HARD_STOP:
                row['status'] = 'TIMEOUT'
            else:
                try:
                    g = graph(case['jobs'], case['budget'])
                    values, policy = solve(g)
                    rounds = validate(g, values, policy)
                    roots = [((U,)*len(case['jobs']), b) for b in range(case['budget']+1)]
                    actual = [values[s] for s in roots]
                    expected = h17(case['jobs'], case['budget'])
                    differences = [dict(b=b, primitive=x, h17=y) for b, (x, y) in enumerate(zip(actual, expected)) if x != y]
                    row.update(status='SUCCESS', primitive=actual, h17=expected, differences=differences,
                               root_actions=[g[1][policy[s]]['name']+':'+str(g[1][policy[s]]['job']) for s in roots],
                               states=len(g[0]), actions=len(g[1]), policy_rank_rounds=rounds)
                    if differences:
                        row['all_states'] = [dict(state=s, value=values[s], action=policy[s]) for s in g[0]]
                        row['all_actions'] = g[1]
                    gaps += bool(differences)
                    comparisons += len(roots)
                    total_states += len(g[0])
                    total_actions += len(g[1])
                except Exception as e:
                    row.update(status='INVALID', error=repr(e))
            counts[row['status']] += 1
            f.write(json.dumps(row, separators=(',', ':'))+'\n')
            f.flush()
    summary = dict(planned=len(cases), recorded=sum(counts.values()), outcomes=counts,
                   gap_inputs=gaps, root_comparisons=comparisons, validated_states=total_states,
                   actions=total_actions, elapsed_seconds=time.monotonic()-start,
                   raw_sha256=hashlib.sha256((ROOT/'RAW.jsonl').read_bytes()).hexdigest(),
                   normal_form_proved=False, application_established=False, novelty_established=False)
    write('SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()

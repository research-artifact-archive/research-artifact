import copy
import datetime
import hashlib
import itertools
import json
import pathlib
import platform
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PREVIOUS = ROOT.parent / 'dependency_hybrid_01'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data):
    with path.open('x') as f: json.dump(data, f, sort_keys=True, separators=(',', ':')); f.write('\n')


def partitions(n, limit=None):
    if n == 0:
        yield []
        return
    for h in range(min(n, limit if limit is not None else n), 0, -1):
        for tail in partitions(n - h, h): yield [h] + tail


def payload(cp, slopes):
    # A candidate certificate, not a call to any compiler or checker.
    runs = []
    for h in slopes:
        if runs and runs[-1][0] == h: runs[-1][1] += 1
        else: runs.append([h, 1])
    sums = [0]
    for h in slopes: sums.append(sums[-1] + h)
    thresholds = []; z = sum(p for c, p in cp)
    for c, p in cp:
        thresholds.append(next(b for b, total in enumerate(sums) if total >= z) if p else 0)
        z -= p
    return dict(schema='dag-retry-ordered-cursor-v1', route='ordered', completion_state='cursor',
                input=dict(id='candidate', cp=cp, edges=[]), order=list(range(len(cp))),
                protect_at_budget=thresholds, value_slopes=runs,
                normal_cost=sum(c for c, p in cp), runtime_synthesis_calls=0)


def main():
    routes = json.loads((PREVIOUS / 'SMALL_ROUTES.json').read_text())
    small = [dict(id=id, path=str(PREVIOUS / 'small_controllers' / f'{id}.json')) for id, route in routes.items() if route == 'ordered']
    assert len(small) == 221
    scale = json.loads((PREVIOUS / 'SCALE_UNITS.json').read_text())
    for unit in scale: unit['path'] = str(PREVIOUS / 'units' / unit['id'] / 'compile/controller.json')
    save(ROOT / 'SMALL_UNITS.json', small); save(ROOT / 'SCALE_UNITS.json', scale)
    count = 0; vectors = 0
    with (ROOT / 'CANDIDATES.jsonl').open('x') as f:
        for n in [1, 2, 3]:
            for costs in itertools.combinations_with_replacement([1, 2, 3], n):
                for premiums in itertools.product([0, 1, 2, 3], repeat=n):
                    vectors += 1; cp = [list(pair) for pair in zip(costs, premiums)]
                    for index, slopes in enumerate(partitions(sum(premiums))):
                        row = dict(id=f'vector{vectors:04d}_partition{index:02d}', vector_id=vectors, certificate=payload(cp, slopes))
                        f.write(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n'); count += 1
    base = payload([[1, 1]], [1]); fixtures = []
    def mutation(id, change, source=base):
        artifact = copy.deepcopy(source); change(artifact); fixtures.append(dict(id=id, certificate=artifact, expected='REJECT'))
    mutation('threshold_below', lambda a: a.update(protect_at_budget=[0]))
    mutation('threshold_above', lambda a: a.update(protect_at_budget=[2]))
    mutation('zero_premium_nonzero_threshold', lambda a: a.update(protect_at_budget=[1]), payload([[1, 0]], []))
    mutation('topology_reverse', lambda a: a['input'].update(edges=[[1, 0]]), payload([[1, 1], [1, 1]], [1, 1]))
    mutation('cost_order', lambda a: a['input'].update(cp=[[2, 1], [1, 1]]), payload([[1, 1], [2, 1]], [2]))
    mutation('duplicate_edge', lambda a: a['input'].update(edges=[[0, 1], [0, 1]]), payload([[1, 1], [1, 1]], [1, 1]))
    mutation('malformed_edge', lambda a: a['input'].update(edges=[[0, 2]]))
    mutation('root_mass', lambda a: a.update(value_slopes=[[1, 2]]))
    mutation('nonconcave', lambda a: a.update(value_slopes=[[1, 1], [2, 1]]), payload([[1, 3]], [1, 1, 1]))
    mutation('zero_slope', lambda a: a.update(value_slopes=[[0, 1], [1, 1]]))
    mutation('negative_count', lambda a: a.update(value_slopes=[[1, -1]]))
    mutation('wrong_normal_cost', lambda a: a.update(normal_cost=2))
    mutation('schema', lambda a: a.update(schema='unknown'))
    mutation('route', lambda a: a.update(route='ideal'))
    mutation('cursor_field', lambda a: a.update(completion_state='mask'))
    mutation('runtime_synthesis_field', lambda a: a.update(runtime_synthesis_calls=1))
    save(ROOT / 'MALFORMED.json', fixtures)
    files = [ROOT / name for name in ['PLAN.md', 'PROOF_DRAFT.md', 'check.py', 'prepare.py', 'semantic.py',
                'worker.py', 'run_scale.py', 'SMALL_UNITS.json', 'SCALE_UNITS.json', 'CANDIDATES.jsonl', 'MALFORMED.json']]
    files += [pathlib.Path(u['path']) for u in small + scale]
    files += [PREVIOUS / name for name in ['MANIFEST.json', 'SMALL_RAW.jsonl', 'SCALE_RAW.jsonl', 'hybrid.py', 'check.py']]
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    files=[dict(path=str(p), sha256=sha(p)) for p in files],
                    known_ordered_small=len(small), unchanged_ideal_small=len(routes) - len(small),
                    scale_units=len(scale), exhaustive_vectors=vectors, exhaustive_candidates=count,
                    malformed_units=len(fixtures), semantic_cap_seconds=300,
                    scale_unit_cap_seconds=10, scale_total_cap_seconds=900,
                    rss_cap_bytes=1073741824, rss_poll_seconds=.05,
                    session_deadline_utc='2026-09-08T00:50:00+00:00', python=sys.executable,
                    python_version=sys.version, platform=platform.platform(),
                    final_evaluation=False, repeated_compilation=False, retries=False, exclusions=[])
    save(ROOT / 'MANIFEST.json', manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, indent=2))


if __name__ == '__main__': main()

"""Materialize every unit before compiler/value/timing observations."""
import datetime
import hashlib
import itertools
import json
import pathlib
import platform
import random
import sys
import hybrid

ROOT = pathlib.Path(__file__).resolve().parent
SESSION = ROOT.parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data):
    with path.open('x') as f: json.dump(data, f, sort_keys=True, separators=(',', ':')); f.write('\n')


def main():
    small = json.loads((SESSION / 'dependency_retry_01/INPUTS.json').read_text())
    assert len(small) == 643
    groups = {case['id']: 'known_small_regression' for case in small}
    for k, permutation in enumerate(itertools.permutations(range(4))):
        for v, premiums in enumerate([[0, 0, 0, 0], [9, 0, 3, 1], [1, 2, 9, 0]]):
            cp = [None] * 4
            for i, j in enumerate(permutation): cp[j] = [3, premiums[i]]
            small.append(dict(id=f'equal_chain_perm{k:02d}_p{v}', cp=cp,
                              edges=[[permutation[i], permutation[i + 1]] for i in range(3)]))
    small.extend([dict(id='empty', cp=[], edges=[]), dict(id='single_zero', cp=[[7, 0]], edges=[]),
                  dict(id='single_positive', cp=[[7, 23]], edges=[]),
                  dict(id='equal_fork', cp=[[5, 1], [5, 10], [5, 0], [5, 30]], edges=[[3, 0], [3, 1], [0, 2], [1, 2]])])
    for case in small: groups.setdefault(case['id'], 'fresh_semantic_fixture')
    malformed = [dict(id='cycle', cp=[[1, 0], [1, 0]], edges=[[0, 1], [1, 0]]),
                 dict(id='self_loop', cp=[[1, 0]], edges=[[0, 0]]),
                 dict(id='duplicate', cp=[[1, 0], [2, 0]], edges=[[0, 1], [0, 1]]),
                 dict(id='out_of_range', cp=[[1, 0]], edges=[[0, 1]]),
                 dict(id='zero_cost', cp=[[0, 1]], edges=[]),
                 dict(id='negative_premium', cp=[[1, -1]], edges=[])]
    save(ROOT / 'SMALL_INPUTS.json', small); save(ROOT / 'MALFORMED_INPUTS.json', malformed)
    save(ROOT / 'SMALL_GROUPS.json', groups)
    save(ROOT / 'SMALL_ROUTES.json', {c['id']: ('ordered' if hybrid.order_if_compatible(c) is not None else 'ideal') for c in small})
    scale = []; (ROOT / 'inputs').mkdir()
    seed = 202609080141
    for family_index, family in enumerate(['independent', 'chain', 'layered8', 'sparse3']):
        for n in [64, 512, 4096, 32768]:
            rng = random.Random(seed + family_index * 100000 + n)
            permutation = list(range(n)); rng.shuffle(permutation)
            if family == 'independent': edges = []
            elif family == 'chain': edges = [[i, i + 1] for i in range(n - 1)]
            elif family == 'layered8': edges = [[i, j] for j in range(8, n) for i in range((j // 8 - 1) * 8, j // 8 * 8)]
            else: edges = [[i, j] for j in range(1, n) for i in sorted(rng.sample(range(max(0, j - 64), j), min(j, 3))) ]
            remapped = [[permutation[a], permutation[b]] for a, b in edges]
            for prices in ['SMALL', 'WIDE_C', 'WIDE_P']:
                price_rng = random.Random(seed + family_index * 100000 + n)
                cp = [None] * n
                for i, j in enumerate(permutation):
                    c = (1 << 40) + i * 127 if prices == 'WIDE_C' else 1 + i // max(1, n // 16)
                    p = price_rng.randrange(1, 257)
                    if prices == 'WIDE_C': p = c * (1 + i % 3) + price_rng.randrange(c)
                    elif prices == 'WIDE_P': p = p * (1 << 50) + i % 251
                    if i % 13 == 0: p = 0
                    cp[j] = [c, p]
                case = dict(id=f'{family}_{n}_{prices}', cp=cp, edges=remapped, family=family, prices=prices)
                assert hybrid.order_if_compatible(case) is not None
                save(ROOT / 'inputs' / f"{case['id']}.json", case)
                scale.append(dict(id=case['id'], group='fresh_structurally_compatible_scale', n=n, edges=len(remapped), prices=prices))
    old_cases = json.loads((SESSION / 'dependency_scale_01/INPUTS.json').read_text())
    historical = []
    for case in old_cases:
        changed = hybrid.order_if_compatible(case) is not None
        historical.append(dict(id=case['id'], changed_route=changed,
                               disposition='new_packing_measurement' if changed else 'unchanged_old_fallback_receipts_only'))
        if changed:
            save(ROOT / 'inputs' / f"{case['id']}.json", case)
            scale.append(dict(id=case['id'], group='known_scale_changed_path', n=len(case['cp']), edges=len(case['edges']), prices=case['prices']))
    save(ROOT / 'SCALE_UNITS.json', scale); save(ROOT / 'OLD_SCALE_DISPOSITIONS.json', historical)
    files = [ROOT / p for p in ['PLAN.md', 'hybrid.py', 'check.py', 'prepare.py', 'small.py', 'worker.py', 'run_scale.py',
                                'SMALL_INPUTS.json', 'MALFORMED_INPUTS.json', 'SMALL_GROUPS.json', 'SMALL_ROUTES.json',
                                'SCALE_UNITS.json', 'OLD_SCALE_DISPOSITIONS.json']]
    files += sorted((ROOT / 'inputs').glob('*.json'))
    sources = [SESSION / p for p in ['dependency_retry_01/RAW.jsonl', 'dependency_curves_01/curves.py',
                'dependency_curves_01/checker.py', 'dependency_curves_01/RAW.jsonl', 'dependency_scale_01/RAW.jsonl',
                'dependency_scale_01/MANIFEST.json']]
    sources += sorted((SESSION / 'dependency_curves_01/controllers').glob('*.json'))
    sources += [SESSION.parent / 'quantitative_progress/adaptive_retry_control/compiler.py']
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), seed=seed,
                    files=[dict(path=str(p), sha256=sha(p)) for p in files + sources],
                    small_valid_cases=len(small), known_small=643, small_invalid_cases=len(malformed),
                    small_budgets=list(range(13)), small_case_cap_seconds=3, small_total_cap_seconds=300,
                    scale_cases=len(scale), scale_units=2 * len(scale), scale_unit_cap_seconds=10,
                    scale_total_cap_seconds=900, rss_cap_bytes=1073741824, rss_poll_seconds=.05,
                    session_deadline_utc='2026-09-08T00:50:00+00:00',
                    python=sys.executable, python_version=sys.version, platform=platform.platform(),
                    final_evaluation=False, retries=False, post_result_exclusions=[],
                    output_comparison='packed cursor and root curve versus historical all-ideal curves; different output contracts',
                    checker_scope='general curve arithmetic plus sorted-order corollary; no independent theorem proof')
    save(ROOT / 'MANIFEST.json', manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, indent=2))


if __name__ == '__main__': main()

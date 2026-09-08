#!/usr/bin/env python3
"""Replay the paper's four-job work-cap example through the public compiler CLI."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='new output directory')
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[1],
                        help='artifact repository root; normally inferred automatically')
    args = parser.parse_args()
    repository = args.repository.resolve()
    package = repository / 'package'
    out = args.out.resolve()
    if out.is_relative_to(package):
        raise ValueError('output must be outside the frozen package')
    out.mkdir(parents=True, exist_ok=False)
    case = {'cp': [[3, 2], [7, 2], [5, 6], [1, 2]], 'edges': [[0, 1], [0, 2], [1, 3]]}
    case_path = out / 'case.json'
    case_path.write_text(json.dumps(case, sort_keys=True) + '\n')
    commands = []

    def call(arguments, name):
        command = [sys.executable, '-B', str(package / 'retry.py'), *map(str, arguments)]
        result = subprocess.run(command, capture_output=True, timeout=30)
        (out / (name + '.stdout.json')).write_bytes(result.stdout)
        (out / (name + '.stderr.txt')).write_bytes(result.stderr)
        commands.append({'arguments': list(map(str, arguments)), 'exit_code': result.returncode})
        result.check_returncode()
        return json.loads(result.stdout)

    adaptive = out / 'adaptive.json'
    call(['compile', '--input', case_path, '--out', adaptive], 'adaptive-compile')
    actual = call(['query', '--artifact', adaptive, '--budgets', 2], 'adaptive-query')
    if actual['scope'] != 'GLOBAL_ADAPTIVE_RETRY_GAME':
        raise RuntimeError('unexpected adaptive certificate scope')
    total = actual['results'][0]['total_for_normal_cost_equal_to_c']
    fixed = []
    for order in itertools.permutations(range(4)):
        rank = {job: i for i, job in enumerate(order)}
        if any(rank[u] >= rank[v] for u, v in case['edges']):
            continue
        identity = ''.join(map(str, order))
        order_path = out / ('order-' + identity + '.json')
        order_path.write_text(json.dumps(order) + '\n')
        artifact = out / ('fixed-' + identity + '.json')
        call(['compile', '--input', case_path, '--order', order_path, '--out', artifact], 'fixed-' + identity + '-compile')
        query = call(['query', '--artifact', artifact, '--budgets', 2], 'fixed-' + identity + '-query')
        if query['scope'] != 'SUPPLIED_SERIAL_ORDER_ONLY':
            raise RuntimeError('unexpected fixed-order certificate scope')
        fixed.append({'order': list(order), 'total_work': query['results'][0]['total_for_normal_cost_equal_to_c']})
    if total != 24 or len(fixed) != 3 or any(r['total_work'] != 26 for r in fixed):
        raise RuntimeError('published example differs from compiler result')
    result = {'budget': 2, 'normal_work': 16, 'adaptive_total_work': total,
              'all_fixed_orders': fixed, 'work_cap': 25,
              'adaptive_meets_cap': total <= 25,
              'any_fixed_order_meets_cap': any(r['total_work'] <= 25 for r in fixed),
              'scope': 'Declared counted-work contract; not elapsed time or arbitrary Java code',
              'known_input_replay': True, 'scientific_sample_increase': False,
              'frozen_package_manifest_sha256': hashlib.sha256((package / 'MANIFEST.json').read_bytes()).hexdigest()}
    (out / 'COMMANDS.json').write_text(json.dumps(commands, indent=2) + '\n')
    (out / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

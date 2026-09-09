from pathlib import Path
import datetime
import hashlib
import json
import time
import curves
import checker

HERE = Path(__file__).resolve().parent
receipt = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'purpose': 'Exact all-budget compiler export; not native execution or speedup evaluation',
           'source_hashes': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                             for name in ('curves.py', 'checker.py', 'export.py', 'PLAN.md')},
           'inputs': []}
for lam in (1, 3, 10):
    case = {'id': 'deephaven_fixed_forest_lambda_' + str(lam), 'cp': [[4, 4 * lam], [176, 176 * lam]],
            'edges': [[0, 1]], 'provenance': 'source-derived selected-operation caps; fixed author fixture'}
    start = time.perf_counter_ns()
    certificate = curves.compile_case(case)
    compile_ns = time.perf_counter_ns() - start
    certificate_bytes = (json.dumps(certificate, sort_keys=True, indent=2) + '\n').encode()
    cert_path = HERE / f'certificate_{lam}.json'
    with cert_path.open('xb') as f:
        f.write(certificate_bytes)
    reparsed = json.loads(certificate_bytes)
    start = time.perf_counter_ns()
    result = checker.check(reparsed)
    check_ns = time.perf_counter_ns() - start
    assert not result['violations']
    digest = hashlib.sha256(certificate_bytes).hexdigest()
    lines = ['RETRY_PROFILE_V1', f'lambda {lam}', 'caps 4 176', 'certificate ' + digest]
    for mask, profile in sorted(certificate['curves'].items()):
        for a, value, slope in profile:
            lines.append(f'piece {mask} {a} {value} {slope}')
    data = ('\n'.join(lines) + '\n').encode()
    profile_path = HERE / f'profile_{lam}.txt'
    with profile_path.open('xb') as f:
        f.write(data)
    huge = [{'budget': b, 'root_excess': curves.at(certificate['curves'][3], b),
             'default_action': curves.choose(certificate, 3, b)} for b in (10**6, 10**12, 10**18)]
    assert all(x['root_excess'] == lam * 180 for x in huge)
    receipt['inputs'].append({'lambda': lam, 'input': case, 'compile_nanoseconds': compile_ns,
                              'check_nanoseconds': check_ns, 'certificate_bytes': len(certificate_bytes),
                              'certificate_sha256': digest, 'profile_bytes': len(data),
                              'profile_sha256': hashlib.sha256(data).hexdigest(),
                              'states': certificate['states'], 'segments': certificate['segments'],
                              'all_budget_checker': result, 'huge_queries': huge})
with (HERE / 'EXPORT_RECEIPT.json').open('x') as f:
    json.dump(receipt, f, indent=2)
    f.write('\n')
print(json.dumps(receipt, indent=2))

"""One cold charged-construction workload; parent supplies time/RSS bounds."""
from pathlib import Path
import json
import platform
import resource
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
CURVES = HERE.parent / 'charged_curves_02'


def bind_certificate(method, decoded, case, budgets):
    assert decoded['input'] == case, 'certificate belongs to another requested input'
    if method == 'PEAK':
        assert decoded['budgets'] == budgets, 'certificate budget order differs from request'


def main(method, input_path, output_path):
    started = time.perf_counter()
    output = Path(output_path)
    phases = {}
    result = dict(status='FAILURE', method=method, phases=phases)
    try:
        unit = json.loads(Path(input_path).read_text())
        assert unit['method'] == method
        case, budgets = unit['case'], unit['budgets']
        phases['input'] = time.perf_counter() - started
        before = time.perf_counter()
        if method == 'ALL':
            sys.path.insert(0, str(CURVES))
            import basis
            import checker
            phases['method_import'] = time.perf_counter() - before
            before = time.perf_counter()
            artifact = basis.compile_case(case)
            phases['construct'] = time.perf_counter() - before
            before = time.perf_counter()
            text = json.dumps(artifact, separators=(',', ':'), sort_keys=True)
            (output / 'CERTIFICATE.json').write_text(text)
            phases['serialize_write'] = time.perf_counter() - before
            before = time.perf_counter()
            decoded = json.loads((output / 'CERTIFICATE.json').read_text())
            bind_certificate(method, decoded, case, budgets)
            phases['read_parse'] = time.perf_counter() - before
            before = time.perf_counter()
            report = checker.check(decoded)
            phases['certificate_check'] = time.perf_counter() - before
            before = time.perf_counter()
            profile = decoded['curves'][str(decoded['full'])]
            values = [checker.value(profile, b) for b in budgets]
            phases['query'] = time.perf_counter() - before
            result.update(values=values, certificate_bytes=len(text.encode()), check=report,
                          stats=dict(states=decoded['states'],
                                     basis_lines=sum(len(b) for b in decoded['bases'].values()),
                                     profile_rows=sum(len(f) for f in decoded['curves'].values())),
                          certificate_scope='ALL_BUDGET_BELLMAN_PRICES_ROUTING_BASIS')
        elif method == 'PEAK':
            import oracle
            import point_checker
            phases['method_import'] = time.perf_counter() - before
            before = time.perf_counter()
            solved = oracle.solve_many(case, budgets)
            phases['construct'] = time.perf_counter() - before
            before = time.perf_counter()
            text = json.dumps(solved['artifact'], separators=(',', ':'), sort_keys=True)
            (output / 'CERTIFICATE.json').write_text(text)
            phases['serialize_write'] = time.perf_counter() - before
            before = time.perf_counter()
            decoded = json.loads((output / 'CERTIFICATE.json').read_text())
            bind_certificate(method, decoded, case, budgets)
            phases['read_parse'] = time.perf_counter() - before
            before = time.perf_counter()
            report = point_checker.check(decoded)
            phases['certificate_check'] = time.perf_counter() - before
            before = time.perf_counter()
            values = list(decoded['values'])
            phases['query'] = time.perf_counter() - before
            result.update(values=values, certificate_bytes=len(text.encode()), check=report,
                          stats=solved['stats'], certificate_scope='REQUESTED_ROOT_VALUES')
        else:
            if method == 'DP':
                import direct as engine
            else:
                assert method == 'GENERIC'
                import generic as engine
            phases['method_import'] = time.perf_counter() - before
            before = time.perf_counter()
            solved = engine.solve_many(case, budgets)
            phases['construct'] = time.perf_counter() - before
            before = time.perf_counter()
            text = json.dumps(solved, separators=(',', ':'), sort_keys=True)
            (output / 'VALUES.json').write_text(text)
            phases['serialize_write'] = time.perf_counter() - before
            before = time.perf_counter()
            decoded = json.loads((output / 'VALUES.json').read_text())
            phases['read_parse'] = time.perf_counter() - before
            result.update(values=decoded['values'], certificate_bytes=len(text.encode()),
                          stats=decoded['stats'], certificate_scope=decoded['certificate_scope'])
        result.update(status='SUCCESS', budgets=budgets,
                      baseline=sum(w + min(v, g + r) for w, p, g, v, r in case['jobs']))
    except Exception:
        result.update(status='FAILURE', error=traceback.format_exc())
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result.update(internal_seconds=time.perf_counter() - started,
                  process_peak_rss_bytes=maximum if platform.system() == 'Darwin' else 1024 * maximum)
    with (output / 'RESULT.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'method', 'internal_seconds')}))
    if result['status'] != 'SUCCESS':
        raise SystemExit(1)


if __name__ == '__main__':
    main(*sys.argv[1:])

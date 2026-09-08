import hashlib
import json
import pathlib
import sys
import time
import traceback
import check
import hybrid


def main():
    method, src, dest = sys.argv[1:]; out = pathlib.Path(dest); start = time.perf_counter()
    try:
        if method == 'compile':
            case = json.loads(pathlib.Path(src).read_text()); compiled = hybrid.compile_case(case)
            encoded = json.dumps(compiled, sort_keys=True, separators=(',', ':')).encode()
            with (out / 'controller.json').open('xb') as f: f.write(encoded)
            built = time.perf_counter() - start
            assert compiled['route'] == 'ordered'
            saturation = sum(count for height, count in compiled['value_slopes'])
            budgets = sorted({0, 1, 2, len(case['cp']), saturation // 2, saturation})
            row = dict(status='SUCCESS', route=compiled['route'], construction_serialization_seconds=built,
                       jobs=len(case['cp']), edges=len(case['edges']), slope_runs=len(compiled['value_slopes']),
                       controller_bytes=len(encoded), controller_sha256=hashlib.sha256(encoded).hexdigest(),
                       normal_cost=compiled['normal_cost'], saturation=saturation,
                       queries=[dict(b=b, extra_cost=hybrid.value(compiled, b)) for b in budgets])
        elif method == 'check':
            encoded = pathlib.Path(src).read_bytes(); compiled = json.loads(encoded)
            checked = check.check(compiled)
            row = dict(status='FAILURE' if checked.get('violations') else 'SUCCESS', symbolic=checked,
                       controller_sha256=hashlib.sha256(encoded).hexdigest())
        else: raise ValueError(method)
    except AssertionError: row = dict(status='FAILURE', error=traceback.format_exc())
    except Exception: row = dict(status='INVALID', error=traceback.format_exc())
    row['worker_seconds'] = time.perf_counter() - start
    with (out / 'RESULT.json').open('x') as f: json.dump(row, f, sort_keys=True); f.write('\n')


if __name__ == '__main__': main()

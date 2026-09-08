from pathlib import Path
import hashlib
import importlib.util
import json
import resource
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
S = ROOT.parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    begin = time.perf_counter()
    method, source, destination = sys.argv[1:]
    out = Path(destination)
    try:
        assert __debug__
        unit = json.loads(Path(source).read_text())
        t = time.perf_counter()
        if method == 'previous':
            shape = module('compare_old_shape', S / 'final_evaluation_dag_01/structure.py')
            scanner = module('compare_old_bellman', S / 'dependency_curves_01/checker.py')
        elif method == 'sweep':
            scanner = module('compare_sweep_scanner', ROOT / 'certificate.py')
        else:
            raise ValueError(method)
        imports = time.perf_counter()-t
        t = time.perf_counter()
        encoded = (S / unit['path']).read_bytes()
        assert hashlib.sha256(encoded).hexdigest() == unit['sha256']
        data = json.loads(encoded)
        reading = time.perf_counter()-t
        t = time.perf_counter()
        if method == 'previous':
            structural = shape.check(data)
            result = scanner.check(data)
            assert result['checked_states'] == structural['states']
        else:
            result = scanner.check(data)
        checking = time.perf_counter()-t
        assert not result['violations'], result
        row = dict(status='SUCCESS', artifact_sha256=unit['sha256'], report=result,
             import_seconds=imports, read_hash_parse_seconds=reading,
             check_seconds=checking, worker_seconds=time.perf_counter()-begin,
             ru_maxrss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             ru_maxrss_units='bytes on recorded Darwin platform')
    except AssertionError:
        row = dict(status='FAILURE', error=traceback.format_exc())
    except Exception:
        row = dict(status='INVALID', error=traceback.format_exc())
    with (out / 'RESULT.json').open('x') as f:
        json.dump(row, f, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    main()

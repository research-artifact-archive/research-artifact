import hashlib
import json
import pathlib
import sys
import time
import traceback
import check


def main():
    source, destination = sys.argv[1:]; start = time.perf_counter()
    try:
        data = pathlib.Path(source).read_bytes(); compiled = json.loads(data); result = check.check(compiled)
        row = dict(status='SUCCESS', symbolic=result, controller_sha256=hashlib.sha256(data).hexdigest())
    except AssertionError: row = dict(status='FAILURE', error=traceback.format_exc())
    except Exception: row = dict(status='INVALID', error=traceback.format_exc())
    row['loading_checking_seconds'] = time.perf_counter() - start
    with (pathlib.Path(destination) / 'RESULT.json').open('x') as f: json.dump(row, f, sort_keys=True); f.write('\n')


if __name__ == '__main__': main()

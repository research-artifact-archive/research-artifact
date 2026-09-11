"""Exclusive-output runner, source-hash verification and <=270 second watchdog."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    family = sys.argv[1]
    freeze_path = HERE / 'FREEZE.json'
    freeze = json.loads(freeze_path.read_text())
    assert family in freeze['family_input_counts']
    for name, expected in freeze['files'].items():
        assert sha(HERE / name) == expected, ('frozen input changed', name)
    receipt_path = HERE / (family + '_RECEIPT.json')
    assert not receipt_path.exists(), 'family already attempted'
    start = datetime.datetime.now(datetime.timezone.utc)
    remaining = (datetime.datetime(2026, 9, 11, 4, 58, tzinfo=datetime.timezone.utc) - start).total_seconds()
    assert remaining > 0, '13:58 JST research-sidecar cutoff has passed'
    cap = min(270, int(remaining))
    started_mono = time.monotonic()
    receipt = dict(family=family, started_at_utc=start.isoformat(),
                   freeze_sha256=sha(freeze_path), target_sha256=freeze['files']['target_filter01.py'],
                   planned_inputs=freeze['family_input_counts'][family], timeout_seconds=cap,
                   status='RUNNING', command=[sys.executable, '-B', str(Path(__file__).resolve()), family])
    with (HERE / (family + '_START.json')).open('x') as out:
        json.dump(receipt, out, indent=2, sort_keys=True)
    def alarm(signum, frame):
        raise TimeoutError('frozen family watchdog/cutoff reached')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(cap)
    rawpath, failurepath = HERE / (family + '_RAW.jsonl'), HERE / (family + '_FAILURES.jsonl')
    with rawpath.open('x') as raw, failurepath.open('x') as failures:
        checker = None
        try:
            from checker import Checker
            target_file = str(HERE / 'target_filter01.py')
            spec = importlib.util.spec_from_file_location('frozen_filter_attempt02', target_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            checker = Checker(module.ChargedFilter, target_file, raw)
            with (HERE / 'inputs.jsonl').open() as inp:
                for line in inp:
                    case = json.loads(line)
                    if case['family'] == family:
                        checker.execute(case)
            assert checker.counts['inputs_completed'] == receipt['planned_inputs']
            if family == 'initial':
                assert checker.counts['query_pairs'] == freeze['planned_initial_totals']['initial_queries']
                assert checker.counts['permitted_actions_completed'] + checker.counts['forbidden_actions_rejected'] == freeze['planned_initial_totals']['initial_actions']
            for name, expected in freeze['files'].items():
                assert sha(HERE / name) == expected, ('frozen input changed during run', name)
            receipt['status'] = 'PASS'
        except BaseException as exc:
            receipt['status'] = 'TIMEOUT' if isinstance(exc, TimeoutError) else 'FAIL'
            detail = dict(exception_type=type(exc).__name__, message=str(exc),
                          details=getattr(exc, 'detail', None), traceback=traceback.format_exc(),
                          context=checker.context if checker else None)
            failures.write(json.dumps(detail, sort_keys=True, separators=(',', ':')) + '\n')
            receipt['failure'] = dict(exception_type=type(exc).__name__, message=str(exc))
        finally:
            signal.alarm(0)
            receipt['counts'] = dict(checker.counts) if checker else {}
            receipt['operation_maxima'] = dict(checker.operation_maxima) if checker else {}
            receipt['elapsed_seconds_resource_accounting_only'] = time.monotonic() - started_mono
            receipt['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt['raw_sha256'], receipt['failures_sha256'] = sha(rawpath), sha(failurepath)
    receipt['frozen_hashes_unchanged'] = all(sha(HERE / name) == expected for name, expected in freeze['files'].items())
    receipt['current_root_sources'] = {name: sha(HERE.parent.parent / 'charged_general_01' / name) for name in freeze['sources']}
    with receipt_path.open('x') as out:
        json.dump(receipt, out, sort_keys=True, indent=2)
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

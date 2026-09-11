"""Post-timeout, append-only preparation. Does not import or execute the filter."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
A = HERE / 'attempt01'
B = HERE / 'attempt02'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not B.exists()
    old_receipt = json.loads((A / 'streams_RECEIPT.json').read_text())
    assert old_receipt['status'] == 'TIMEOUT'
    assert sha(A / 'streams_RAW.jsonl') == old_receipt['raw_sha256']
    assert sha(A / 'streams_FAILURES.jsonl') == old_receipt['failures_sha256']
    completed, old_steps = set(), {}
    with (A / 'streams_RAW.jsonl').open() as inp:
        for line in inp:
            row = json.loads(line)
            if row['phase'] == 'terminal':
                completed.add(row['id'])
            elif row['phase'] == 'step':
                old_steps[row['id']] = old_steps.get(row['id'], 0) + 1
    assert len(completed) == old_receipt['counts']['inputs_completed'] == 37
    cases = [json.loads(line) for line in (A / 'inputs.jsonl').read_text().splitlines()]
    unfinished = [c for c in cases if c['family'] == 'streams' and c['id'] not in completed]
    assert len(unfinished) == 2
    B.mkdir()
    for name in ['reference.py', 'target_filter01.py', 'target_PROOF01.md', 'target_FILTER_DERIVATION01.md']:
        shutil.copyfile(A / name, B / name)
    checker = (A / 'checker.py').read_text()
    old = 'def full(obj):\n    return copy.deepcopy(obj.__dict__)'
    new = '''def full(obj):
    # Every target array holds immutable int/bool entries; heaps are two such arrays.
    # Copy all six arrays, preserving the complete dict and counters, without a
    # Python recursive deepcopy visit for every immutable scalar in every query.
    return {key: [list(heap) for heap in value] if key == 'heaps'
            else list(value) if type(value) is list else copy.deepcopy(value)
            for key, value in obj.__dict__.items()}'''
    assert checker.count(old) == 1
    (B / 'checker.py').write_text(checker.replace(old, new))
    runner = (A / 'run_family.py').read_text().replace('frozen_filter_attempt01', 'frozen_filter_attempt02')
    (B / 'run_family.py').write_text(runner)
    shutil.copyfile(Path(__file__), B / 'prepare_attempt02.py')
    with (B / 'inputs.jsonl').open('x') as out:
        for case in unfinished:
            out.write(json.dumps(case, sort_keys=True, separators=(',', ':')) + '\n')
    protocol = '''# Corrected harness attempt02 — unfinished streams only

Author-side bounded implementation verification, LOCAL route. Same user delegation,
write scope, 14:00 JST reporting deadline, 13:58 launcher cutoff and 270-second cap
as attempt01. Not blind review, theorem audit, workloads or latency evidence.

This protocol is frozen AFTER observing attempt01 streams TIMEOUT. Attempt01 remains
TIMEOUT with its complete prior raw, failure traceback, 37 completed series and
partial next series. No old result or denominator is changed. This is not a new
independent sample or a target fix. Root filter SHA remains exactly unchanged.

Input selection is all and only series without a terminal raw record in attempt01:
streams-000037 (n=4096 alternating) and streams-000038 (n=4096 half-completed fresh).
Both are byte-equivalent input records from the earlier frozen input file. Their
6144 steps cover the outstanding obligations, including rechecking the partial
prefix of streams-000037. The repeated prefix is disclosed and not double-counted.
Use attempt01's completed series and attempt02's complete unfinished series for
combined coverage; retain attempt01's partial series and compare overlapping raw.

The ONLY checker change is snapshot construction for full object mutation checks:
copy each known flat int/bool array and the two flat heap arrays with list(), and
copy all scalar/other dict entries. This retains all state, capacities, handles,
values, done flags and counters while avoiding recursive Python visits to every
immutable scalar. Assertions, sorting oracle, target operations, instrumentation,
thresholds, order, bodies, outcome policies, heap invariants and per-step checks
are unchanged. Runner module label is updated to attempt02 only. Target, proof
and derivation snapshots are exact copies of attempt01. No original source is edited.

All original protocol formulas and success/falsification thresholds apply. Preserve
any failure or timeout in new exclusive raw/receipts; do not retry this attempt.
Hash this protocol, inputs, checker, reference, runner, preparer and source snapshots
in FREEZE.json before any target execution. Verify the old attempt01 freeze/raw/
receipt/failure hashes afterward. Record original timeout separately even if the
combined coverage finishes successfully. A discovered target bug still goes to
root for a patch and would require another explicit frozen corrected attempt.
'''
    (B / 'PROTOCOL.md').write_text(protocol)
    names = ['PROTOCOL.md', 'inputs.jsonl', 'checker.py', 'reference.py', 'run_family.py',
             'prepare_attempt02.py', 'target_filter01.py', 'target_PROOF01.md', 'target_FILTER_DERIVATION01.md']
    oldfreeze = json.loads((A / 'FREEZE.json').read_text())
    predecessors = {name: sha(A / name) for name in ['FREEZE.json', 'streams_START.json',
                                                   'streams_RECEIPT.json', 'streams_RAW.jsonl', 'streams_FAILURES.jsonl']}
    manifest = dict(attempt='attempt02', frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         monotonic_ns=time.monotonic_ns(), family_input_counts={'streams': len(unfinished)},
         files={name: sha(B / name) for name in names}, sources=oldfreeze['sources'],
         predecessor_hashes=predecessors, predecessor_status='TIMEOUT',
         completed_series_retained=sorted(completed), repeated_prefix_steps={c['id']: old_steps.get(c['id'], 0) for c in unfinished},
         planned_stream_steps=sum(len(c['order']) for c in unfinished),
         target_executed_before_this_freeze=True,
         disclosure='Target previously tested in attempt01; revised harness not executed before this freeze.',
         revised_harness_executed_before_freeze=False, timeout_seconds=270, output_scope=str(HERE))
    with (B / 'FREEZE.json').open('x') as out:
        json.dump(manifest, out, indent=2, sort_keys=True)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()

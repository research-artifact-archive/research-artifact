# Corrected harness attempt02 — unfinished streams only

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

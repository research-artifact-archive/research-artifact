# Fixed native DAG evaluation 01

Author-created bounded contract conformance and causal-policy comparison. This is
the new fixed native evaluation; all selected earlier native witness results stay
exploratory. It does not provide application prevalence, observed interference
budgets, latency benefit or user impact. Root is sole writer.

## Generator fixed before model/native outcomes

Seed 202609080250. Use n=3,4,5; two structural strata; eight vectors per n/stratum,
for 48 core vectors. Generate each possible forward edge with probability 0.35,
and always include 0->n-1. In the ordered stratum sort n independent integer costs
from 1..12. In the general stratum draw all costs from 1..12, then draw c0 from
2..12 and c(n-1) from 1..c0-1, enforcing an incompatible edge. Draw each p from
0..24. Apply a uniform seeded permutation of the job labels, moving costs,
premiums and edges together. Do not inspect costs/values to replace a sample or
search for a favorable seed. Keep any repeated vector as a specified unit and
report exact overlaps rather than replacing it. All graphs have a dependency.

For each core vector use budgets {0,1,2,4}, both distinct and colliding bins, and
five actual policies: the serialized hybrid controller; the best fixed topological
completion order for that initial budget with exact adaptive modes; both existing
fixed-mode-bound lookahead ties; and the exact adaptive cached-fallback family.
This fixes 192 priced-budget roots, 384 root/layout cells and 1,920 policy cells.
Enumerate every topological order for the fixed-order comparator and every
terminal outcome path for every policy before native execution. Root/layout/path
counts are not interchangeable with workload counts. No selected witness is
inserted into the 48-vector core sample.

Separate immutable-parent controls use two 2-job chains at B=1, only the all-normal
hybrid path, both layouts: (c,p)=[(2,1),(3,2)] is an exact earlier regression; and
[(3,1),(1,2)] exercises the general route. An external write changes completed
parent 0's live value before child 1 starts. The child must consume the captured
foreground milestone. Four controls are separate from the 192 comparison roots.

## Concrete kernel and costs

Retain the whole array-transform kernel, immutable Value identity, parent-output
folding, guarded-weight mapping, actual Java replace/compute operations, and
Python output reconstruction from dependency_native_01. The transform executes
one counted step for each parent seed fold and each resulting array entry;
length_i=8*c_i-indegree_i, d=lcm(c_i), q_i=d*p_i/c_i. Therefore measured
d*W+sum_i q_i*L_i equals 8*d times abstract total work, with a_i=c_i. This is a
declared weighted-work objective; it is not elapsed time or an empirical premium.
All lengths must be positive; failures are retained if any declared mapping fails.

The actual native ordered route reads the emitted order/threshold deployment and
uses a cursor, advancing only on successful/protected completion. Failed retries
keep the cursor. The program separately retains completion information for
readiness. The general route reads emitted integer curves and selects actions
from the actual remaining mask/budget. Neither hybrid route performs runtime
synthesis or reads a future outcome before selection. Full JSON certificates,
including root curves, stay saved even when only order/thresholds are deployed.
Comparators select their own actions causally. Counted kernel work is the common
objective; no Java policy-speed comparison is claimed.

All adversarial writes run in the actual separate background executor. A planned
failure is a completed external write after fresh preparation and before its
comparison/callback; a normal outcome omits that write. Postwrite controls count
their extra completed-key write against total B even though it is not a failed
comparison. Both layouts retain the previous fixed capacity/no-resize scope.

## Preparation, freeze, execution, checking

Freeze generator/plan before generating model values. Save all 48 vectors and
their source overlaps. Then separately materialize scalar model values, all
topological orders, independently checked serialized hybrid certificates,
deployment bytes, exact terminal schedules and expected actions, arrays/digests,
generations, parent seeds, measured work, protected work and write counts. Model
preparation is observed before the native experiment and is reported as such.
Freeze all exact inputs, sources/imports, native runtime/compiler hashes, command
lines and terminal-unit denominator before native compilation/execution.

One run, no retry/replacement/exclusion. Java compile cap 30s; native execution
cap 120s; -Xmx256m and one active processor. Background write join cap 2s.
Save raw stdout/stderr and class hashes. Every planned path is SUCCESS, FAILURE,
TIMEOUT, INVALID, or NOT_RUN. Missing/duplicate/unexpected IDs, parse problems,
value mismatches and preparation defects remain explicit. Compare all policy
maxima only when every constituent path succeeds; include failed/unstarted
paths in the denominator. Check identities and recompute expected outputs after
the run without rerunning native paths. Report preparation, compile and execution
costs separately, retaining all earlier development cost and adverse outcomes.

Stop new work by Sep8 09:50 JST and stop/report at10:00. This evaluation cannot
close practical significance, source-fit gaps, closest-work novelty or readiness.

# Fixed final DAG semantic evaluation 01

This is a fixed final evaluation of the current author implementation under the
stated guarded-kernel contract, following preserved development. It is not a
held-out application population, a native benchmark, a proof of the theorem, or
an independent blind review. Old raw outcomes and development costs remain.

## Inputs and complete denominators

Use every n=1,2,3 and every subset of the possible forward edges i<j. For each
specified graph use every vector of (c,p) in {1,2} x {0,1,2,3}, and every initial
budget b=0..4. Keep transitive-edge-redundant graphs and equal-cost ties. There
are 11 graph descriptions, 4,232 priced inputs and 21,160 roots. There are
1,220,680 admissible physical state-budget pairs, 9,239,600 controller actions,
and 12,551,856 adversarial outcome edges. These counts were materialized without
solving any final value and are checked per input during execution.

The 584 empty-edge inputs are explicit regression of the previous independent
final grid. Of 3,648 dependent inputs, four were observed in the new development
preflight; none exactly coincide with the earlier 643 DAG input corpus or its
719-input hybrid extension. The complete exact overlap mapping is in INPUTS.json
and DENOMINATORS.json. No claim of statistical independence or unseen population
is made. Non-topological labels have separate preserved development coverage;
this grid does not enumerate all labeled DAGs.

## Compared contracts and checks

For every input enumerate all admissible physical U,C,L,LC,D states and budgets,
including guards acquired before readiness, all fixed batch subsets and outcomes,
retained cached preparation, atomic fallback, discard/release, and zero-cost
cycles. Only evaluate a fresh/guarded kernel or perform atomic fresh execution
after every actual parent has completed. Preserve every adversarial transition
allowed by the remaining budget. Use unchanged AND/OR solving and separately
check Bellman minima for every physical state and a goal-reaching rank for its
selected policy.

Compute the scalar DAG recursion without importing curve construction. Check
the physical invariants, the potential lower bound at every state, and its
one-step inequality at every action. Compare all roots against the scalar value
and serialized/reloaded hybrid root. Compile once per input for all budgets.
Check every stored policy state for every b=0..4 against the scalar Bellman
optimum, using suffix masks on the ordered route and all valid masks on the
general route.

Additionally check all-subset scalar monotonicity, cheapest-fast dominance with
all minimum-cost ties, one-pass inequalities for every subset of available jobs,
cached-fallback bounds, budget monotonicity and discrete concavity over b=0..4.
These are finite regression checks of proof lemmas and do not replace proofs.

For the general route first check complete reachable-mask coverage, root/counts,
input acyclicity, integer contiguous normalized curves, zero/tail boundaries,
exact available actions and cheapest-fast tie metadata. Then use the unchanged
all-integer-domain affine Bellman checker. The separate packed-root checker
checks the ordered route. All-budget certificate claims are symbolic checks of
the emitted functions; explicit full primitive enumeration covers only b=0..4.
The shared model, theorem, runtime, input parser and author implementation are
part of the trusted basis and are not independent validation of each other.

## Fixed execution and failure handling

Freeze this plan, complete inputs, structural denominators, source files,
unchanged imported code, previous overlap inputs, development raw/manifest and
author-side verification receipt in MANIFEST.json before starting. Assertions
must be enabled. Bind Python executable hash/version and platform. One sequential
run; 10 seconds per input and 180 seconds total soft bound, with no new unit after
09:50 JST. No retries, replacements or exclusions. Timeout of an executing unit
is TIMEOUT; later units that cannot start are NOT_RUN. Unexpected exceptions are
INVALID; mismatches, counterexamples or failed validator assertions are FAILURE.
All units retain IDs and remain in the denominator. Memory has no claimed cap;
record observed process peak RSS. No native process or external solver is invoked.

All required equalities must hold for SUCCESS; any adverse unit prevents an
all-input correctness claim. Save each successful emitted artifact and its hash,
per-input raw results and timing, aggregate outcomes, counts and all adverse
details. Report compile/serialization and checking costs as well as whole-run
cost; do not turn this small-domain semantic run into a performance comparison.
Development preflight 10/10 and checker controls 25/25 remain separately labeled.

Stop all work once at 2026-09-08 10:00 JST and report. This plan does not extend
that deadline or establish practical importance, novelty or submission readiness.

# A certificate for safe protection choices

This extension characterizes which actions preserve the universal call/protected-work guarantees after the allowed failed calls have been spent. It does not establish a general total-work optimum.

Let `S` be the unfinished jobs, `ell` the protected work already paid, and `h` the number of later cached mismatches. `Top_t(T)` sums the largest `min(t, |T|)` fixed job works in `T`. A suffix with no remaining failed-call allowance can satisfy the required envelope at every future writer budget exactly when

```text
ell + Top_t(S) <= Top_(h+t)(J)    for t = 0, ..., |S|.
```

Fresh completion of next ready job `i` is permitted exactly when the same inequalities hold for `(S-i, h, ell+w_i)`. Cached completion preserves feasibility on both outcomes. The conditions give a finite certificate for allowable choices. They need no writer-budget input. The actual-write interpretation requires the modeled prefix to admit an exact `r+h`-write realization; the theorem is not a compression of arbitrary histories that separately reveal extra writes. Whole fixed kernels, no held guards or cross-job batches, and persistent captured predecessor outputs remain required. The [complete proof](evidence/RESUMED_20260909_1413/protected_suffix_02/THEORY.md) also characterizes a designated fresh subset.

The earlier all-tail guard and the new greedy one-job rule choose different feasible actions. Both weakly improve worst total work over the same-order threshold rule, but neither dominates the other. Of 209,408 fixed roots over 6,544 authored inputs, the new rule is lower at one root, higher at three, and equal at 209,404 relative to all-tail. The new input portion comprises 1,024 five-job chains; 5,520 inputs were already observed. The [full result guide](evidence/RESUMED_20260909_1413/protected_suffix_02/RESULTS.md) gives both favorable and adverse examples. None is labeled held out.

A separate finite-rank AND-OR solver checks 665,500 states for 363 weight tuples, with 1,331,000 comparisons across arbitrary-order and fixed-order choices. All agree with the certificate: 271,630 feasible and 393,870 infeasible states. A Java selector receiving only weights, predecessors, the failure allowance, policy and its own outcomes executes all 20,594 fixed paths. The checker confirms exact outputs, captured parents, identities, actual selected kernel iterations and call counts, all 384 maxima, and eight corruption rejections. The checker was fixed before the new native run but derived from an already observed checker. These are author finite checks and controlled semantic executions, not an independent proof or application population.

Run from the repository root with Python 3.10 or later and assertions enabled:

```sh
python3 -B charged/reproduce.py protected-suffix --out work/suffix --timeout 300
```

This twenty-second standard stage recomputes both complete equation ledgers byte-for-byte and checks every saved native path. The old 21 stages retain their workers and evidence. A separate JDK17 command compiles the new selector and re-executes all fixed paths, requiring exact raw-output bytes and maxima:

```sh
python3 -B charged/reproduce.py protected-suffix-java --out work/suffix-java --timeout 300
```

Use new output directories. The optional native command is deterministic semantic replay; it does not rerun a timing campaign. All earlier negative timing results and the all-tail/certificate incomparability remain preserved. Variable/lazy Roslyn transformations do not meet the fixed-work requirement of this theorem.

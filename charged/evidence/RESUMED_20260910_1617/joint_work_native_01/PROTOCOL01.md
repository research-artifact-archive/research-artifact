# Native check of the observable-comparison resource contract

Fixed before implementation execution. Route SCIENTIFIC; root sole writer. This addresses a new material model defect: B/C/D's attaining policies need to observe cached match/mismatch. The prior whole-kernel source wrapper already computes a local Boolean, but the refinement table called exporting it optional. No timing, SLA, deployment-importance or mechanical JMM claim follows. All old sources/results remain unchanged; create a new source and new output namespace.

Use the installed OpenJDK17.0.19+0 on this machine, recording javac/java versions and exact new source/input hashes. Use ConcurrentHashMap.compute on permanent existing keys, one foreground controller, one actual external-writer thread, stable identity equality, immutable result objects, and exact saved predecessor outputs. Kernel work is the prescribed wi per invocation; count all invocations and protected invocations. Q counts each public compute or conditional publication once. Diagnostic measurements do not control the policy. The policy receives only weights, DAG, its fixed order/cap, completion state, and the callback's local comparison Boolean.

## Fixed inputs and complete denominator

Six jobs/DAG fixtures:
1. singleton: works(8), no edges;
2. chain8_16: works(8,16), edge0->1;
3. chain16_8: works(8,16), edge1->0;
4. independent8_16: works(8,16), no edges;
5. fork: works(1,2,4), edges0->2,1->2;
6. tied: works(2,2,1), no edges.

For each fixture, use each distinct M in {0,w_i} with the Lawler order, plus all-cached and all-fresh comparators. For a Lawler policy, jobs heavier than M complete fresh and lighter jobs prepare/cached; after the first observed mismatch, prepare/cached all remaining jobs. Within B=1 that last phase always matches and has the same costs as the earlier mathematical prepare/cheap suffix. Cached completion preserves Q=n outside the promised B as well, without preserving W/L caps there. No outside-B runs are part of this attempt.

Cross every policy with two key layouts (distinct and colliding bins) and two kernels: fresh allocation from actual immutable own input/completed parents, and a fixed-work pure payload computation whose completed output is a canonical immutable per-job object. The latter deliberately makes returned-output reference equality unable to identify recomputation; it tests the sufficiency of the explicit Boolean. It is not silently treated as satisfying the prior fresh-allocation kernel assumption.

Writer schedules: no write, plus every single write indexed by (completion position k, target job j, phase), k,j in0..n-1 and phase in {before preparation/operation, after preparation before the counted call, after the counted API returns before saving the milestone}. For a fresh node the first two phases are both legitimate before-call positions and remain distinct inputs. A write to an unrelated key is retained. Phase3 uses the API's saved output even if the live map changes. There are1+3n^2 schedules per fixture. Budget is always an upper bound1; no-write cases are included. This yields2,076 correct-policy executions:64 singleton +780 across the three two-job fixtures +672 fork +560 tied.

Negative controls: for chain8_16 and independent8_16 at M=8, canonical-output kernels only, both layouts and all13 schedules, force the policy to treat every cached callback as a match while retaining the real flag only in diagnostics. There are52 separate controls. Exactly four schedules are predicted to expose L=24>16: at the first/light cached call, write its own key after preparation but before comparison, for two fixtures and two layouts. Other controls can remain within the resource caps and must not be discarded. This is an expected counterexample, not a successful valid policy. Total2,128 executions.

## Outcomes and checks

For every case save actual mode/job sequence, captured/current/returned reference identifiers, comparison Boolean, returned-is-prepared equality, completed/live outputs, each kernel invocation with its input/parents/protection, external committed write, Q/W/L and the independently computed caps. Policies never inspect diagnostic identifiers or counters. For correct policies require functional output correctness, permanent exact parent outputs, exactly n completing calls, <=1 external write, and W/L within the assigned mathematical caps. Reconstruct costs from invocation events in an independent Python checker. Lawler caps are W<=Omega+M and L equal to the scheduling maximum as an upper bound; all-cached is W<=Omega+wmax,L<=wmax; all-fresh is W=L=Omega. Preserve maxima and witness paths, not just per-case status.

For controls, separately record whether a violation was exposed and whether it matches the predicted condition; retain all52 rows. Never report all2,128 policies as satisfying the contract. A surprising absence or additional violation is a failed model/prediction check to investigate. Do not relabel the original outcome after a repair.

One compile-and-run attempt with a120-second execution cap and at most2seconds for each writer operation, and a180-second process cap including compilation. No automatic retry. Account for SUCCESS/FAILURE/INVALID/TIMEOUT/NOT_EXECUTED for all2,128 cases. Keep compilation/runtime errors and every unexecuted case; any implementation fix is a new successor with the failed attempt preserved. Stop the owned writer executor in finally and verify its termination. Do not modify the original BudgetBlindCallbacks.java or prior artifacts.

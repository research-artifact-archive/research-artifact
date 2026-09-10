# Guard entry separates resource/information contracts

This corrected author proof incorporates the read-only inspection in AUTHOR_PROOF_REVIEW01.json. The candidate01 and finite result01 remain unchanged; no observed values changed. The corrections specify the environment's write counters, include already-stale cached bodies in a lower-bound set, and make the observation/admissibility premises explicit. The scheduling algorithm is attributed to Lawler, not claimed as new.

## Interface and resource

Use the manuscript's finite persistent-job whole-kernel game, positive works w_i, DAG readiness, fresh own-key identities at post-choice gates, free inspections/retained records, charged computed initialization, and terminating selected operations. Guards do not survive calls; one completing call completes exactly one job. Cheap calls cost no guard entry, whereas every fresh or cached completing call costs a fixed g_i≥0, including a cached match. Let Γ=Σg_i and P_g=L+Σ_(guarded completed i)g_i. Here W remains body work. If needed, W_g=W+Σg_i counts that extra work too; no result about its joint frontier is asserted. The current native Linux study does not calibrate g_i, and this cheap-operation cost law is not a claim about Java replace's implementation.

An informed class promises Q≤n+r only in all environments with at most its supplied B writes. A universal class receives no B and promises that cap in every finite-write environment. Explicit cached match/mismatch observations remain available, without a clock or diagnostic cost channel. The absence of retained guards or batch completion prevents amortizing one g_i charge across several jobs.

## Theorem A: exact universal charged-protection curve

For every B,r≥0 and every DAG,

    U_g(B,r) = Γ·1[B≥r] + Top_min((B-r)+,n)(w).

One fixed B-unaware policy attains the whole curve: repeatedly prepare JIT and call cheap until r failures have occurred, then prepare JIT and cached-complete every remaining ready job. If B<r no guarded completion occurs. Otherwise entry charges total at most Γ. The r failed read-to-comparison intervals are disjoint, and every subsequent cached mismatch needs another distinct write; at most B-r distinct jobs recompute under protection. This proves the upper curve without observing B or actual costs.

For the lower bound take B≥r and k=min(B-r,n). Fix k heaviest target jobs. The adversary counts cheap failures f, useful cheap invalidating writes c, and for each target whether a cached invalidation write has already occurred. Before f reaches r it rejects every cheap call: write a fresh own-key identity only if its no-write continuation would match; an already-stale call fails without a write. Every target's matching cached completion is invalidated with a fresh identity unless that target is already completed. Fresh or already-stale cached target completion needs no write to protect its whole body. Enforce explicit unconditional caps c≤r, one cached invalidation write per target, and at most r+k **environment input publications** in total. Controller completion publications are not counted in that cap.

On an admitted play the caps never suppress a required rejection: before f=r there are at most r useful cheap writes, and a target's cached operation immediately completes that target. After f=r another cheap call cannot be selected by a universally Q-admissible program. If already stale it fails immediately; if matching, a fresh write in a separate finite continuation can make it fail. In either case r+1 noncompletions together with n mandatory completions exceed n+r. That hypothetical extra write need not occur in the lower-bound execution.

Thus there are no cheap successes on this adversarial play, either before or after f=r. Every job finishes through a guarded operation and contributes its g_i. Every target also protects w_i, by fresh or stale/invalidated cached completion. The bounded finite-write adversary forces completion despite arbitrary free inspections or record retention. Its charge is at least Γ+Top_k and it uses at most r+k≤B environment writes. Nonnegativity settles B<r. The theorem follows.

## Corollary: supplied and hidden budgets separate for any positive total entry charge

At supplied B=r, an informed policy can keep attempting cheap publication until all jobs finish, with at most r failures; its optimal P_g is0. The universal optimum at the same evaluated budget isΓ. Consequently the original body-only equality between informed and universal three-mode protected-work optima fails for every Γ>0, already for one job. At r=B=0, the universal program must guard because it must also survive a larger finite-write environment; an informed zero-budget program may complete cheaply. There is no contradiction with the original theorem, whose L deliberately counts only whole-kernel work.

## Theorem B: informed zero-retry one-write value

For r=0, supplied B=1, let π range over topological orders and C_i^g(π) sum the g_j through job i. Then

    min_P sup_E_1 P_g(P,E) = min_π max_i [C_i^g(π)+w_i].

One may include Γ inside the maximum to expose the no-write branch. It is redundant because the last job has C_i^g=Γ and w_i>0.

Upper bound: follow a fixed topological order with freshly prepared cached completions until its first actual cached mismatch, then prepare/cheap-complete all remaining jobs. A mismatch of a JIT record proves that the sole write has been spent; a mismatch of an arbitrary old record would not. Without a mismatch, only Γ is charged. A mismatch at i incurs C_i^g+w_i and leaves no protection needed. Absorbed or irrelevant writes do not enlarge this bound.

Lower bound: in an arbitrary admitted program's no-write execution, no cheap call can appear. It would fail after a fresh own-gate write, forcing more than n calls to achieve n persistent completions. All no-write completions are guarded and induce a topological order π. Let F contain jobs whose whole bodies execute under protection on this no-write path, **including fresh and already-stale cached completions**. Its no-write charge is Γ+Σ_F w_j. For every i outside F, a separate fresh-write continuation at its matching cached gate forces prefix charge

    C_i^g + Σ_(j in F before i) w_j + w_i.

These are alternative witnesses, not costs on one common execution. Let Hπ(F) be their maximum together with the no-write charge. Remove a job j from F in this lower-bound expression. Existing later terms and the no-write term decrease by w_j. The newly added j term equals the old guarded charge through j and cannot exceed the old no-write total. Repeating gives Hπ(F)≥Hπ(empty). This is an algebraic lower-bound transformation, not replacement of the arbitrary concrete program. Every program is therefore bounded below by the stated expression for its no-write order, matching the upper policy.

The objective is Lawler's inherited precedence-constrained maximum completion-cost problem with p_i=g_i and c_i(t)=t+w_i. Build the order backward by choosing a remaining sink with minimum w_i for the final position; zero g_i are allowed. For independent jobs, a nonincreasing w order is optimal by the usual adjacent exchange. An example is w=(1,10),g=(1,1): light-first costs12, heavy-first11. At g=0 the value is w_max for every order. The original body-only least-total-work choice at its optimum protection corner can instead favor light-first; the resource objectives differ.

## Corroboration and limits

The fixed1809 inputs give26874 universal scalar roots,1809 informed one-write comparisons against all topological orders/Lawler,5427 informed boundary checks and86376 interpreted counter-policy paths, with no discrepancies. These are finite corroboration, not a mechanical proof or new native samples. Full joint W/P_g or W_g/P_g frontiers, least unknown-budget work curves, real guard-price calibration and native minimax transfer remain unclaimed. The native five-policy matrix supplies separate body and guard counts only.

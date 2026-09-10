# Concrete histories, global charges, and a finite policy witness

Expanded proof for manuscript203 Theorem7 and Lemma2, building on the preserved [earlier proof](evidence/RESUMED_20260910_1617/joint_work_general_r_01/PROOF02.md). This concerns the declared body-work interface, not arbitrary lock APIs, positive guard charges, partial kernels or real-time cost. No new measurements or mechanical verification are claimed.

## 1. Operative interface and quantifiers

There are finitely many jobs J with an acyclic predecessor relation and positive works w_i. Write Omega(J)=sum_(i in J) w_i for their total work. An unfinished job is ready precisely when all its predecessors have completed. Each completion saves one immutable result in M; later external writes do not change M or revoke readiness. The objective is a correct saved result for each job under its own operation, not an atomic snapshot of all jobs.

A concrete interface history records the controller's actions, permitted returned values, and completion events. A state contains live own-key identities x, saved completed outputs M, finite raw-snapshot/computed-record storage R, and program-local state ell. Every available computed record has one job, one captured own identity, its exact completed-parent tuple, and one result of that job's opaque kernel. Creating such a record performs the whole kernel at cost w_i. Copies retain that record's capture information and do not authorize retagging it for another identity, parent tuple, or job. Kernel calculations have no live reads or other effects after their operands have been captured. Computation before a job is ready and partial or cross-job discharge are outside this interface. Raw snapshots may be old; computed records are fully charged from the common start, including discarded computations and computed initialization.

At a selected ready-job call, the job and mode are fixed before the environment's gate. A gate is the instant at which the environment supplies a finite word of legal external assignments before the indivisible operation. Any record selection after this call’s gate is restricted to the computed store that existed before that gate. The controller cannot perform even a paid, unprotected preparation after the gate and then use it in the same selected call. A new preparation is a separate action, followed by a later comparison with its own new write gate. The proof below therefore refers to the record selected on a *counterfactual no-write continuation*, not necessarily the record actually selected on a failing branch. Free inspections honestly return the current state; they cannot prevent a following gate write. No clock, work counter, raw hidden cached state, or retained protection is implicitly observable.

The operations are these, all for a ready unfinished job i:

* Prepare a captured own identity and the saved parent tuple: create a record, adding (Q,W,L)=(0,w_i,0).
* Cheap completion: compare the selected record's identity with the live own identity. A match publishes and saves the prepared output; a mismatch does not complete and clears selection, while retained copies remain. Either outcome adds (1,0,0).
* Fresh completion: compute from current own input and saved parents under protection, publish and save its result, adding (1,w_i,w_i).
* Cached completion: under one indivisible protection interval compare the selected record; on match publish/save it, and on mismatch compute/publish/save afresh. The increments are (1,0,0) on match and (1,w_i,w_i) on mismatch. The output and exact comparison Boolean are visible. A mismatch is still one completing call.

All guards end before return. Free local/record actions and inspections neither publish nor finish a job. Every selected operation terminates. Admissibility requires completing every job after finitely many actions on each admitted environment play; an infinite sequence of local/preparation actions is not completion. This is a per-play condition, not a uniform bound on action counts across all environments. Foreground actions cannot change the live own identity of an unfinished job except by a publishing completion, which ends that job. In particular, a local action cannot restore an invalidated identity.

The fresh-write premise is manuscript Lemma1's *record-invalidating* choice: at any finite history and for any selected unfinished target, the environment can install a legal own identity distinct from all target identities already available in its records, snapshots, and history, and never reuse that identity later in the restricted run. This freshness history includes identities in the initial store and old raw snapshots from before the charged interval; starting a cost or write counter does not reset it. The declared supply of legally writable fresh references, together with the finite store/history, justifies this choice in the intended interface. Finiteness of the store alone does not prove that such a legal write is possible. Merely promising a changed identity that might already be in a retained record would be insufficient. The retained-record-invalidating choice is explicit in the manuscript and in the [conditional Java interface proof](JAVA_INTERFACE_PROOF.md). The [earlier Java proof](evidence/RESUMED_20260910_1617/java_refinement_01/OPERATION_TRACE_REFINEMENT_02.md) already requires a new target reference outside preceding snapshots. A mere changed identity is insufficient.

An environment E is in E_b when it makes at most b external assignments along *every* play. A supplied-budget controller P belongs to P_3(B,r) when every E in E_B yields completion with Q<=n+r. A universal controller belongs to U_3(r) when one controller, given no B, has that property for every finite b and every E in E_b. Strategies are deterministic and causal; the environment knows the selected operation and the preceding state/history. The costs below count kernel work, not waiting or all machine instructions.

**Existing target statement, under the preceding interface and fresh-write premise.** For every P in P_3(B,r), there is a finite immediate-preparation policy tree T of depth at most n+r such that

    for every E in E_B there exists E' in E_B:
        (Q,W,L)(T,E) <= (Q,W,L)(P,E') coordinatewise.

The completed jobs in each execution have correct saved results. This is resource dominance, not equality of the two concrete traces or outputs under the same environment. For P in U_3(r), one B-independent T has the same property simultaneously at every finite B. The theorem is existential over admitted programs; it does not claim an algorithm for extracting a tree from arbitrary terminating source code.

## 2. Fixed concrete witnesses define an extraction tree

Fix the initial instance and P, including the supplied B if there is one. Restrict the environment to zero writes at inspections, preparations, and local operations. At a selected comparison, first determine the unique no-write continuation of this concrete history. If it would match, keep two alternatives: no write, or one fresh own-key write. Fix a particular legal fresh identity at each such concrete node once and for all. If it would already mismatch, keep only the no-write continuation. At fresh calls keep only no write.

These rules determine a *tree of concrete executions of P*. Each node's complete witness history fixes all intervening inspections, captured values, records, local actions, and P's next choice. Alternative comparison outcomes give different child witness histories. A future real execution of T will not replay P's local choices on its new values; it will follow the already fixed node labels. Thus no equivalence between two arbitrary histories with the same completed set is assumed.

Project this concrete tree as follows. A fresh call becomes a unary fresh node. A no-write-matching cached call becomes a binary cached node with two completing children. A no-write-matching cheap call becomes a binary cheap node with one completing child and one failure child. A cached call already stale without a write becomes a unary fresh node, retaining its concrete zero-write continuation. An already-stale cheap call is deleted and its concrete failing continuation is followed. Intervening preparations and local actions are recorded only in the witness histories and disappear from T. Readiness is preserved because every retained node completes exactly the same job as its concrete original counterpart, and deleted calls complete none.

Call a retained binary cheap failure useful and write H for the multiset of such failures on a path. Write D for the jobs completed at retained binary cached mismatches. Let s count deleted stale cheap failures, u completed jobs, and h retained cheap failures in a prefix. The original uses u+h+s calls and the projected prefix uses u+h. In particular, deletion consumes none of T's remaining allowance and can never require adding replacement failures.

For a supplied budget, construct this tree only until B selected fresh writes have occurred; the continuation after that point will be replaced below. For a universal controller, use an unconditional extraction cap K=n+r. Every path prefix in either construction is a concrete execution under an environment in E_B or E_K respectively: its selected fresh writes never exceed the cap, and all further writes can be stopped. Original admissibility therefore excludes more than n+r counted calls on any such prefix, as well as endless intervening free/preparation actions. Deleted stale calls are counted in this argument. Finite branching and depth at most n+r of retained calls give a finite projected tree. In the universal construction, a hypothetical nonterminal leaf at depth K would require more than K completing/call nodes, contradicting admissibility under the bounded restricted environment. No new useful comparison write is needed after the Kth counted call.

## 3. Global distinct-charge lemma

Consider a complete restricted concrete execution, including any eventual no-write continuation of a supplied-budget cut. At a useful comparison with no-write matching continuation, let rho be the computed record that the no-write outcome of this same selected comparison would select; this does not scan forward to a later call. Its capture identity equals the pre-gate live identity. The kernel calculation creating rho has already completed before the write decision. Its work is thus present on the fresh-write branch too, even if that branch selects a different retained record.

The fresh write removes rho's captured identity from the target's future live identities while the job is unfinished. The restricted environment never restores it, and no foreground action restores an unfinished job's old identity: cheap failure does not publish; inspections, local actions and preparation do not publish; a publishing completion ends the job. Consequently, the record charged at a later useful failure of this job has a different capture identity and was created by a distinct kernel calculation. Copies and equal result values cannot merge these calculations because records cannot be retagged.

For each job, its final completion incurs a further distinct whole-kernel calculation. A matching completion uses a record for the then-live identity; that identity differs from all records invalidated at earlier useful failures. A fresh or cached-mismatching completion performs its own protected calculation. At a useful cached mismatch, the already-paid counterfactual matching record and the protected completing calculation are distinct as well. Calculations assigned to different jobs are distinct by the whole-kernel/no-sharing contract.

Choose one such final calculation per job as its mandatory w_i charge. Additionally choose one invalidated pre-gate calculation per useful cheap failure and one pre-gate calculation per useful cached mismatch. These chosen calculation instances are pairwise distinct. Other computations, stale calls, discarded results and duplicate preparations may add work but are not needed for the lower bound. For a collapsed stale cached call, its protected completing computation supplies the mandatory job charge; any prior stale preparation is unused slack in this inequality, not another mandatory charge. Therefore, from the common start,

    W_P >= Omega(J) + sum_(h in H) w_i(h) + sum_(i in D) w_i.

Every projected fresh node is either an original fresh call or a stale cached call; both protect its whole kernel. Every binary cached mismatch also protects its completing kernel. These are distinct original completing calls, hence

    L_P >= sum_(projected fresh nodes) w_i + sum_(i in D) w_i.

This is a complete-execution charge. It never asserts that an arbitrary suffix owes fresh work Omega(S): some eventual completing records may already have been paid for before the suffix. That distinction is what permits early preparations and retained records.

## 4. The supplied-zero-budget suffix

At a cut following B selected fresh writes, retain the original concrete prefix and continue P with no additional writes. This is a globally B-bounded original environment, so P finishes all remaining jobs within its original total n+r call cap. Replace the projected continuation by a fixed topological order of the unfinished jobs, preparing and cached-completing each immediately.

On a real execution of this replacement, the B preceding binary bad outcomes require at least B distinct actual writes. In an environment in E_B the budget is therefore exhausted. Every immediate preparation/cached completion in the replacement suffix matches. It uses exactly n-u further calls and zero protected kernel work. Original P needs at least n-u completing calls after its prefix; with u+h+s already used, Q_P >= n+h+s >= n+h = Q_T.

The replacement suffix computes the remaining kernels, but the global lemma already reserves one mandatory calculation per job in the *entire* original execution. All extra charges assigned to H and D lie in the retained prefix and are distinct from the mandatory calculations, even when an original suffix completion reuses an early record. Hence the replacement's complete W remains no larger than the lemma's original lower bound. Its zero protected suffix adds nothing to the projected fresh/mismatch lower bound for L_P. This proves all three resource comparisons without a false per-suffix charging claim. For B=0 the argument applies at the root.

## 5. Realizing the labels as one operational policy

The emitted policy stores its current tree node. At a fresh node it calls fresh on the labeled ready job. At a cached or cheap node it captures the job's current own input and exact saved parents, performs exactly one immediate preparation, and invokes that mode. It follows the child named by the actual returned comparison/success bit. Job choice depends on the finite node label, not on the new concrete data values. The completed-set argument above ensures readiness on every node; the primitive contract ensures a correct saved result for the actual operands. The supplied cut tail is as in Section4. The universal tree has no supplied-budget cut or B-dependent action.

Because preparation and comparison concern the same job and no intervening foreground action changes that key, each actual cheap failure or cached mismatch needs at least one external own-key write in that preparation-to-comparison interval. The selected operations are sequential, so these intervals are disjoint. A path with d=|H|+|D| binary bad outcomes therefore needs at least d actual writes. Irrelevant writes, repeated identities and multiple writes in one interval do not weaken this injection. Every actual tree path in E_B has d<=B, and it has at most n+r calls.

For each complete tree path the policy's actual costs are exactly

    Q_T = n + |H|,
    W_T = Omega(J) + sum_H w_i(h) + sum_D w_i,
    L_T = sum_(fresh nodes) w_i + sum_D w_i.

Every kernel is prepared exactly once for a matching/cheap/cached node; each failure duplicates the unfinished job's mandatory computation and each cached mismatch duplicates its completing computation. Fresh nodes compute once under protection. These formulas are independent of the values seen on that path.

## 6. Matching every path to an unconditional bounded environment

Take an actual T execution and its path. Reconstruct P's already-fixed concrete witness by taking exactly the selected fresh-write branch at each binary bad node and the no-write branch at each good node. At collapsed/deleted calls use their fixed zero-write continuations. At a supplied cut, use the original P no-write continuation from Section4. This yields d=|H|+|D| writes, exactly one per binary bad node, and the same retained labels H,D and original protected completions corresponding to projected fresh nodes (including collapsed stale cached calls).

Define E' to follow these prescribed writes when P's history is the corresponding concrete witness prefix. On any off-witness history it can stop writing; in every case impose an unconditional cap d. This is a strategy in E_d on *every* play, not merely a strategy whose one observed play happened to use d writes. Determinism reproduces the selected witness prefixes, and stopping on off-witness histories does not change that execution. Since d<=B, E' is in E_B. It finishes by admissibility.

Its original call count is at least n+|H|, including any deleted cheap failures. The two inequalities of Section3, with Section4 at a cut, dominate the exact W_T,L_T formulas. Thus this E' proves the target coordinatewise comparison. Different actual paths may use different witnesses E'; this is exactly the stated universal-existential quantifier and implies dominance of the separate worst-resource maxima. There is no assertion that one global E' simultaneously witnesses every real environment.

For a universal P, the construction used K=n+r only to build a finite tree, and its node choices are independent of B. An actual path at any finite B still has d<=min(B,K), and the same reconstruction belongs to E_d. Therefore the *same* T works simultaneously for all B. The theorem says no more about the existence of a least total-work curve among all optimal-protection policies; that is the separate independent-job theorem.

## 7. Boundary of the claim

The record-invalidating supply includes old raw snapshots. Optional post-gate selection is restricted to the already-computed store; a new preparation cannot occur after this call's gate for use in that same call, even if it pays its kernel cost. The [conditional Java proof](JAVA_INTERFACE_PROOF.md) separately treats completed-operation trace normalization and its limits; no instruction-level JMM equivalence follows from this abstract proof. These are premises of the stated result, not consequences of finite testing.

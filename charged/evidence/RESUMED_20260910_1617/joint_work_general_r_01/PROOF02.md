# Whole-program joint-resource domination with arbitrary retry slack

Author derivation, September10,2026. This extends the corrected r0 proof, preserving the original statement that the extension was then unproved. AUTHOR_GODEL_FINAL01 is a read-only author check, not independent closure. Claude GENERAL05 remains pending. All greedy-rule counterexamples, retained-preparation checks and finite-root singleton observations remain distinct from this symbolic proof.

## Contract and quantifiers

Use manuscript165 Section2's whole-kernel interface with explicit cached comparison Boolean, positive fixed wi, finite DAG, permanent completed outputs and exact immutable predecessor tuples. Begin before computed initialization and charge every preparation or replacement computation to W. Raw old snapshots may be given and records copied, but computed records cannot be fabricated or retagged without their kernel calculation. Before completion the foreground does not write that job's live key: failed cheap does not publish, and inspections/preparations/local operations do not publish. Pure kernels have no live interactions. The job/mode is fixed before the write gate; any later record selection uses only the already-computed store. Any such post-gate selection may vary with permitted local information, so the charging below must use the counterfactual matching record. The primitive returns its promised output/flag; no implicit clocks or W/L observations are supplied.

For every known-budget admissible P in P3(B,r), there is a finite immediate-preparation tree T with Q<=n+r such that each T execution in E_B has an original P execution in E_B with componentwise at least its Q,W,L. For every universal P in U3(r), there is one B-independent finite tree T for which that statement holds simultaneously for every B>=0. The comparison is to some globally budget-bounded original environment, not trace equivalence in the same environment. Hence both separate worst-resource suprema of T are no larger. This does not by itself assert that one tree attains every pointwise minimum W over the class of universal optimal-L policies.

## Extraction from concrete histories

Restrict the adversary to no writes except optionally one fresh own-key identity at a comparison whose zero-write continuation matches. Fix the fresh identity at every concrete branch history. A fresh call gives a unary fresh node. A zero-write-matching cached call gives two completing children; a zero-write-matching cheap call gives completion or fresh-write failure. A cached call already stale without a write is replaced by a unary fresh node keeping its original zero-write continuation. An already-stale cheap call is deleted, also keeping that original failing continuation, including its program-local choices in the fixed witness history. No costful local action or stale call needs to be reproduced by T; T is a resource-improving functional policy, not a simulation of P's internal state.

If an original prefix has u completions, h retained binary cheap failures and s deleted stale-cheap failures, its call count is u+h+s, whereas T has u+h. The original remaining failure allowance r-h-s is at most T's allowance a=r-h. Unused allowance is permitted; there is no obligation to introduce extra calls after deleting one. All retained paths therefore have at most n+r nodes. Every sequence of free/preparation actions and deleted stale calls between retained nodes is finite: otherwise the original program would fail to complete after the environment stops writing, contradicting its finite-budget admissibility. Finite binary branching and bounded retained depth give a finite tree, despite arbitrary local state and values in the full language.

For a supplied B truncate on B selected fresh writes and replace the remaining continuation by a ready immediate prepare/cached suffix. For a universal P, extract all branches with an unconditional cap K=n+r and do not perform a known-budget suffix substitution. Before n+r counted calls an additional useful comparison write never requires more than K writes; at depth K admissibility requires completion. This finite construction consequently retains all useful outcome branches of every T path.

## Global per-version charging

Immediately before a useful comparison, identify the computed record rho that the zero-write continuation would select and match. Its captured identity is the current identity. Its kernel calculation already occurred before the adversary's gate move, so the corresponding cost is also present on the fresh-write branch, even if that branch actually selects a different older record. Charging only the record actually selected on failure would be unjustified and is unnecessary.

Each binary cheap failure makes that rho's captured identity permanently unavailable as a live identity on the restricted path. The restricted adversary uses a never-before-used identity; until the job completes, no foreground operation restores an earlier identity. A later zero-write-matching comparison of that same unfinished job therefore uses a record for a different identity and requires a distinct kernel calculation. Copies of an old record do not create an exception. Every job's final completion needs an additional distinct calculation: either its protected completing kernel or its matching preparation for the then-current identity. At a binary cached mismatch the zero-write-matching preparation and the protected completing calculation are also distinct. Charges for different jobs cannot share opaque whole-kernel work.

Let H be the multiset of binary cheap failures and D the set of binary cached-mismatch jobs on a complete extracted path. The corresponding full original execution satisfies

    W_P >= Omega + sum_(h in H) w_i(h) + sum_(i in D) wi.

Its protected work is at least the sum of the extracted fresh-node works and binary cached-mismatch works. A collapsed stale cached call already protects its wi; discarded stale cheap calls cannot make L smaller in the original. This proof charges the entire execution from the common start; it does not claim that an arbitrary original suffix owes a fresh Omega(S), since that suffix may reuse prepaid records. Replacing a known-b=0 suffix retains the mandatory global charge and can only reduce protected work.

## Realization and globally bounded witnesses

At each selected cheap/cached node, T prepares exactly once immediately before that call; at fresh nodes it performs no preparation. The choices depend on the fixed witness node, completed set and returned operation flag, not current kernel values or writer state. Every selected job remains ready, and correct actual outputs follow from the primitive semantics using actual current inputs and saved completed parents.

Every actual cheap failure or cached mismatch needs an own-key write in that node's preparation-to-comparison interval. These intervals are disjoint, so d=|H|+|D| is at most the actual number of writes. Conversely exactly d fresh own-gate writes realize each complete tree path. Extra writes may be irrelevant, hidden or identity-reusing; they do not invalidate the injection. On the path,

    Q_T = n+|H|,
    W_T = Omega+sum_H wi+sum_D wi,
    L_T = sum_(fresh nodes) wi+sum_D wi.

The original concrete witness can be generated by the restricted gate choices and an environment with an unconditional cap d; on every other history stop writing at that same cap. This preserves the witness path and is globally d-bounded, rather than merely using d writes accidentally on one play. Thus an actual T execution with at most B writes is matched to an original P execution under an environment in E_d subset E_B. This proves the supplied-budget and simultaneous-all-B domination statements, including Q. Universal T's useful-write curves saturate by K=n+r.

## Exact supplied-budget Pareto recurrence

Let F(S,b,a) denote attainable nondominated suffix-tree bounds (e,l), where e=max W-Omega(S), l=max L, and a is the remaining noncompletion allowance. This indexes bounds and tree witnesses, not an equivalence of arbitrary original histories. Bases are F(empty,b,a)=F(S,0,a)={(0,0)}. For b>0, ready i, R=S-i:

* Fresh: (e,wi+l) from F(R,b,a).
* Cached: (max(e0,wi+e1),max(l0,wi+l1)), choosing child0 in F(R,b,a) and child1 in F(R,b-1,a) independently.
* Cheap, only if a>0: (max(e0,wi+e1),max(l0,l1)), choosing child0 in F(R,b,a) and child1 in F(S,b-1,a-1).

Take the nondominated union over all choices. Cheap failure's preparation is an extra wi because its job remains unfinished and still needs its mandatory eventual kernel; that failure adds no protected kernel work. A completed cached mismatch duplicates that job's mandatory kernel. The branches give separate worst W and L, possibly at different leaves. Dominated child bounds may be removed because every parent combination is coordinatewise monotone. Modes/outcomes, fixed wi and S determine future readiness and charges for these trees, while an actual emitted policy retains its selected witness node. There are at most(r+1)(min(B,n+r)+1)2^n states, with possibly exponential frontier sizes. The known B=1,r0 Lawler reduction remains the stated polynomial special case; no general fixed-order theorem follows. This is inherited Pareto backward induction applied to the proved finite class.

## Complete universal-optimal-L curve enumeration

Write Lambda_r(B)=Top_max(B-r,0)(J), using the ORIGINAL entire job set J. A universal canonical tree satisfies L<=Lambda_r(B) for every B iff every leaf with d useful writes has L_leaf<=Lambda_r(d). Necessity uses its exactly d-write realization; sufficiency uses monotonicity and d<=actual writes<=B. The prefix guard ell<=Lambda_r(d) is necessary because the adversary can stop all further writes, after which L cannot decrease. Checking it only at a nonterminal prefix is not a substitute for a complete feasible continuation.

For curve enumeration a state (S,a,d,ell) records unfinished jobs, remaining failures, useful writes already observed, and protected work used. Reject precisely the guard violation. An empty S has zero remaining extra-W curve. Fresh decreases S and adds wi to ell. Cached joins a matching child(S-i,a,d,ell) and mismatching child(S-i,a,d+1,ell+wi); cheap joins matching completion with failure(S,a-1,d+1,ell) if a>0. A comparison's future extra-W vector is c[0]=c0[0] and c[k]=max(c0[k],wi+c1[k-1]) for k>=1. Fresh copies its child's extra-W vector. Retain all coordinatewise nondominated vectors and concrete witnesses. Coordinates B=0,...,n+r cover all root budgets; further coordinates saturate. Induction plus the domination theorem makes this a complete finite characterization of the unrestricted universal optimal-L class, although the enumeration may be exponential and general singleton-root optimality remains unresolved.

## Corroboration and unresolved claims

FINITE_PROTOCOL01's first execution compared retained-preparation and canonical games in96,795 cases and preserved all successes and hashes. UNKNOWN_PROTOCOL02's first execution checked713 roots and independently interpreted10,932 witness paths; every root frontier was singleton, all237r0 curves agreed with the prior theorem and both old chain fixtures were retained. These checks do not prove the unrestricted reduction, general root uniqueness or FSE merit. No native general-r execution or final manuscript adoption has yet occurred. The original36/39-stage artifacts, old manuscript163 and its Reject/borderline-Major-Revision critique remain unchanged.

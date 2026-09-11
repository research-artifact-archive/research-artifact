# Exact residual safety and an online mode filter

Author proof, 2026-09-11. This elaborates immutable HYPOTHESIS01 after its fixed bounded check01. It is not a certification by the checker or by an external model. No manuscript claim has yet been changed. The explicit residual-game quantifiers are essential.

## 1. Interface and local obligation

Let J be any finite set of jobs with fixed positive whole-kernel works w_i, and a DAG. At an operation boundary let D be its completed ideal and S=J\D. Outputs in D persist. Let ell>=0 be protected work already incurred and k>=0 an integer credit. Write T_t(A) for the sum of the min(max(t,0),|A|) largest weights in A. The weights may be positive reals; algorithmic bounds below count arithmetic/comparison operations. An implementation with integers must separately account for bit lengths.

A residual policy receives the completed history and may choose any ready job and one of two completing modes, in finite time. Fresh performs exactly one protected kernel, with total/protected work (w_i,w_i). Cached first captures the CURRENT own-key identity and immediately executes the whole kernel on that capture and saved parents; then its terminating completion compares under a call-local guard, reusing on a match and recomputing protectively otherwise. Its costs are (w_i,0) or (2w_i,w_i). Preparation is paid; none is done when choosing fresh. Each job completes once; no cheap failures, retained guards, extra preparations, partial repair or live-parent rereads occur in this residual class. No cached mismatch is possible without a write after its current capture. Different calls' relevant intervals are disjoint. Cached results are observable. Additional harmless writes are permitted.

Define local residual viability by the existence of ONE causal completion policy satisfying, for every b>=0 and every future environment with an unconditional at-most-b write bound on every play,

    ell + L_future <= T_(k+b)(J).                            (R0)

The same policy must satisfy all b. This definition does not claim k equals the actual hidden prefix-write count or exhausts all knowledge conveyed by that prefix. In particular R0 may be stronger than the original global obligation at a history that proves additional harmless writes occurred.

## 2. Exact viability

The following are equivalent:

(a) some residual policy satisfies R0;
(b) immediate cached completion in ANY causal ready order satisfies R0;
(c) ell + T_m(S) <= T_(k+m)(J) for all integers 0<=m<=|S|;
(d) ell <= T_k(D).

(b)=>(a) is immediate. For (c)=>(b), in a suffix with at most b writes at most min(b,|S|) distinct cached jobs mismatch, costing at most T_b(S) protectively. Apply (c) at m=min(b,|S|), and monotonicity of the right side if b>|S|.

For (a)=>(c), fix m and a set H of the m largest unfinished jobs before execution. A writer has one slot per target in H, used only if that target selects cached, placing a fresh own identity after its current preparation and before comparison. A slot is never used twice, and no other write is made. On EVERY play this writer spends at most m writes, independently of termination or whether the policy obeys its specification. A target selecting fresh already protects w_i without consuming its slot; a target selecting cached is forced to protect w_i. Completion is part of admissibility and forces all targets to finish, including target predecessors, which are counted once. Thus the play incurs at least ell+T_m(S). R0 at b=m implies (c). The writer need not spend exactly m writes; its unconditional cap is what R0 quantifies over. For m=0 the no-write environment gives the same argument with the empty target set.

For (c)<=>(d), the following sorted-union identity holds:

    min_(0<=m<=|S|) {T_(k+m)(D union S)-T_m(S)} = T_k(D).     (I)

Union the largest min(k,|D|) jobs of D and largest m jobs of S. Their cardinality is at most k+m, proving the left side is at least T_k(D). Equality: k=0 uses m=0. If 1<=k<=|D|, fix a total descending weight order with deterministic tie breaking, and let m be the number of S jobs preceding the kth D job. The first k+m jobs are exactly the largest k D jobs and largest m S jobs. If k>|D|, use m=|S|. This handles ties and all clamping boundaries. Applying I to (c) proves the equivalence.

## 3. All permissible next modes

In a viable state, all ready cached choices retain a viable successor on both outcomes. A match enlarges D without changing k or ell. A mismatch adds i to D, increases k by one and adds w_i to ell; the inequality

    T_(k+1)(D+i) >= T_k(D)+w_i

follows by selecting i plus the largest min(k,|D|) old jobs. Hence cached is always an available fallback.

A ready fresh i has the successor (D+i,k,ell+w_i). By the equivalence just proved it retains some viable continuation if and only if

    ell+w_i <= T_k(D+i).                                   (F)

Thus F with always-available cached choices is precisely the maximally permissive action filter for R0 in this class. This is a statement about which modes can retain the protection contract, not which safe mode minimizes total work. Future cheap calls, non-current preparations, hidden resource observations, retained guards and partial kernels are not silently included in the class.

Necessity for fresh could also be read directly from the rejecting successor's finite target adversary in Section2. The existence of a counter-writer depends on the fixed program but is not an assumption that the writer can see hidden program state at runtime: its future action depends only on the already selected public job/mode, with H fixed in advance.

## 4. Original completion contract

Take any common current-prepared cheap controller that either completes all jobs or stops at r cheap failures, selecting a ready target in finite time. At that switch, let D include ALL cheaply completed jobs, set k=0 and ell=0, and run the filter above. The initial state is viable because T_0(D)=0.

There are at most r noncompleting calls and n completing calls. Each cheap failure and each subsequent cached mismatch requires a separate actual write, so at a suffix boundary r+k<=B whenever the actual total writer budget is at most B. The invariant gives

    Q<=n+r,   ell<=T_k(D)<=T_k(J)<=T_((B-r)+)(J).

If completion occurs before the switch, ell=0. This proves the optimal protection curve already lower-bounded for general programs in the manuscript. The filter uses observable mode/results and declared works, not B or resource instrumentation.

For total work the exact-prefix domination proof from the earlier safe_fresh_suffix_01/PROOF01 applies verbatim to ANY current-prepared completing fresh/cached suffix, irrespective of its fresh guard. For a concrete play retain all b0 actual prefix writes, not merely r. If its suffix mismatches are H, an all-cached continuation can instead mismatch the |H| heaviest remaining jobs using |H| slots and the identical prefix. It costs at least as much with an unconditional b0+|H|<=B write cap. Consequently the filtered policy's worst W is no larger than the common cheap controller followed by all-cache completion, even if the ready orders differ. This proves domination against this comparator only, not global DAG work optimality or a pathwise dominance coupling.

For independent jobs with ascending cheap order, the manuscript's general-program lower bound and this domination imply the filtered policy retains the least entire W curve, for ANY ready choices in the suffix. The same applies for any DAG at r=0. Those lower bounds are inherited results, not a new lower-bound proof here.

## 5. Online implementation and unknown future jobs

Maintain k, ell, a min-heap H of the largest min(k,|D|) completed weights, their sum s, and a max-heap R of the remaining completed weights. For a proposed weight w, compute T_k(D+w) without mutation:

* k=0: 0;
* |H|<k: s+w;
* otherwise: s+max(0,w-min(H)).

This requires O(1) arithmetic/comparison operations. On completion, insert its weight into the appropriate heap and rebalance; on a cached mismatch increment k first and move the largest remaining old weight to H if available, then insert. The target heap size changes by at most one for each of those two events, so an update needs O(log(|D|+1)) operations and O(|D|) memory. The mode query itself does not sort unfinished jobs or enumerate a game. Initialization from arbitrary D takes O(|D| log(|D|+1)) with insertion, or can be optimized by selection/heapify; no optimized initialization bound is claimed for the implementation before it is checked.

No unfinished weight or edge enters F. Thus the SAME filter can be used when future jobs and their weights are not known, as long as jobs have fixed positive works when chosen, completed outputs persist, readiness is sound, and each considered execution ends after finitely many jobs and finite dispatch choices. For every finite realized final J the invariant proves the above Q/L bounds retrospectively. If infinitely many jobs arrive or dispatch never terminates, this argument supplies a prefix invariant, not finite completion. This corollary concerns safety under future-input uncertainty; it does not provide an optimal work curve under adaptive job release or alter the current paper's fixed-J lower bounds.

## 6. Attribution and limitations

Cardinality-budget top-weight sums and their efficient evaluation are inherited robust-optimization mathematics. The general use of winning regions to permit safe actions is inherited safety-game/shielding methodology. The candidate contribution is the exact closed-form winning region and its operational necessity/online enforcement for this particular all-future-budget completion contract. Whether that specialization is sufficiently important for FSE depends on nearest-source comparison and a substantive software design question. Small-state agreement is corroboration, not this proof. The previous negative Linux/Roslyn/Valkey results and the unconfirmed real-client resource contract remain in force.

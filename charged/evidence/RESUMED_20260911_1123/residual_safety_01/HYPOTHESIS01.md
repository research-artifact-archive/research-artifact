# Exact residual protection safety candidate (pre-experiment)

This new author derivation follows the general sufficient SF theorem in the previous session. No new numerical experiment has been run. Definitions below concern a residual game, not arbitrary information-rich histories under a possibly larger hidden write count. Do not infer all-program necessity at every original history merely from k observed mismatches.

Let J be a finite positive-weight job set, D completed jobs, S=J\D unfinished jobs in any fixed DAG with persistent completed outputs. Let k>=0 be a credited mismatch count, ell>=0 current protected work, and G_j=Top_j(J), clamped to the set size. Only completing fresh and immediately CURRENT-prepared cached calls remain; each ready job completes once. Each cached mismatch requires a new actual write in its read-to-comparison interval. For every future suffix write budget b, require final protected work <=G_(k+b). This residual contract is an explicit local obligation, potentially stronger than the original global contract at an information-rich history with extra inferable writes. Pure whole-kernel constant weights, no retained guards/partial reuse, finite ready choices and operation termination are assumed.

Candidate A (all-cache safety): completing every remaining job cached in any ready order satisfies that residual contract iff

    ell + Top_m(S) <= G_(k+m) for every integer0<=m<=|S|.       (R)

Sufficiency: at most b cached jobs mismatch, so protection is ell+sum their weights<=ell+Top_b(S)<=G_(k+b); clamp if b>|S|. Necessity for ANY fresh/cache policy: select a set H of the m heaviest remaining jobs, and write once at each target in H only if it selects cached; fresh targets already contribute their full weight. All H must complete, so final protection>=ell+Top_m(S); there are at most m one-use write slots, globally capped on every play. If R fails at m, this contradicts the b=m bound. This adversary also covers history-dependent ready order and observed cached flags. No attempt is made to make the witness spend exactly m writes when a target is fresh. Selected operations always terminate, and finite choices plus persistent completion force every selected H target eventually to complete.

Candidate B (sorted-union identity): for disjoint D,S and integerk>=0,

    min_(0<=m<=|S|) [Top_(k+m)(D union S)-Top_m(S)] = Top_k(D). (I)

One direction follows by unioning the k largest D weights and m largest S weights; when k>|D| use allD and clamp. For k<=|D|, pick m equal to the number of S weights ahead of the k-th D weight in a fixed global nonincreasing total order, breaking ties by ID. Then the first k+m jobs are exactly the selected kD and mS, yielding equality. k0 uses m0; k>|D| uses m=|S|. Thus R is equivalent to

    ell <= Top_k(D).                                        (C)

Candidate C (maximally permissive local mode filter): in a safe state C, every ready cached call is safe on both results; a fresh completion of i is permitted iff

    ell+w_i <= Top_k(D union {i}).                          (F)

After cached match, D grows and ell,k are unchanged, preserving C. After cached mismatch, ell'=ell+w_i and k'=k+1, and Top_(k+1)(D+i)>=Top_k(D)+w_i, preserving C. Fresh keeps k and grows ell by w_i, so F is exactly C at the successor. Necessity of C for any residual completion policy makes F necessary, not merely sufficient, for retaining some residual-contract continuation. It does not optimize W or assert that every permitted fresh choice is W-optimal.

Candidate D (original guarantee): apply the filter after any common immediate-cheap phase that completes or ends at r failures. At the switch k0,ell0 and C holds. Maintain k as only observed suffix cached mismatches. Each bad comparison needs its own write, so at most B total actual writes implies r+k<=B. At all suffix boundaries C yields ell<=Top_k(D)<=Top_k(J)<=G_((B-r)+). Q<=n+r holds. Exact-prefix worst-W domination over the same cheap phase followed by all-cached completion is inherited verbatim from previous SF/PROOF01, including harmless prefix writes; it does not depend on the particular fresh safety guard. No original-history all-program necessity is claimed without a minimal-write-realizability argument.

The filter requires only completed weights, credited k, ell and the selected ready job's weight. Future-job weights and the full remaining DAG are unnecessary for the safety decision. A data structure for dynamic top-k sums could implement it without a policy tree; precise costs and a standalone implementation remain to be checked. The local Top_k calculation/cardinality robustness is inherited mathematics. Potential novelty is the complete operational safety characterization plus inference-free online enforcement in this completion contract, not sorting itself.

A proposed strict-permissiveness witness (not executed): chain weights100,1,2,80,80,80 with r1. Complete100 cheaply with match; fail cheap1; cached1 mismatches. Then D={100,1},k1,ell1 and next weight2. F allows fresh2 since3<=Top1({100,1,2})=100. Old SF refuses because ell+remainingWork=243>globalTop2=180. This is a reachable decision difference, not proof of a better worst-W curve or representative effectiveness. Preserve it even if overall worst curves coincide.

Falsifiers: any finite residual state where exact backward safety disagrees with C; any action where F disagrees with exact viable successors; sorted-union identity failure; an operational no-new-write mismatch under current preparation; original Q/L violation under the filter; or a hidden-write/side-channel construction invalidating any attempted broader necessity claim. Importance additionally fails if closest primary work directly yields the same returned decision procedure/contract or the software API assumptions are irrelevant to the claimed design problem.

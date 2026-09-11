# A sharp work guarantee for every caller of the body residual filter
Author derivation, 2026-09-11T05:41:02.078881+00:00. Not yet paper-adopted or independently certified. Uses inherited results explicitly; no new greedy ordering theorem is claimed.

## Contract and quantified comparison
Let J be a nonempty finite DAG with positive whole-kernel works w_i; Omega=sum_J w_i, M=max_J w_i. Keep the paper's immediate capture/preparation, per-job persistent outputs, own-key write gates, atomic completing actions, release-on-return, and finite selected-operation assumptions. Fixed integer r>=0 is the maximum extra failed-call allowance; B>=0 is an integer environment budget and is never supplied to the caller.

V_r is the FULL paper class of causal deterministic general programs guaranteeing completion, Q<=n+r, and L<=Top_(b-r)+(J) simultaneously for every finite b and unconditionally b-capped environment. Programs in V_r can inspect, retain records and prepare early; their kernel work is charged from the common start.
F_DAG(B)=inf_(P in V_r) sup_(E in E_B) W(P,E).
The class is nonempty because cheap-then-all-cached is admissible. Each F is finite and at least Omega; no single policy attaining all these infima is assumed.

Let A_r be the caller class:
1. While fewer than r cheap failures have occurred and jobs remain, choose any ready unfinished job and perform exactly one current capture/preparation and cheap call.
2. After r failures, make only ready fresh/cached completions permitted by the exact body residual filter, beginning with D=cheap-completed jobs, k=ell=0. Cached completion has exactly one current preparation.
3. Choices are causal and may depend on observations and prior outcomes, but not B; each choice terminates. No other paid preparation, post-threshold cheap calls, retained guards or partial kernels occur.
The ordering need not be fixed and no future weight/edge is required by the filter. Readiness and finite choice remain caller obligations.

## Membership and exact operation accounting
Every call either completes a new job or is one of at most r failed cheap calls. Hence Q<=n+r, and the finite DAG plus finite selections gives termination. After the switch, the exact filter maintains ell<=Top_k(D). Every failed cheap call and every cached mismatch contains at least one write in its own disjoint current-capture/comparison interval. Thus k<=max(B-r,0), so final L<=Top_(B-r)+(J). Before switching L=0. Therefore every caller in A_r belongs to V_r.

For each complete concrete play,
 W = Omega + sum_(failed cheap calls) w_i + sum_(cached mismatches) w_i.
The mandatory Omega pays each job's completing body once. A failed cheap call adds its preparation; a cached mismatch adds its protected reexecution. Fresh adds no speculative body. There are no other kernels in A_r. This identity does not hold for arbitrary V_r programs; only the lower bound below uses the full class.

For B<=r, no cached mismatch can occur after r failed calls, and at most B cheap calls fail. Thus W_A(B)<=Omega+B M.
For B>r, set m=min(B-r,n), T=Top_m(J). There are at most r failed cheap calls and at most m distinct mismatching cached jobs, so
 W_A(B)<=Omega+r M+T.  (U)
No premise on the ordering was used.

## Full-program lower bound and where DAG readiness enters
The paper's useful-write charging lemma and capped-play lemma imply, for every DAG,
 F_DAG(B)>=Omega+B M for B<=r,
 F_DAG(B)>=Omega+H for B>r,
 H=max_(1<=s<=min(B-r,n)) [r a_(n-s+1)+Top_s(J)],
where a sorts all job works increasingly. These are the lower bounds used in the independent-jobs theorem; independence is used for its attaining policy, not this lower construction.

For completeness, target the s heaviest jobs. At a target comparison whose zero-write continuation would match, write a fresh own-key identity. Count useful cheap failures f, useful cached mismatches c and all target completions t. Stop forever at f=r+1 or t=s. Before a write, f<=r and t<=s-1, hence the write count after it is at most f+t+1<=r+s. This is one unconditionally (r+s)-capped causal environment, including on inadmissible programs.
A V_r program cannot incur r+1 cheap failures under its call cap and must eventually complete every target. DAG predecessors may delay readiness, but the globally capped environment admits the whole program and thus forces completion of those predecessors too. No target-readiness scheduling assumption or dependency deletion is used.
No target comparison can match before the last target completes; a would-be match is invalidated, and an already-stale comparison fails or completes protectively. All target bodies are protected, giving L>=Top_s(J). At the realized final write count d=f+c<=r+s, capped-play safety gives L<=Top_(d-r)+(J). Positive works force d=r+s, f=r, c=s. Thus all target completions are useful cached mismatches. The distinct-kernel charging lemma yields mandatory Omega plus r failed preparations of work at least a_(n-s+1), plus all s target works. Extra observations, stale failures, early preparation and retained records cannot erase these charged invocations.
For early budgets, take s=1 and truncate this concrete environment after the completed call containing the Bth useful write, for B<=r (at B0 keep the empty prefix). Its unchanged prefix has destroyed B distinct paid preparations of the still-unfinished maximum job. Finite completion requires another distinct mandatory kernel. Again use an unconditional B cap on every play, not a budget informed policy. At B0 mandatory Omega suffices.
This is a repeated proof exposition of the inherited lower, not a new experimental result.

## Uniform approximation theorem
For every A in A_r and every B,
 W_A(B)<=alpha_r F_DAG(B),  alpha_r=(3r+2)/(2r+2).
At r0, all such callers are exact for all B. At B<=r+1, all are exact for every r. For r>=1 the factor is strictly below3/2; at r1 it is5/4.

Proof: early budgets match the lower. At r0 (U) is Omega+Top_B and the lower matches. For r>=1,B>r, H>=(r+1)M by s1 and H>=T by sm. Write x=T/M>=1 and z=Omega/M>=x. Then
 W_A/F_DAG <= (z+r+x)/(z+max(r+1,x)).
The ratio is nonincreasing in z, since r+x>=max(r+1,x). Replace z by x. On 1<=x<=r+1, (2x+r)/(x+r+1) is increasing; on x>=r+1, 1+r/(2x) is decreasing. Both meet at alpha_r. No infimum/supremum interchange is used: (U) bounds every concrete play, and the lower bounds every V_r program separately.
For B=r+1, m1 and U=Omega+(r+1)M matches the s1 lower.

## Sharpness for the whole permitted-caller class
Fix r>=1 and q=r/(r+1). For independent jobs, let w_j=q^(j-1), j1..n. These are positive; multiplication by (r+1)^(n-1) gives positive integer works without changing ratios. Choose the allowed caller with descending cheap order, retrying its current job until r failures, then all-cached. It does not know B.
At B=n+r, r useful failures on the first unit job followed by n mismatching cached completions give
 W_A=2Omega+r.
Every completing suffix action on this path is allowed; all-cached maintains the exact invariant on every other path too. General operation accounting supplies the matching upper at this B.
For every s, r w_s+Top_s = r+1, by the geometric sum. The inherited exact independent optimum therefore gives
 F_DAG=Omega+r+1,  Omega=(r+1)(1-q^n).
The ratio (2Omega+r)/(Omega+r+1) tends to alpha_r as n grows. Thus no smaller uniform constant works for every finite instance and every caller in A_r. This does NOT claim alpha_r is tight for the minimum-ready constructor, which uses ascending order and is optimal on these independent instances. Allowing all r makes3/2 the sharp supremum of the constants, not an attained finite-r factor.

## Interpretation and limitations
The guarantee permits external scheduling priorities and safe mode choices while bounding the worst-work price relative to the full universal Q/L contract. The original body filter remains O(1) query/O(log n) update and sees no future weights or edges. This theorem gives no ideal order for general positive-retry DAGs, no optimal continuation at every state, and no guarantee for an arbitrary program merely because it has small L: the caller must follow A_r's preparation/call structure.
The sharp witness is a poor allowed order, not a speedup or a natural client. It is a theorem about whole-kernel work, excluding filter maintenance, native allocation, waiting, writer work and variable/partial costs. The fixed-order greedy theorem already existed in this project; the new statement is the bound and its sharpness for the full permitted-caller interface.
The chain(2,4,1,1,2,1),r1 adaptive improvement23->22 and the seven-job local incompatible-curves example remain valid. A factor bound does not turn either into a solved exact DAG optimum.

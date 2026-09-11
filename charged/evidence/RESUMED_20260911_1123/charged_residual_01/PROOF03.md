# Charged residual safety: complete proof and interface boundary

Author research, 2026-09-11. This consolidates HYPOTHESIS02/HYPOTHESIS03 and AUTHOR_PROOF_CHECK02; neither older hypothesis nor raw experiment is changed. The benchmark is the all-cached charged curve, not an asserted optimal charged curve. This is not a native-runtime cost theorem.

## Model and quantifiers

Fix a finite positive whole-kernel job DAG J, a completed ideal D, S=J\\D, integer0<=k<=|D|, and nonnegative incurred protected cost ell. Each remaining job completes once by either fresh (protected increment p_i>0) or immediate-current-preparation cached (increment0 on match, q_i=p_i+h_i on mismatch, h_i>=0). Each mismatch is possible by one fresh own-key assignment after the job/mode and preparation have been fixed. No other completion, partial work, retry, skipped job or retained guard is admitted in this residual game. Calls are sequential with disjoint current-capture/comparison windows. The policy may know the fixed instance but receives no future write bound b. It must complete on every finite-write environment.

Let G_b=Top_b(q_J), saturating at |J|. A residual policy is safe iff the SAME policy satisfies ell+L_future<=G_(k+b) against EVERY environment with an unconditional b-write cap, for every integer b>=0. Historical k is a contract offset, operationally the number of cached mismatches since switching after the cheap phase; it is not knowledge of the actual total write count. Do not infer global-history necessity where observations can reveal more writes.

## Sorted-union identity and the all-cached region

For positive q and0<=k<=|D|,

    min_(0<=m<=|S|) [G_(k+m)-Top_m(q_S)] = Top_k(q_D).

Every term is at least the right side because the k largest D values and m largest S values form a feasible k+m subset of J. If k=0, m=0 attains0. Otherwise set tau to the kth largest D value and select H from S to contain exactly those q_i strictly greater than tau. With m=|H|, the k largest D values and H constitute k+m largest J values, including any ties by this selection, so equality holds. In particular k+m<=|J|.

All-cached has worst future cost Top_m(q_S) with m writes: at most m distinct jobs mismatch, and targeting the m largest S jobs realizes equality through one assignment per target as it becomes ready. Therefore all-cached is safe exactly on

    R: ell<=Top_k(q_D).

This statement holds for arbitrary nonnegative heterogeneous h.

## Safety of the completed-state filter

From R every ready cached action is safe. Match adds q_i to D without changing ell,k. Mismatch adds q_i to ell and increments k; Top_(k+1)(q_(D+i))>=Top_k(q_D)+q_i. A fresh action is sufficient whenever

    ell+p_i<=Top_k(q_(D+i)).                 (F)

These actions preserve R. Each completes one job, so any policy selecting only them completes the finite DAG and ends at ell_final<=G_(k+c), where c is the actual number of future mismatches. Since c<=b in any b-write environment, it satisfies the residual contract. There is no assertion that every action from an arbitrary viable state outside R is safe, nor that F minimizes total work.

## Necessity under fee separation

Assume a single fixed H bounds ALL jobs, including D and future jobs, by h_i<=H<=q_i. Equivalently max_J h_i<=min_J q_i. Suppose ell=Top_k(q_D)+delta, delta>0, and let Htarget,m be the equality cut above. Fix ANY candidate completing B-unaware policy P. Use an environment that writes exactly once at each Htarget job when its mode is cached, using a fresh identity; it spends nothing at all other jobs. This environment is unconditionally m-bounded. P must terminate. In that completed play let c count its cached targets and t=m-c its fresh targets. These targets alone impose

    ell+L_future >= ell+Top_m(q_S)-sum_(fresh targets i)h_i
                 = G_(k+m)+delta-sum_(fresh targets i)h_i.

Now define a new environment by capping this very environment unconditionally at c writes. Induction over the complete finite play preserves its history: before its jth realized write, j<=c so that write is retained; after the last, the original play has no write to remove. P is the same policy and receives no supplied b, hence all its actions and the complete play are preserved. This new environment belongs to E_c on ALL plays. The contract would require ell+L_future<=G_(k+c).

But G_(k+m)-G_(k+c) is the sum of t actual q values, each at least H, because k+m<=|J|. It is at least the sum of the t saved h_i. Therefore the reproduced play exceeds G_(k+c) by at least delta, contradiction. Strict inequality maxh<minq is unnecessary: delta supplies strictness. The result covers every DAG because each target eventually completes, irrespective of its readiness time.

Thus under fee separation R is exactly the viable region. A fresh action is safe iff F, and all cached actions are safe from R: the filter is maximally permissive within this residual game. The physical domain k<=|D| is essential to this proof. Example D with q2,p1, k2,ell3 and one remaining q2,p1 is viable via fresh (total4<=G2=4), but violates ell<=Top2(q_D)=2; it is outside the stated domain.

For common h, q_i=p_i+h and k<=|D| give Top_k(q_D)=Top_k(p_D)+hk. If ell=L_body+hk, F and R reduce exactly to the body-only predicates. The common fee need not be zero or small. For heterogeneous h satisfying the global admission bound, the same q-based filter applies, but the cancellation to p alone does not.

## Implementation without future weights

Store the completed q multiset in two heaps, its top-k sum T and kth value tau, together with ell,k. For k=0, F rejects any positive p. Otherwise Top_k(q_(D+i))=T+max(0,q_i-tau), so F is a constant-time query. Each completed job requires insertion and at most constant many heap transfers as k increases by at most one: O(log(|D|+1)) time, O(|D|) memory. Initial sorting or heap construction is charged if used; an initially empty stream needs none. Under a declared global H admission contract, future exact p/q and the future DAG need not be supplied to this safety component. The scheduler still establishes readiness. This proves safety for each finite fixed realized instance, not finite termination under unbounded arrivals.

## Indistinguishable futures require different permissions

The original analytic A/B pair and its numerical results remain in HYPOTHESIS02 and check01. The following NEW post-response simplification uses smaller integers; it is analytic, not a retrospective replacement of the evaluated inputs. Chain0->1->2, r=0, q=(2,2,4) in both worlds. Jobs0,1 have p=1,h=1. In A, job2 has p=1,h=3; in B, job2 has p=3,h=1. Both benchmarks equal G=(0,4,6,8).

Common prefix: cached0 mismatches with one write, yielding D={0},k1,ell2. Ready job1 has the same p1,q2 in both worlds. In A, fresh1 then fresh2 costs4<=G1. It belongs to a fully safe initial policy: cached0; if bad, fresh1/fresh2; otherwise cached1; if bad, fresh2; otherwise cached2. Its four leaves have costs0,4,3,4 with respectively0,1,1,1 minimum writes, and all Q=3. Additional harmless writes only loosen G.

In B, fresh1 gives ell3. Fresh2 then costs6>G1=4 without any more write. Cached2 can be mismatched with one more write, costing7>G2=6. No completing continuation is safe. The common prefix is reachable under initial all-cached in B. Thus identical full q_J, DAG, completed/current p/h/q and visible prefix still yield different safe choices when future fee splits are hidden. A filter seeing only these data cannot be maximally permissive for each instance in the unrestricted fee class. This does not forbid a conservative safe filter, and does not characterize every individual instance outside fee separation.

## Translating fixed common completion fees

If each job pays exactly one mode/outcome-independent g_i, subtract Gcost(D)=sum_D g_i from ell_total and include the full baseline Gcost(J) on the benchmark side. Then ell_total+L_future,total<=Gcost(J)+Top_(k+b)(q_J) is equivalent to the residual variable-cost contract. Cached-only comparison costs, retries, outcome-dependent fees, variable waiting and retained guards are not this baseline. No full native charge is silently erased.

## Provenance and limitations

Root's fee-separation proof predates the latest Claude response and was checked by an author helper. Claude later proposed a stronger state-specific threshold condition and an outer necessary bound; these have a separate ongoing check and are not needed above. Claude raw counts have not been added to author-run denominators. Generic budgeted top-k sums, sorted-union algebra and permissive safety control are inherited. The contribution candidate is the exact region and its resulting interface/cost boundaries for this explicitly defined game. Important actual-client demand, native speedups and submission readiness remain unestablished.

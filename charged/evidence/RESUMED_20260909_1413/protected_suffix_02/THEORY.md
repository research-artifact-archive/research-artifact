# Exact suffix feasibility and non-dominating greedy certificates

Author-derived mathematical analysis, checked by a read-only author mathematical helper after creation. This is not an independent blind review, mechanical proof, or novelty certification. The results below are under the paper's whole-kernel, own-input-identity, persistent-completion atomic-call contract.

Let J be the full positive-weight job set, S the unfinished subset at a call boundary with no retained preparation for an unfinished job, ell the protected work already paid, and h a nonnegative offset. Top_t(T) is the sum of the largest min(t,|T|) weights in T. Consider continuations with at most |S| further completion/validation calls in every finite-write environment and, for each future writer allowance b, required final protected work at most Top_(h+b)(J). A feasible continuation exists exactly when

    C(S,h,ell) := for every t=0,...,|S|,
                  ell + Top_t(S) <= Top_(h+t)(J).

This is a characterization of a suffix state under a specified protection envelope and zero remaining failure slack. It does not claim arbitrary-prefix feasibility, optimal work, or correspondence to arbitrary variable-cost/reentrant software.

Sufficiency: choose any legal order and prepare/cached-complete each remaining job. Every call completes. At most b mismatches affect distinct completed jobs and add at most Top_b(S) protected work, so C bounds the total. The statement includes b>|S| by saturation.

Necessity: at most |S| calls leaves no room for any failed validation. For each t choose the t largest remaining jobs in advance. When a selected job is computed freshly inside protection it is already charged to L and needs no write. If it is completed from a retained/fresh outside preparation, change that job's own input immediately before the eventual comparison, forcing its whole protected recomputation or a forbidden noncompleting call. At most one actual write per selected job suffices, and captured predecessor outputs persist. The resulting finite environment has at most t writes and forces protected work at least ell+Top_t(S). Hence all inequalities are necessary. The no-held-guard/no-cross-job-batching and whole-kernel assumptions are essential.

For the modeled serial threshold prefix, its observations admit a realization with exactly r+h writes, where r counts cheap failures and h counts later cached mismatches. This exact-prefix realization is required for the necessity interpretation under actual writes: a richer history that independently reveals extra writes is not compressed by this theorem. Distinct read/comparison intervals give at least r+h actual writes; Q used so far is completed jobs+r. With ell the protected work so far, C describes legal post-threshold protection states against the universal frontier Top_((B-r)+)(J). At the initial switch, C(S,0,0) holds because S is a subset of J.

A cached match preserves C by subset monotonicity. For a cached mismatch on i, for every t:

    ell + w_i + Top_t(S-i)
      <= ell + Top_(t+1)(S)
      <= Top_(h+t+1)(J).

Thus the successor C(S-i,h+1,ell+w_i) holds. A fresh next job is feasible exactly when C(S-i,h,ell+w_i) holds. Checking its |S| inequalities gives a certificate for allowing that action. Any sequence of certified fresh choices and cached choices preserves the universal Q<=n+r and worst-L frontier; no B is read. Universal lower bounds from the paper establish equality of worst L, not merely an upper bound.

The prior all-tail guard ell+sum(S)<=Top_h(J) permits finishing all remaining jobs freshly, and hence is a sufficient way to choose certified fresh actions. It is not the same policy as choosing each next job fresh whenever its successor satisfies C.

For a fixed order (including the minimum-ready-work order), any such post-threshold certified policy has worst W no greater than the same-order threshold policy. Simulate a certified run in the threshold policy: retain its cheap failures and cached outcomes; replace each certified fresh completion with a matching cached completion. Both cost w_i on those jobs. The threshold execution has the same jobs and per-job W, and uses no additional writes. It is enough that the environment is at-most-B and may choose matching outcomes. This is a comparison of worst values, not equality for a fixed schedule.

Greedy immediate fresh selection is not a work-optimality theorem. The fixed exploration has one root better and three worse than the prior all-tail rule. Both are at most threshold; neither dominates the other. All roots, native witnesses and previous results are retained in RESULTS.md, RESULTS.jsonl and native01/check01/MAXIMA.json.

A designated fresh subset F, with S\F assigned cached completion in any legal order, is safe exactly when ell+Omega(F)+Top_t(S\F)<=Top_(h+t)(J) for every t=0..|S\F|. Necessity targets the largest cached jobs; sufficiency counts cached mismatches. If F must execute before any other job, it must also be predecessor-closed within S. The feasible-subset family is downward closed, but inclusion-maximal subsets need not be unique or equally good for worst work. This subset statement is an analytic consequence and is not an additional experimental population.

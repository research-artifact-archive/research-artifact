# Exact deterministic one-job minimax additive regret

Keep the original PROOF_DRAFT.md and input-bound finite results unchanged. This refinement replaces its incomplete description of the terminal comparator call and counts all noncompleting calls, rather than equating cheap failures with actual writes. The numerical outcomes are unchanged; the general argument is not inferred from finite agreement.

In the whole-kernel pre-comparison interface, take one job of mandatory protected work w>0, fixed toll κ≥0 per counted call, and C=L+κQ. An unaware deterministic causal program must complete with Q≤r+1 in every finite-write environment. The informed comparator C*(B) minimizes worst C under the same cap on environments of at most its supplied B writes. Write C_P(B) for an unaware program's worst C in such environments and R*=inf_P sup_B≥0(C_P(B)−C*(B)).

**Informed comparator.** For B≤r, B+1 freshly prepared cheap attempts give worst(B+1)κ. Immediate cached completion gives at mostκ+w, and givesκ atB=0. To prove the matching lower bound, let a count all preceding noncompleting calls. While a<B, a comparison that could publish cheaply is invalidated by at most one fresh own-key write, placed after the mode is selected and immediately before comparison. Actual writes so far are at mosta. A cached completion can therefore be invalidated within at mosta+1≤B writes; a fresh completion needs no additional write and already incursw. If a=B is reached without protected completion, stop writing. Any eventual completion, cheap or cached, then has Q≥B+1. In both cases C≥min((B+1)κ,κ+w). For B>r the same strategy can invalidate every comparison through the call cap, using at mostr+1≤B writes. Admissibility excludes another failure afterr noncompleting calls, so protected completion is forced and C≥κ+w. Consequently

    C*(B) = κ+min(Bκ,w)  for0≤B≤r;
            κ+w          forB>r.

**Unaware lower bound.** For0<κ<w andr≥1, invalidate every selected usable comparison by at most one fresh identity. Count all noncompleting calls ina, including gratuitous/validation-only calls. Before the first fresh/cached completion, a≤r and actual writes≤a. If the completion is fresh, choose witness budgetB=a. Its regret is at least aκ+w−min(aκ,w)≥w. If it is cached anda<r, invalidate its comparison within at mosta+1 writes and chooseB=a+1≤r. Its regret is at least aκ+w−min((a+1)κ,w)≥w−κ. If it is cached anda=r, chooseB=r+1; the regret is at leastrκ. The supremum overB is therefore at leastmin(w−κ,rκ).

This environment stops writing after at mostr+1 noncompleting comparisons, even on an inadmissible program. The universal call cap excludes that many failures, and finite-write completion excludes infinite inspection/preparation loops. Stale preparations do not help: one fresh own-key identity invalidates every retained preparation at the chosen comparison. If an additional write is unnecessary, the selected B remains a valid upper bound. There is no need to assume equality between writes and failures or that a final zero-protection call is cheap. No guard survives a call, and inspection does not publish. Choosing the mode after observing the comparison would be a different interface.

**Upper bounds.** Always freshly prepared cached completion has regret(w−κ)+ whenr≥1 and0 whenr=0. The r-threshold policy has exact C_P(B)=κ+κmin(B,r)+w·1[B>r]. Its regret is max(Bκ−w,0) forB≤r, andrκ forB>r, so its supremum isrκ. Nonnegativity coversr=0,κ=0 andκ≥w. Hence

    R* = min((w−κ)+, rκ).

Choose always-cached if(w−κ)+≤rκ and the r-threshold otherwise. For0<κ<w this comparison is equivalently w≤(r+1)κ. At equality both choices attain the optimum. This is an exact all-program one-job deterministic additive-regret result under the listed operation and termination assumptions. It is not a general-workflow, randomized, total-preparation-work or physical-latency theorem.

# Strong native direct-completion comparator: exploration01

Before new computation, retain Claude's NATIVE_DECISION02_RAW_FINAL and the original restricted-game results. Study a single job with finite observations, least per-attempt write count c, nonnegative repair cost h<=W, positive prepared-attempt toll T, at mostq logical validation calls, and direct unprepared completion of cost S>=W available at the beginning of any attempt. Direct consumes one validation and completes without observing dirty; prepared attempts consume one snapshot command plus one validation (wire2). A reject continues only with remaining logical calls. This first study fixes validation cap; it reports wire separately and does not claim an optimal full-wire cap allocation.

Use full contingent-policy vectors to enumerate every observation branch and include direct at every attempt. Compare the resulting informed curve to min(S,K_T,q(B)) and compare the complete frontier to a class allowing direct only initially. This tests the proposed prefixwise dominance of direct after rejection: accepting the preceding observation costs at mostW<=S and avoids later work. The result is not assumed. Compare minimum regret using the new comparator, not the old restricted comparator. Test the claim that it is bounded by old delta and monotone inS; preserve counterexamples.

Fixed finite inputs: singleton additive components (1),(1,2),(1,2,3); additionally the two abstract general-cost examples h(a)=h(b)=1,h(ab)=10 and h(a)=h(b)=0,h(ab)=10. q1,2,3; T1,2,4,8; S from W to W+T+2 inclusive. All full policy vectors, individual comparisons, failures and timeouts retained. Whole-run cap300seconds. Numeric curve bound is q*max c+1, so all histories and direct completions are covered. These are abstract corroborations, not new native timings.

Also compare the closed-form candidate for one all-or-nothing observation of costW requiring one write, q>=2 and T<S<T+W:

    delta_new = min(S-T, T+W-min(S,2T), q*T+W-S).

For q1 the exact candidates are direct and first prepared acceptance, giving min(S-min(S,T), T+W-min(S,T+W)). Check this separately. Formula claims are author hypotheses pending proof. Native resource substitution T=beta*P+2rho, W=(alpha+beta)*P, S=W+rho is an accounting identity in the specified resource units, not elapsed-time calibration. Payload transfer bytes must remain a separate resource or explicitly priced action term when extending the objective.

No new theorem is inferred solely from passing cases. No source demand, strong novelty or merit closure is inferred from this study. A separate action class permitting different prepared subsets is only a prospective extension; do not silently include its optima in this result.

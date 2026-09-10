# Exact one-component loss with retained refresh and direct completion

Fix one component with transform workP>0, nonnegative coefficients alpha,beta,rho, and integer q>=1 validation calls for the prepared protocol. Policies are deterministic and must complete within the cap. The initial capture does not count toward q, so prepared Qwire is at most q+1. For integer B>=0 let C(P,B)=sup_{environments with at most B committed writes} cost(P,E), F_q(B)=min_{budget-informed P_B} C(P_B,B), and delta_q=min_{one B-independent P} sup_B(C(P,B)-F_q(B)); both minima use this same operation class. Initial capture/transform costs I=beta*P+rho; a dirty rejection costs rho+beta*P=I and leaves a fresh logical preparation after outside recomputation. Clean acceptance costsrho and dirty acceptance costsrho+(alpha+beta)*P=S. Direct completion from the root costsS and has no initialI. Each dirty observation requires at least one write and can be realized with exactly one after each logical capture. The resource objective is alpha*L+beta*W+rho*Qwire. It includes one snapshot command initially and one per validation; it is not a latency formula.

Accepting a clean observation dominates continuing: the current validation charge rho is common, acceptance has zero extra transform charge, and every continuation has nonnegative additional cost. Direct after a rejection, selected before any new information, is dominated by accepting the preceding dirty observation: dirty accept costsS, whereas rejection/refresh followed by direct costsI+S. This also holds whenI=0 as weak dominance. Thus it suffices to consider direct at the root, or a prepared strategy which accepts clean and on a dirty-only path rejects m times before acceptance, for some0<=m<=q-1. Extra native observations do not alter this lower-bound argument if the canonical minimal-write source execution determines them withoutB; that separate source condition must be proved.

The informed value is

    F_q(B)=min(S,(B+1)I+rho)  for0<=B<q;
           S                   forB>=q.

Upper bound: direct costsS. IfB<q, reject dirty observations until a clean one occurs, using at mostB+1 validations; cost is at most(B+1)I+rho. Lower bound: give a dirty observation after each prepared attempt while theB writes last. If the policy completes on dirty, initialI and any preceding charges yield cost at leastS. If it rejects every dirty observation until the writes are exhausted, even its first clean completion costs at least(B+1)I+rho. WhenB>=q, allq observations can be dirty, so cap-admissible completion costs at leastS; direct attainsS. The environment can stop aftermin(B,q) writes and is finite.

Direct's worst regret is D=max(S-I-rho,0)=max(alpha*P-rho,0), attained atB0. The policy rejecting every dirty observation until itsqth validation has curve(B+1)I+rho forB<q andqI+S forB>=q. Its lower-budget loss is max((B+1)I+rho-S,0)<=qI since S>=rho, and its high-budget loss is exactlyqI. Thus it attainsqI.

Fix the B-independent canonical all-dirty execution and let m be its number of dirty rejections before acceptance. For m<=q-2 choose budgetB=m+1<q, which realizes this same prefix. Its cost is(m+1)I+S and its informed comparator ismin(S,(m+2)I+rho). The difference is

    max((m+1)I, S-I-rho) >= D.

For m=q-1, chooseB=q and obtain lossqI. A deterministic prepared policy cannot avoid both cases while obeying the cap. Together with the two upper bounds this gives

    delta_q = min(max(alpha*P-rho,0), q*(beta*P+rho)).

This includesq1,zero coefficients and ties; no positive-toll argument is silently reused atI0. When the direct term is smaller choose direct initially; otherwise refresh on every dirty observation until the last validation. In particular the value can increase with the permittedq because the informed comparator also improves. Increasing a resource cap is not being asserted to make every fixed policy worse.

The formula is for the specified one-component action/preparation class. Changing prepared subsets, additional speculative computation, writer-maintained transforms or the budget-accounting interval requires a new comparison. It is not claimed as a new generic minimax principle or a performance theorem.

Author check: AUTHOR_ONE_COMPONENT_CHECK_GODEL.md found no counterexample in the deterministic model. The expectation-based randomized extension is false: P1,alpha3,beta1,rho1,q1 gives deterministic loss2, while a half direct/half prepared mixture gives worst expected regret1. This is retained as an explicit scope boundary. Each dirty event must occur in a distinct logical capture interval. This revision changes explanations and quantifiers only; oracle_run01 separately checked the original closed formula.

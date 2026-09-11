# Joint resource objectives: analytical corollary and priced extension

Author derivation after manuscript232 was frozen and sent to a separate model conversation. This file is NOT in that manuscript, not a pre-registration of an experiment, and not an established novelty/importance claim. No new experiment has been performed for this derivation. It asks whether the existing vector lower witnesses support joint objectives, instead of incorrectly replacing a supremum of a sum by a sum of separate suprema.

Keep exactly the model, full program class V_r and immediate-preparation filtered caller class A_r of dag_approximation_01/PROOF02.md. Integer r,B>=0, a nonempty finite DAG, positive whole-body weights, and the same unconditional call/protection contract apply. Write Omega=sum w, M=max w, a_1<=...<=a_n, T_s=sum of the s heaviest weights, m=min(B-r,n) when B>r. Actual calls are Q as defined in the paper, not a native-body count.

## Independent jobs: one policy for every monotone joint objective

For independent jobs the ascending cheap-until-r-failures then all-cached policy P* simultaneously minimizes

    inf_(P in V_r) sup_(E in E_B) Phi(W(P,E), L(P,E), Q(P,E))

for every coordinatewise nondecreasing real-valued function Phi on nonnegative resource vectors and every finite B. Phi and B are not supplied to P*. No interchange of infimum and supremum, or continuity/convexity of Phi, is needed.

For B<=r the value is Phi(Omega+B M,0,n+B). For B>r the value is

    max_(1<=s<=m) Phi(Omega+r a_(n-s+1)+T_s, T_s, n+r).       (J)

First handle r=0: all-cached starts immediately; every play is dominated by (Omega+T_m,T_m,n), attained by mismatching the m heaviest jobs. At B=0 the corner is (Omega,0,n). For the following last-failed-rank argument assume r>0.

Upper proof: if a play switches after r failures and has s>=1 mismatching cached completions, take a_j to be the ascending current weight at the last failed cheap call. All r failed preparations cost at most r a_j. Every later mismatched job is in that unfinished suffix, so a_j<=a_(n-s+1). Their work, and precisely their protected work, are at most T_s. Q=n+r. Thus the entire concrete resource vector is dominated by the s corner in (J). If s=0, or the program completes before r failures, its vector is dominated by the s=1 corner when B>r. Since r failures and each mismatch need disjoint writes, s<=m. For B<=r there is no protection, at most B cheap failures of weight<=M and Q<=n+B.

Lower proof: the globally capped target-s construction already used for the full-program work lower bound has, for every P in V_r, a concrete complete execution with L=T_s, Q=n+r and W>=Omega+r a_(n-s+1)+T_s. Indeed final count d=f+c=r+s forces f=r and c=s; every target completes by a useful cached mismatch, and there are no other failed cheap calls because of Q<=n+r. The charging proof gives W. This is a single execution realizing the entire lower vector, not different executions for its coordinates. The construction is unconditionally (r+s)-capped and belongs to E_B. Early budgets use the completed-call truncation of the one-maximum-job construction: B useful failures, zero protection by the cap, and eventual completion imply Q>=n+B and W>=Omega+B M. The weak lower Q>=n+B suffices. In fact Q=n+B on this witness: the universal zero-protection promise at every budget<=r prevents total cheap failures exceeding actual writes in this range. If a prefix with d<=r writes had F>d failures, an unconditionally r-capped continuation freshly invalidating every later comparison would force at least F+r-d>r failures before any permitted completion. Fresh or mismatching cached completion would instead violate zero protection. The full continuation argument is preserved with the author audit. This corrects DERIVATION02's unsupported suggestion that extra stale failures could occur after the B useful failures on this witness; it does not forbid every stale call on other histories. Apply monotonicity to each witness separately and take the finite maximum. The matching upper proves (J) and the common attainer.

For r=0, any A_0 caller on a DAG has its resource vector dominated by (Omega+T_m,T_m,n), which the same general-program lower witness forces. Thus every A_0 is simultaneously optimal for every such Phi on every DAG. For r>0 this paragraph claims no exact positive-retry DAG optimum.

## Scalar body/protection/call prices: sharp arbitrary-DAG factor

Let lambda,gamma>=0 be fixed finite real prices and define the CONCRETE joint cost

    C = W + lambda L + gamma Q,
    C_A(B)=sup_(E in E_B) C(A,E),
    F_C,J(B)=inf_(P in V_r) sup_(E in E_B) C(P,E).

Put theta=1+lambda>=1. For every A in A_r, every DAG and every B,

    C_A(B) <= beta_(r,theta) F_C,J(B),
    beta_(r,theta) = 1 + r theta / ((theta+1)(theta+r)).     (S)

For B<=r+1 all callers are exact. For r=0 all callers are exact at all B. At lambda=gamma=0, (S) is exactly manuscript232's alpha_r; it is an extension of that proof, not a distinct independent mechanism. For r=1, lambda=1, beta=11/9. These are resource-vector prices, not a fit or guarantee for elapsed time or actual native guard fees.

Upper proof: for B>r every concrete A play has

    C <= Omega+gamma(n+r)+rM+theta T_m.

This follows from the existing W accounting, L<=T_m and Q<=n+r on the SAME play; equality of separate maxima is not assumed. The target-s lower vector gives

    F_C,J(B) >= Omega+gamma(n+r)
                 + max_(1<=s<=m) [r a_(n-s+1)+theta T_s].

In particular the bracket is at least max((r+theta)M,theta T_m). Normalize x=T_m/M>=1 and z=(Omega+gamma(n+r))/M>=x. The ratio is at most

    (z+r+theta x)/(z+max(r+theta,theta x)).

For fixed x this is nonincreasing in z. At z=x, on 1<=x<=(r+theta)/theta the ratio increases with x; the derivative numerator is theta(r+theta+1)>0. On x>=(r+theta)/theta it equals 1+r/((theta+1)x), which is nonincreasing (strictly decreasing when r>0). Their meeting value is (S). At m=1 the upper and lower coincide. For B<=r both coincide at Omega+B M+gamma(n+B).

Sharpness: fix integer r>=1, theta>=1 and finite gamma>=0. Use independent descending geometric weights w_j=t q^(j-1), q=r/(r+theta), and a permitted caller processing jobs in descending order, retrying its current job until it completes or the global r-failure count is reached, then completing all remaining jobs cached. At B=n+r, its joint cost is

    (theta+1)Omega+r t+gamma(n+r).

For every s, r w_s+theta T_s=t(r+theta). By (J), the optimum is

    Omega+t(r+theta)+gamma(n+r).

First take t large relative to gamma n (or choose t_n=n^2(1+gamma)), then n large. Omega/t approaches (r+theta)/theta, and the ratio approaches beta. For gamma=0 no scaling limit beyond n is needed. Real weights suffice under the model; for rational theta, rational weights can be scaled to positive integers. This sharpness is across all permitted callers, not minimum-ready scheduling. The input cannot require exact integer weights for every irrational theta without a separate approximation argument; no such claim is made here.

## What this does and does not add

The possible positive consequence is a common optimal policy for every monotone joint resource preference on independent jobs, and an explicit price-dependent approximation bound for arbitrary-DAG caller freedom. It avoids pretending that separately optimal W/L suprema already prove a joint-cost theorem. It does not establish a new native workload, timing improvement, required production contract, or literature novelty. The exact general-DAG positive-retry problem stays open. Native preparation/validation/guard-entry fees with different charging rules are outside this scalar objective unless an explicit equality to W+lambda L+gamma Q is proved.

An author-side audit with inherited project context supports these conclusions, subject to the exposition corrections incorporated here. It is neither blind review nor formal verification. Nine declared exact-arithmetic illustrations check the displayed expressions only. The monotone result is a direct corollary of the existing vector witnesses; beta is a priced extension of the current caller-work proof. Selected earlier project files did not state these exact formulas, but this bounded comparison does not establish public-literature novelty. Original derivations, corrections and audit drafts remain preserved.

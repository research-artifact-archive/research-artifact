# Per-call toll: curve, exact compiler, and simultaneous-optimality boundary

This is an author-side mathematical result for the stated finite operation interface. It is not a calibration of Roslyn execution time or a literature-priority finding. `PLAN.md` and `run01/INPUT_RECEIPT.json` preceded the numerical execution; this full proof exposition was written after it. The exact footprint profile is an input prerequisite, as in the preceding compiler's `CERTIFICATE_SCOPE.md`.

## Model and notation

There are m positive-weight repair units. A write selects one member of a fixed, repeatable footprint family; dirtiness is the union of the selected footprints since the preceding preparation. Let c(D) be the minimum number of writes realizing D. Define H(k)=max{w(D):c(D)=k}, with unavailable k omitted, and G(k)=max_{j<=k}H(j). Then G(0)=0 and G(m)=W*>0 is the weight of the union of all footprints. This W* can be smaller than the total weight of all units. Each observation is followed by accepting and repairing D or, if a call remains, rejecting and re-preparing outside the measured resource. There are at most q calls. Call t's accepted cost is mu+t*kappa+w(D), where mu>=0 is paid once and kappa>=0 on every call. Fresh full completion costs at least as much as observing and accepting, and provides no cheaper escape. Policies are deterministic and causal. The environment's write budget B is an upper bound; unused or redundant writes are permitted.

## Known-budget curve

Let M be the multiset of qm numbers t*kappa+G(k), for t=1,...,q and k=0,...,m-1, in sorted order M_1<=...<=M_qm. Set

    C_q(B) = min(kappa+W*, M_(B+1)) for 0<=B<qm,
             kappa+W*                 for B>=qm.

The known-budget minimax cost is exactly mu+C_q(B).

Proof. Remove the common mu. Fix an absolute threshold T<kappa+W*. At call t define a_t(T)=min{k:G(k)>T-t*kappa}. This exists because t*kappa+W*>T. It is exactly the smallest write cost of a dirty set on which accepting at t exceeds T. A sequence of q such bad observations therefore requires at least A(T)=sum_t a_t(T) writes, and this bound is achievable by independently repeating minimum witnesses in each interval.

If A(T)>B, accept the first observation with t*kappa+w(D)<=T; a budget-B execution cannot contain q bad observations, so this policy finishes below threshold. If A(T)<=B, present those q witnesses: any acceptance exceeds T, and rejecting the first q-1 still forces acceptance on the last. Thus a threshold below the cap is achievable iff A(T)>B. Since G is nondecreasing, a_t(T) equals the number of indices k in 0,...,m-1 with t*kappa+G(k)<=T. Hence A(T) is the rank of T in M, including all equal entries. The smallest achievable threshold below the cap is M_(B+1). At or above the cap, accepting the first observation always suffices. This proves the formula, including ties, B=0, and saturation. With kappa=0, q copies of each profile value give C_q(B)=G(min(floor(B/q),m)). With q=1 the formula is kappa+G(min(B,m)).

The supplied `known_curve` merges q sorted shifted lists. Its implementation materializes O(qm) entries, using O(qm log(q+1)) arithmetic work and O(qm) memory. This is separate from the earlier no-toll singleton compiler's smaller-space bound.

## Exact unknown-budget ratio

At zero-based depth t and prior minimum observed write cost e, accepting a dirty set of exact cost k and weight h has ratio

    (mu+(t+1)*kappa+h)/(mu+C_q(e+k)).

Use 0/0=1 and positive/0=infinity. Because the known-budget curve is nondecreasing, an actual budget larger than e+k can only lower this ratio. Conversely, an adversary can choose that stopping-prefix budget. Consequently optimizing the worst prefix ratio is exactly the budget-unaware competitive problem. The quantifiers are: for each tested policy there is a budget and a compatible terminating execution; the same budget need not refute every policy.

For a candidate ratio R>=1, test badness by cross multiplication. At a fixed depth and exact k, badness is monotone as e decreases. Start at e=0 and repeatedly choose the smallest available k whose H(k) is bad. If an all-q bad path exists, induction couples this greedy path to it: at equal depth the greedy cumulative cost is no larger, so the witness on the other path remains bad, and the greedy next k is no larger. If the greedy path stops before q, no all-q bad path exists. Accepting the first nonbad observation then guarantees R. If it reaches q, presenting maximizing dirty-set witnesses refutes R, whichever stopping prefix the policy chooses. The proof uses monotonicity of C_q, not monotonicity of H.

A bad observation may have k=0: accumulated call tolls can make even a later clean acceptance exceed the ratio threshold. Depth still advances, so the coupling above remains valid without a positive-write assumption. For example, one component of weight3, q=3, kappa=2 and mu=0 has C(0)=2,C(1)=4,C(B>=2)=5, and the R=1 greedy bad path has costs (1,1,0).

Scale rational mu, kappa, and weights to nonnegative integers and put U=mu+q*kappa+W*. Finite attainable ratios have numerator and positive denominator at most U. If mu+kappa>0, all denominators are positive integers, so every ratio is at most U. If mu=kappa=0, the old interface applies: each denominator-zero bad observation for R>=1 has positive write cost, so q such observations cannot all retain a zero denominator. Hence ratio U is feasible in both cases, and every complete lower path contains a finite ratio. Every ratio below 1 is impossible. Binary feasibility isolates the optimum in an interval narrower than 1/U^2. Distinct fractions with denominator at most U are separated by at least 1/U^2. A complete bad path at the lower endpoint supplies the exact optimum as its minimum finite prefix ratio; the upper endpoint's feasibility proves it is the unique attainable boundary in the interval. The compiler then checks feasibility at that exact fraction.

The upper certificate is a greedy bad prefix ending at a depth where every available k is acceptable. The lower certificate is a complete path whose every finite prefix ratio is at least the returned ratio, with one equal. A checker verifies the known-budget curve, each prefix sum, each toll charge, all upper dominance conditions, and every lower ratio. Ratio 1 instead uses the general minimax lower bound. Given H,G, curve construction is O(qm log(q+1)), subsequent decisions cost O(qm log U), and storage is O(qm+q). Arithmetic bit cost and footprint-profile construction are additional. Numerical checks independently reconstruct dirty-set games, rather than treating a supplied H as authenticated native input.

## Sharp all-budget boundary

For q=1, accepting first is optimal for every budget. For q>=2:

* kappa=0: simultaneous optimality holds exactly when G(1)=W*, the preceding footprint-saturation criterion.
* 0<kappa<W*: no policy is simultaneously optimal for all budgets.
* kappa>=W*: accepting the first observation is simultaneously optimal for every budget.

The common mu does not change this boundary.

Proof for positive kappa. If a policy rejects any possible first dirty set, follow it with maximum dirtiness until it stops, using a sufficiently large finite budget. Its terminal cost is at least mu+2*kappa+W*, whereas the known-budget first-accept cap is mu+kappa+W*. Therefore an all-budget optimal policy must accept every possible first observation.

Let k*=min{k:G(k)=W*}. At budget k*, a policy can accept every first observation except maximum dirtiness. On maximum dirtiness it rejects; all k* necessary writes have then been spent, so the second observation is clean. The worst cost of this known-budget policy is at most mu+max(kappa+W_less,2*kappa), where W_less<W* is the greatest attainable nonmaximum weight (the finite family includes the empty set). For 0<kappa<W* this is strictly below mu+kappa+W*, while a first-accept policy incurs the latter on maximum dirtiness. Hence simultaneous optimality is impossible.

For kappa>=W*, at any budget B present a first dirty set of weight G(min(B,m)). Accepting incurs mu+kappa+G(min(B,m)); rejecting incurs at least mu+2*kappa, which is no smaller. Thus that first-accept value is both a lower bound and achievable for every B. This also proves the equality case kappa=W*. The kappa=0 case is exactly the old interface and retains its separate proof.

# Compact exact competitive synthesis after footprint profiling

This proof uses precisely the deterministic partial-repair interface of `../partial_repair_baseline_01/PROOF.md`. All observations concern one job; preparation after rejection resets dirtiness; write footprints are fixed and repeatable. The cost is protected repair plus a common publication baseline, not elapsed time. Let q>=1, m positively weighted components, total weight W, and common publication cost mu>=0. The known-budget comparator is K(B)=mu+G(floor(B/q)).

Let c(D) be the least number of allowed footprints with union exactly D. For every attainable k define H(k)=max{w(D):c(D)=k}; unattainable k are absent. Choose a realizing set D_k. Then G(j)=max_{k<=j}H(k), with H(0)=G(0)=0, and k<=m. Given a history of rejected observations, e is the sum of their c(D). The previous least-consistent-budget lemma says that accepting current D has worst consistent ratio

    a(e,D)=(mu+w(D))/(mu+G(floor((e+c(D))/q))).

Use 0/0=1 and positive/0=infinity. The controller computes e from observations; it receives neither B nor actual write counts.

## 1. Threshold feasibility is a path question

Fix R>=1. Call an observation unacceptable at e if a(e,D)>R. If an arbitrary controller stops on such an observation, the environment realizing this prefix with the minimum consistent writes already proves a ratio greater than R. Conversely the policy accepting the first observation with a(e,D)<=R has ratio at most R whenever it stops, by monotonicity of K for larger actual budgets. Thus R is feasible exactly when no length-q sequence consists entirely of unacceptable observations. A length-q unacceptable sequence defeats every stopping policy; without one, the threshold policy must accept by q. Fresh protected completion cannot improve this conclusion: it costs at least acceptance of any dirty observation, and stopping before an extra observation has a no-larger least consistent budget.

For a fixed k, the denominator and next e are fixed, and the largest numerator is mu+H(k). Therefore an unacceptable observation of cost k exists exactly when D_k is unacceptable. The test need only consider at most m+1 profile entries. This dominance does not assert that all reachable dirty sets of the same cost have the same weight; the runtime still tests the actual w(D).

## 2. One greedy path suffices

Set e_0=0. At e_t, choose the smallest attainable k with

    (mu+H(k))/(mu+G(floor((e_t+k)/q))) > R.

If none exists, stop successfully; otherwise set e_{t+1}=e_t+k. Reaching q steps reports infeasibility and gives the explicit history D_k at each step.

To prove completeness, compare this path with any all-unacceptable history. For each k, its ratio is nonincreasing in e. Hence the set of unacceptable k can only shrink as e increases. Inductively the greedy e_t is no larger than the history's e'_t. Every cost unacceptable at e'_t is also unacceptable at e_t, so greedy's smallest available k is no greater than that history's next cost. Consequently e_{t+1}<=e'_{t+1}. If greedy stops, all ratios at e_t are <=R, and they are also <=R at any larger e'_t; no other history can continue. If greedy reaches q, its realizing dirty sets form the required counterexample. This proves both directions, including missing k and nonmonotone H.

An exact feasibility test uses O(qm) profile comparisons and O(q) certificate entries; it never builds a table indexed by e. The acceptance policy is the same threshold R at every call, with q fixed in the comparator. Remaining calls are needed only for the cap, not for its acceptance comparison.

## 3. Exact optimization without enumerating candidate ratios

For rational weights and mu, scale them by a common denominator to integers; all ratios remain unchanged. Write U=mu+W in the scaled units. Any finite ratio arising from a profile observation has numerator at most U and positive integer denominator at most U. Different such ratios are separated by at least 1/U^2. The special 0/0 value1 also has denominator1.

The optimal value is finite and lies in [1,U]. For the upper bound, every positive-denominator ratio is at most U. An unacceptable observation under R=U must therefore have positive weight and zero denominator. Each such observation costs at least one write. If q such observations occurred, the final e+k would be at least q, making G(floor((e+k)/q))>=G(1)>0, a contradiction. Thus the feasibility test at U must succeed. A ratio of at least1 is forced by the zero-write case under the stated convention; when mu=0 a repeated maximum one-write footprint also supplies the usual positive-cost lower bound.

Test1 first; return1 if feasible. Otherwise maintain an infeasible lower endpoint l and feasible upper endpoint h, initially1 and U. Bisect exactly until h-l<1/U^2. Preserve the q-step greedy counterexample for the current infeasible l. Let rho be the least finite ratio on that path. At least one finite ratio exists by the preceding argument. Every controller stopping on that path incurs ratio at least rho, so rho<=R*, where R* is the optimal value. Also l<rho<=R*<=h.

The finite alternating stopping tree has its minimax value at one of its terminal ratio labels. Replacing sets with H(k) does not change threshold feasibility, so R* is a ratio from the profiled tree. Since rho and R* both lie in an interval shorter than the separation between different candidate ratios, rho=R*. A final feasibility test at rho gives the upper certificate. The saved q-step history gives the matching lower certificate. This argument uses no floating-point reconstruction or enumeration of O(m^2) candidate ratios.

Bisection takes O(1+log U) iterations because the initial width is at most U and the target width is U^-2. After the profile is supplied, construction and its certificate checks require O(qm(1+log U)) arithmetic operations and O(m+q) space. Integer bit costs, scaling and input representation still count; after scaling, numerators/denominators in the bisection have O(log U) bits. The state variable e needs O(log(qm)) bits. This is not a strongly polynomial bound independent of weight encodings.

## 4. Singleton footprints and general-footprint limits

For singleton footprints, c(D)=|D| and H(k)=G(k) is the sum of the k greatest component weights. Sorting and prefix summation construct the profile in O(m log m) comparisons/additions. Thus the complete singleton compiler uses O(m log m+qm(1+log U)) arithmetic operations and O(m+q) space, with the explicit bit costs above. Runtime acceptance uses a count, a weighted sum, e and a profile lookup; reading/validating the observed set still costs its representation length. A worst-history certificate can represent D_k by the first k components in the common weight ordering rather than expanding q bitmasks.

For arbitrary footprints, profile generation and exact c(D) queries can be expensive. Enumerating reachable unions may take exponential time; maximum coverage is not declared a polynomial primitive. The compact bound is conditional on the supplied correct profile, and the runtime still needs correct c(D). In particular, the compiler does not turn arbitrary partial repairs or Roslyn protected merges into this cost model.

## Attribution and verification scope

Finite-horizon minimax dynamic programming and sufficient information states are established techniques. Dave, Venkatesh and Malikopoulos, Definition1/Theorem1, provide a general information-state result: https://arxiv.org/pdf/2301.05089v2 . The model-specific reductions above and their complexity require their own arguments; the presence of these arguments does not establish literature-wide novelty. The prior mu=0 retry-first optimum remains valid, even where this compiler is unnecessary.

The separate run01 compares20,920 already-observed full-state-DP rows, checks every returned certificate, enumerates600 small complete history trees and rejects seven changed certificates/profiles. These checks support implementation consistency; they are neither a mechanical proof nor a native performance guarantee.

# When partial repair destroys simultaneous budget optimality

Author-derived result, 2026-09-10. This document specifies a new call interface. It does not assert a semantics-preserving reduction from Roslyn or a new theorem about the earlier whole-kernel interface. All work weights below are declared component-kernel work, not measured time or total critical-section work.

## Interface and information

There is one job, with a finite nonempty set C of components. Component c has work w_c>0. Initially the job is unfinished. Outside protection the controller can prepare all components from their current versions. A write changes every version in one nonempty footprint γ from a fixed finite nonempty family Γ⊆2^C. Versions do not recur. Footprints may overlap and writes may repeat, including in later attempts; each occurrence consumes one unit of the environment's total write allowance. The same footprint choices remain available in each attempt. Components not covered by Γ are allowed.

A validation/completion call holds protection, observes exactly the dirty set D (the union of footprints since its preparation), and chooses one of two actions:

* **Accept:** recompute all dirty components under protection and publish the whole job, charging L=w(D)=Σ_{c∈D}w_c. An empty dirty set completes with L=0.
* **Retry:** release protection without publishing or performing protected repair, then prepare afresh outside it.

The controller may instead perform a fresh protected completion, charging W=Σ_C w_c. Each validation/completion or fresh protected completion counts once toward Q. There are no free dirty-set queries, partial publications, retained protection across calls, or other completion modes. All calls and preparations terminate. Successful publication ends the execution. Common validation/commit overhead is excluded from this particular L metric; it cannot be inferred to be zero.

The controller observes D and its own history but does not observe the number or identities of repeated writes within an interval. It has a hard cap Q≤q=r+1, where r≥0. The environment is adaptive and uses at most B actual writes. A budget-aware controller receives B; a budget-unaware controller does not. An unaware controller must complete within the cap in every finite-write execution. Policies here are deterministic; all guarantees are worst-execution guarantees, not expected costs.

Define the **damage spectrum**

G(b)=max{w(γ₁∪···∪γ_t):0≤t≤b, γ_j∈Γ}, with G(0)=0.

G is nondecreasing and subadditive. It saturates at reachable work W_Γ=w(∪Γ)≤W. It reaches that maximum after at most |C| writes: repeatedly add a footprint covering a still-uncovered reachable component. Let σ≥1 be the first saturation index. A single-write positive-damage observation is always possible because Γ is nonempty and its footprints are nonempty. Singleton footprints give G(b)=Ω_min(b,|C|), the sum of the largest indicated component weights.

## Theorem 1: budget-aware optimum

For every q≥1 and B≥0, the minimum worst protected repair work in this interface is

K_q(B)=G(⌊B/q⌋).

The achieving policy can also be extended to satisfy the call cap outside the supplied budget.

**Upper bound.** Set k=⌊B/q⌋ and τ=G(k). Accept when w(D)≤τ. Otherwise retry if a call remains; on the last permitted call accept regardless. A dirty set of work greater than G(k) cannot result from at most k writes, by the definition of G. Each rejection therefore certifies at least k+1 distinct write *occurrences in that preparation interval*, without disclosing their exact number. If the last call also had work greater than τ after q−1 rejections, the q disjoint intervals would contain at least q(k+1)>B writes. Thus this last branch is unreachable within the supplied allowance; every accepted dirty set has work at most τ. Fresh protection is unnecessary. On any out-of-budget execution the forced final accept still satisfies Q≤q, but the τ guarantee is not asserted there.

**Lower bound.** Choose a footprint word of at most k writes whose union has work G(k), which exists because the family and component set are finite. After each fresh outside preparation, replay that word using fresh versions. At any accept, the repair work is G(k). A fresh protected completion instead costs W≥G(k). If the controller rejects, repeat before its next call. It must complete by call q, and the environment uses at most qk≤B writes. For k=0 the nonnegative-cost bound is immediate. The controller's knowledge of B and of each dirty set does not defeat this environment. ∎

## Theorem 2: the envelope forced by low-budget optimality

Let P be a budget-unaware policy satisfying the universal call cap and attaining K_q(B)=0 for every B≤r. Then, for every B≥0,

sup_{E: writes(E)≤B} L(P,E) ≥ T_q(B):=G((B−r)_+).

The policy that retries its first r nonempty dirty observations and then always accepts attains equality simultaneously for all B. Thus T is the least achievable envelope **subject to the low-budget zero-work optima**. This is not the pointwise infimum over all unaware policies without that constraint.

**Lower bound.** For B≤r the claim is nonnegativity. For B>r, fix any γ∈Γ and cause exactly one γ-write in each of the first r preparation intervals. Before the jth such observation, the entire history is compatible with an execution having only j≤r writes in total. Accepting that positive dirty set, or performing fresh protected work, would violate the required zero optimum in that low-budget execution. Since P does not receive B, it must retry at every one of these r observations. After the rth rejection, a fresh protected completion would also violate the compatible B=r execution, so P must prepare outside and make its final permitted validation/completion call. Before that call, cause a word of at most B−r writes realizing G(B−r). No further retry is possible under the universal cap. P must accept and pay G(B−r). The combined environment uses at most B writes. The case r=0 starts directly at the final call.

**Upper bound.** A nonempty dirty observation requires at least one write in its own interval. If the threshold policy reaches its last call after r rejections, at least r writes have been consumed. At most (B−r)_+ writes can affect the new preparation, so the final dirty work is at most G((B−r)_+). Any earlier acceptance has empty D and cost zero. Every execution completes within q calls. ∎

For a fixed B, the budget-aware threshold τ=K_q(B) can be hardcoded and extended by a final forced accept; it is a universal-cap unaware program as far as its run-time inputs are concerned. Consequently the pointwise infimum among all such programs equals K_q(B), but the program chosen for one B may be suboptimal at another. The next result concerns one common program, not this pointwise infimum.

## Theorem 3: exactly when one program is optimal for every budget

For r≥1, one unaware policy achieves K_q(B) simultaneously for all B if and only if G(1)=W_Γ, equivalently G(b)=G(1) for all b≥1. For r=0 a simultaneous optimum always exists.

**Necessity.** Every simultaneous optimum satisfies the low-budget requirement of Theorem 2. If G is not saturated after one write, let k≥2 be its first strict increase beyond G(1). Set B=r+k. Since r≥1 and k≥2, ⌊(r+k)/(r+1)⌋ lies between 1 and k−1. Therefore K_q(B)=G(1)<G(k)=T_q(B), contradicting Theorem 2.

**Sufficiency.** If G is constant on positive arguments, then G((B−r)_+)=G(⌊B/(r+1)⌋): both are zero for B≤r and both equal G(1) for B≥r+1. The threshold of Theorem 2 attains all the optima. If r=0 the two arguments are equal for every B, regardless of G. ∎

The condition is about achievable invalidation damage. Merely providing a partial-repair operation does not imply failure: if a single legal write can invalidate all reachable prepared work, simultaneous optimality survives for this single-job model.

## Corollary 4: sharp competitive cost of preserving zero low-budget work

Any unaware policy with a finite multiplicative competitive factor against K must have L=0 for B≤r, because K is zero there. The threshold in Theorem 2 is consequently optimal pointwise among finite-factor competitors. Its exact best factor is

R_q(Γ,w)=max_{q≤B≤qσ} G(B−r)/G(⌊B/q⌋) ≤ q.

Beyond B≥qσ, both numerator and denominator equal W_Γ, so this is a finite maximum. For B≥q let k=⌊B/q⌋≥1 and write B=qk+t with 0≤t<q. Then B−r=qk+t−q+1≤qk. By monotonicity and subadditivity, G(B−r)≤G(qk)≤qG(k). All denominators in the displayed maximum are positive.

For q=m, singleton footprints and m unit-work components, B=2m−1 gives K_q(B)=1 but T_q(B)=m. Thus the factor q is sharp and is unbounded as the permitted retry allowance grows. More generally G(b)≤W_Γ≤|C|G(1), so the factor is also at most |C|. This bound is a protected-component-work ratio, not a wall-clock slowdown.

## Two-component witness

Let C={a,b}, w_a=w_b=1, Γ={{a},{b}}, q=2. The budget-aware optimal profile for B=0,…,7 is (0,0,1,1,2,2,2,2). At B=3, accept a one-component dirty set immediately; retry a two-component set, which has consumed at least two writes and leaves at most one write before the final call. Worst repair is1.

A policy also optimal for B=1 cannot accept the first one-component dirty set: that same prefix may be the entire one-write execution. It must retry. Two more writes, one per component, before its second call force repair2 within B=3. The retry-first profile is (0,0,1,2,2,2,2,2). The known-B=3 policy instead has unaware profile (0,1,1,1,2,2,2,2), explicitly exposing its low-budget sacrifice.

## Evidence and limits

`run01` records 3,495 footprint/weight instances and 160,080 q/B cells. An observation-respecting remaining-budget DP, a collapsed spectrum DP and K's formula agree throughout. Classification counts compare the formula envelopes with one-write saturation; they are not exhaustive policy enumeration for those 3,495 instances. The two-component study records the eight first-dirty-set accept/retry mappings plus always-fresh. The raw field name `all_undominated_policies` is imprecise: this is the complete canonical candidate set under the stated action reductions, and it includes dominated policies. Preserve the raw file and use this corrected interpretation. Five controls reject the named perturbations; several are algebraic controls, not raw-trace mutation tests.

These checks support error detection and are not a mechanical proof. The threshold upper/lower arguments above supply the general reasoning. Γ is fixed and repeatable; changing footprints, state-dependent repair costs, partial publication, retained locks, free future-write information, probabilistic expected objectives or total overhead prices require new analysis. Roslyn's conservative rebase guard has not been reduced to this interface. The theory characterizes a transfer boundary, without establishing application prevalence, general source safety, or external novelty relative to all bounded-loss stopping and online-search results.

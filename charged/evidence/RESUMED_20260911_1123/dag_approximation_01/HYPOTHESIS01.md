# New author hypothesis: simultaneous approximation on arbitrary DAGs
Created before any new evaluation, 2026-09-11T05:36:08.489743+00:00.

This extends the interpretation of existing results, not a new minimum-ready ordering algorithm. RESUMED_20260909_0056/charged_universal_order_01/THEORY.md already proves that minimum-ready Kahn order minimizes the fixed-order cheap-then-all-cached family's work simultaneously for every B,r. The chain(2,4,1,1,2,1),r1 counterexample to two fresh/cached rules remains, and full-program DAG optimum remains open.

Fix all original body-only interface premises, positive whole works, persistent outputs, finite DAG, common charged start, deterministic causal policies and universal Q<=n+r and optimal L(B)=Top_(B-r)+(J) for every B. Let F_DAG(B) be the infimum worst W(B) over that SAME all-budget policy class, not a separately chosen known-B protection contract.

Candidate: minimum-ready fixed-order cheap-until-r-failures then all-cached gives ONE universally admissible policy with
 W_A(B) <= alpha_r F_DAG(B) for every B,
 alpha_r = (3r+2)/(2r+2) = 3/2 - 1/(2(r+1)).
At B<=r and at r=0 it is exact. At B=r+1 it is also exact. Alpha is a sufficient approximation guarantee; no tightness claim, no new solver/method novelty or application importance is inferred.

Derivation under audit:
Let Omega=sum w, M=max w, m=min(B-r,n), T=Top_m(J), r>=1,B>r.
Existing all-cached upper U<=Omega+rM+T (for any fixed legal order, so greedy is at least as good).
Existing order-independent all-program lower from current main.tex Theorem3 proof appears to apply to every DAG:
 F_DAG(B)>=Omega+H, H=max_{1<=s<=m}(r a_(n-s+1)+Top_s(J)).
In particular H>=(r+1)M and H>=T.
Thus for z=Omega/M >= x=T/M>=1,
 U/F <= (z+r+x)/(z+max(r+1,x)).
For fixedx, numerator-denominator difference is nonnegative, so ratio decreases withz; take z=x.
For x<=r+1, (2x+r)/(x+r+1) increases withx.
For x>=r+1, (2x+r)/(2x)=1+r/(2x) decreases.
Atx=r+1 this is alpha_r. Ties and m saturation do not change it.
For m=1, U=Omega+(r+1)M and the matching target lower proves exactness.

Main risks: independently verify the all-program lower extends to DAG readiness; r=0/zero n convention; supremum/infimum quantification; hidden observations and stale record failures; no illicit known-B substitution. Do not use finite agreement as proof. Fixed-order optimality alone is insufficient for approximation against full causal programs; the latter needs that lower.

Next root action: read exact existing lower proof and its supporting charged-record lemma; derive algebra in a separate proof. Any finite verification must freeze input set before execution and retain all outcomes. Existing prior raw data may be reanalyzed under an explicitly new observed-after analysis; do not claim new independent experiments or repeat old populations as new data.

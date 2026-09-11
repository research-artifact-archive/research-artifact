# Additional audit of root PROOF01.md

The root derivation was copied to inputs01/ROOT_PROOF01.md and hashed BEFORE this read. INPUT_RECEIPT03.json records SHA-256 `acc54341674636ad3b221645ba60b2e264a5f6c571d00c487246a77d5c9bb2d3`. The own PROOF_AUDIT01.md was already written; its pre-read SHA-256 is `0a4c15dc3b4dcbfe10681aac002911e67286b393db138af300748d54763711f0`. This records sequencing, not blind independence: this task already knew the two hypotheses, manuscript and user explanations.

**Result: root PROOF01 is supported under the inherited interface. No theorem-changing correction is required.** It agrees with the separately written author audit on the full-program lower, arbitrary-caller upper, exact boundaries, coefficient and geometric sharpness. Independence of jobs is used only to identify the exact benchmark in the sharpness family; it is not used in the general lower construction.

| Root claim | Audit finding |
|---|---|
| V_r is the full simultaneous class, F is pointwise infimum of worst W over it | Correct. No policy is supplied the evaluation B; no single minimizer of every pointwise infimum is assumed. |
| A_r follows immediate cheap calls then exact-filtered fresh/cached completion | Correct. Exactly one new preparation for cached, none unnecessarily before fresh, and no additional paid preparation are essential for the upper identity. |
| A_r subset V_r, arbitrary ready/history choices allowed | Correct by the exact residual invariant, distinct write intervals, n completions plus at most r failed calls and finite selections. Readiness is caller responsibility, not an optimization assumption. |
| W=Omega+failed-cheap works+cached-mismatch works | Exact for A_r, with the stated absence of other kernels. It is not asserted for full V_r. |
| Globally (r+s)-capped target writer | Correct on all plays: active implies f<=r,t<s, and d=f+c with c<=t gives d+1<=r+s. Fresh/stale-cached completions increase t without a write. |
| DAG readiness does not break the lower | Correct: the writer waits silently for selected ready targets; unconditional boundedness forces a V_r program to finish their predecessors and the targets. No edge is removed, and targets need not be an ideal or simultaneously ready. |
| Actual-count protection forces d=r+s,f=r,c=s | Correct. The cap lemma gives Top_s<=L<=Top_((d-r)+); positive works and s<=n force equality of counts. Known-B protection alone would not justify this step. |
| Early/retained/stale records and inspections do not erase work | Correct by the frozen creator-injection lemma, common-start charging, fresh identity supply, prior-store-only record selection and excluded in-gate unprotected preparation. |
| Exactness at B<=r+1 and all B when r=0, for every A_r caller | Correct from matching full lower and per-caller upper, including zero budget. |
| alpha_r=(3r+2)/(2r+2) for every caller and every B | Correct. The ratio decreases in z for z>=x>=1, and the remaining two branches meet at x=r+1. No infimum/supremum interchange occurs. |
| Descending geometric caller reaches 2Omega+r at B=n+r | Correct: r first-job failed preparations and n distinct cached mismatches realize it with an unconditional n+r write cap; operation accounting matches it from above. |
| Exact independent optimum Omega+r+1 | Correct since each inherited term r w_s+Top_s equals r+1. |
| Integer scaling and convergence establish smallest uniform caller factor | Correct; w'_j=r^(j-1)(r+1)^(n-j)>0. The ratio converges from below, so every smaller factor fails on some finite instance. |
| 3/2 is the supremum when r is also unrestricted | Correct. Choose r so alpha_r exceeds a proposed smaller number, then a finite n in that r's geometric family. No finite-r attainment of 3/2 is asserted. |
| Not tightness for the minimum-ready algorithm | Correct and necessary. Minimum-ready is ascending and exact on this independent family. |

Two small precision points can be made explicit when preparing the paper, without changing the theorem:

1. State r in the nonnegative integers, as in the inherited paper; it counts failures. The proof already uses that convention.
2. In the early-budget truncation, stop writing after the COMPLETED call containing the Bth useful write. This preserves the Bth failed-preparation event and avoids an unnecessary ambiguity about a prefix ending between gate and effect. The existing argument and the root's intended completed-operation semantics already justify this choice.

The opening reference to immediate capture/preparation should continue to be read as the attaining/caller discipline, not a restriction secretly imposed on full V_r; the subsequent definition explicitly allows full programs to prepare early and retain records. The audit's main proof separates these classes throughout.

No numerical experiment was required or run. Existing chain6 and seven-job adverse records remain unchanged; neither theorem establishes the full positive-retry DAG optimum or least continuations at every state. The broad caller guarantee remains conditional on the whole-kernel interface, and no native cost/runtime or application claim is certified here.

# Bounded author audit: general-DAG caller approximation

**Supported under the declared body-only interface.** Theorem3's all-program lower extends to every finite DAG. HYPOTHESIS02_INTERFACE and the subsequently frozen root PROOF01 also hold: every permitted immediate cheap-then-filtered caller has the simultaneous factor

    alpha_r=(3r+2)/(2r+2)

against the FULL all-budget optimal-L / universal-Q causal-program class. For each fixed integer r>=1 this is the smallest uniform coefficient over all finite inputs AND all permitted callers. This is not a tightness result for the minimum-ready algorithm. There is no formula-changing defect or in-model analytic counterexample in this audit.

The full derivation and model audit are in [PROOF_AUDIT01.md](PROOF_AUDIT01.md); the direct clause-by-clause check of root PROOF01 is in [ROOT_PROOF_AUDIT02.md](ROOT_PROOF_AUDIT02.md). This is author-side scrutiny, not blind review, proof-assistant certification or paper/public adoption.

## The lower bound covers full programs on arbitrary DAGs

For m=min(B-r,n), B>r, the full class satisfies

    F_DAG(B)>=Omega+max_(1<=s<=m)
                         [r a_(n-s+1)+Top_s(J)]
             >=Omega+max((r+1)M,Top_m(J)).

The argument targets the s heaviest jobs, writing only at their comparisons whose no-write continuation would match. At every boundary d=f+c and c<=t; while active f<=r and t<s, so the next write has d+1<=r+s. This is an unconditional writer cap even on inadmissible programs.

Readiness does not require targets to be simultaneously ready or to form an ideal. The writer stays silent on inspections, preparations and nontarget predecessors. Since it is globally bounded, an admissible full program must finish those predecessors and eventually all targets. Every target completes protectively. Capping the exact realized play at its actual d then gives Top_s<=L<=Top_((d-r)+). Positivity forces d=r+s, f=r and c=s. The global creator-injection lemma charges those distinct failed preparations and target duplicates from the common start, regardless of retained copies, stale inputs, early-after-readiness preparation or late record selection.

Thus independence is unnecessary for the lower. It is needed only for the old theorem's ascending-order attaining equality and for the sharpness family's exact benchmark.

## Stronger arbitrary-caller conclusion and sharpness

For every caller obeying A_r, with no unnecessary paid preparation, each actual execution has

    W=Omega+sum(failed cheap works)+sum(cached mismatch works).

Distinct current-capture intervals give at most r cheap failures and at most B-r cached mismatches on distinct jobs after switching. Hence W_A(B)<=Omega+rM+Top_m(J), without a fixed order or minimum-ready assumption. The exact body filter supplies membership in full V_r. Combining this upper with the lower proves alpha_r. **Every such caller is exact at B<=r+1, and every r=0 caller is exact at all budgets.** Pointwise F_DAG need not have one simultaneously attaining policy for this approximation statement to hold.

For fixed r>=1, descending independent weights w_j=q^(j-1), q=r/(r+1), give a permitted poor-order caller with W_A=2Omega+r at B=n+r. The inherited independent optimum is F=Omega+r+1 because r w_s+Top_s=r+1 for every s. With Omega=(r+1)(1-q^n), the ratio tends to alpha_r from below. Scaling by (r+1)^(n-1) gives exact positive integer weights r^(j-1)(r+1)^(n-j). Every smaller uniform factor therefore fails on a sufficiently large finite instance. This establishes sharpness for **all caller choices**, while minimum-ready uses ascending order and is optimal on these same inputs. When r also varies, 3/2 is the supremum, not an attained finite-r constant.

## Preserved adverse results and limitations

- The existing chain (2,4,1,1,2,1), r=1 still has the saved adaptive improvement W(5)=22 versus23 for the simple rules. The audited full lower is21 there, so 22 is not newly labeled the full-program optimum. The seven-job residual tradeoff also remains valid. No claim of a least general-DAG curve or simultaneous optimum at every intermediate state is made.
- The guarantee compares the SAME all-budget Q/L contract. The supplied-B class is different: the inherited (8,16), r=0, B=1 example has supplied-budget W=32 versus universal-contract40. Substituting that benchmark would invalidate the factor1 boundary.
- The upper needs A_r's exact preparation discipline. Even n=1, r=B=0, redundant double preparation then cached match has W=2 instead of1. That is outside A_r, not a counterexample to the explicit hypothesis.
- The lower needs positive whole kernels, charged initialization, immutable saved parents, certified records, a fresh identity outside the finite store/history, and the comparison gate after job/mode selection. It does not establish a partial-work/native runtime result. Filter maintenance, waiting, allocation and writer costs are outside W.
- No new minimum-ready theorem, minimum-ready worst-factor tightness, source demand, practical importance or submission readiness is certified.

Two wording refinements for adoption: explicitly write r in the nonnegative integers; in early-budget truncation, end the prefix after the completed call containing the Bth useful write. Neither changes the result.

## Inputs, trials and stop

The first substantive read was the new HYPOTHESIS01. The exact requested old interpretation filename is RESULT_INTERPRETATION_JA.md. The relevant current manuscript is RESUMED_20260910_0343/paper_candidate_bounded_retry/main.tex; repository-root main.tex is an older different manuscript. The captured manuscript hash is `a12f25d2603e94b71725954d5357495c350edca0c630358e66f04ada1325587d`. Root PROOF01 was subsequently frozen at hash `acc54341674636ad3b221645ba60b2e264a5f6c571d00c487246a77d5c9bb2d3` and checked after the own analytic audit had been written.

[INPUT_RECEIPT01.json](INPUT_RECEIPT01.json), [INPUT_RECEIPT02.json](INPUT_RECEIPT02.json) and [INPUT_RECEIPT03.json](INPUT_RECEIPT03.json) bind all frozen audit inputs. Existing minimum-ready and chain6 results were read and interpreted, not rerun. **New finite experiments: 0; retries/exclusions/timeouts: 0.** No finite-disagreement count is presented as proof. There were no child agents, Claude calls, humans, reset/credit/paid API use, paper/public edits or writes outside this directory.

The assignment is complete before the15:00 JST reporting deadline and15:05 hard stop. [STOP_RECEIPT.json](STOP_RECEIPT.json) records the actual closeout time and no remaining owned research processes; [OUTPUT_MANIFEST01.json](OUTPUT_MANIFEST01.json) binds final outputs. Root alone decides paper/artifact adoption.

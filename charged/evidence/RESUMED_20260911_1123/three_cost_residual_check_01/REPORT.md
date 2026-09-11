# Three fixed actual costs: author-side proof/model audit and single fixed check

**Finding: the proposed V and both mode inequalities are correct under the inherited residual interface and b>=max(a,f). No formula correction was found.** The full analytic justification, including quantified writer/model correspondence and boundary cases, is in [PROOF_AUDIT01.md](PROOF_AUDIT01.md). This is a narrow author-side audit, not blind review or a claim of paper readiness. Root alone controls paper/public adoption.

Let q=b-a, p=f-a, d=max(a-f,0), t=b-max(a,f), and ell=lambda-sum_D a. Then

    V(D,k)=sum_S d+Top_k(q_D union t_S).

For ready i, X=q_D union t_(S-i) and R=sum_(S-i)d:

    cached i permitted iff ell<=R+Top_k(X);
    fresh i permitted iff ell<=R+Top_k(X union {q_i})-p_i.

Each ready job's best mode has threshold V. Actual lambda is nonnegative; ell can be negative. The actual benchmark is sum_J a+Top_(k+r)(b-a), with r the future write bound. The proof covers real nonnegative fixed prices, zero q, all-zero prices, equality and ties, signed ell/p, empty/terminal states, and integer k/budget saturation. All-budget quantification remains over ONE causal policy not supplied r.

## Translation and implementation implications for root

- For actual source prices a=g+c, f=g+w, b=g+c+w, the substitution is q=w, p=w-c, d=(c-w)+, t=min(c,w). Both guard and cached comparison costs remain in the actual total and benchmark. This translation is correct when c>w as well as c=w and c<w.
- The old claim that future p/body quantities do not enter does **not** carry over unchanged. The signed extension requires future savings d and residual t; future w can matter when c>=w. Future edges still only restrict readiness.
- filter01.py currently rejects p<=0, completed q=0, and negative normalized incurred values. Its heap update h->h+p is not the signed extension: the new update is t->q, an increase max(p,0), while the savings sum drops d. No existing implementation or positive-p heap result is promoted to coverage of this extension.
- A viable state can require fresh. Frozen game844, chain (1,2,3)->(3,1,4), after the first fresh call has lambda=2, ell=1, k=0. Actual state/cached/fresh limits are 3/1/3, so only fresh is safe.
- Signed ell matters on reachable histories. Frozen game718 reverses those types; after the first fresh call lambda=1 and ell=-2. The second fresh call is safe (actual limit2), while clamping ell to0 would forbid it. Both examples have actual all-cached curve 4,6,7,7,... . These are post-run explanatory selections from the fixed population, not additional experiments.
- The supplied-one-write joint (total,protected) frontier in FULLY_CHARGED_PROOF05 has a different policy class, supplied bound and objective. Importing its fixed per-call prices does not import its cheap suffix, total-work claim, or optimization complexity.

## One fixed complete-policy-tree run

[PLAN01.md](PLAN01.md) declared n=0..3, all labeled DAGs, eight actual price types (including b=max(a,f), f<a, f=a, f>a and zeros), all assignments, every completed ideal D, and every physical k=0..|D|. [FREEZE01.json](FREEZE01.json) binds the explicit actual population, structural complete policy/leaf catalog, all checker code and source snapshots before outcome execution. It was not repaired or rerun. No old large experiment or positive-p heap tester was run.

The oracle independently enumerates every full-J cached mismatch subset and sums actual a/b costs to obtain the benchmark. It then enumerates all complete policy trees and all their leaves, summing actual a/f/b costs. A policy's permissible actual-prefix cost is min_leaf[actual benchmark(k+c)-actual future charge]; the best such policy and each forced-root-mode optimum are compared with the proposed formulas. The oracle uses no candidate normalization, Top expression, existing filter or value-function recurrence. Every game's full raw is written and flushed before that game's candidate comparison; raw files are closed and hashed before aggregate output. All trees, leaves and trials remain available, including cost-identical ones.

| Quantity | Fixed/completed count |
|---|---:|
| State games | 157,465 / 157,465 |
| Complete policies evaluated | 1,934,433 |
| All policy leaves evaluated and saved | 7,964,521 |
| Exact ready-job/mode limits | 247,312 |
| Actual benchmark comparisons | 943,459 |
| Actual-prefix boundary probes | 685,077 |
| Probes with negative normalized ell | 190,965 |
| Games with disagreement | 0 |
| Invalid / timeout / not run / excluded | 0 / 0 / 0 / 0 |

Graph counts for n=0,1,2,3 are respectively 1,1,3,25. State-game counts are n=0: 1; n=1: 24; n=2: 1,280; n=3: 156,160. Scientific execution ran once from **13:44:17 to 13:44:33 JST** (16.17 seconds), exited0, and spawned no child processes. Its 180-second wall bound was not approached. [run01/RECEIPT01.json](run01/RECEIPT01.json) records every denominator and raw hash. [READBACK01.json](READBACK01.json) independently reads all saved records, confirms exact counts and input/code/raw hashes, and extracts the two explanatory games; it does not rerun an oracle, formula, or scientific trial.

The zero-disagreement result corroborates this deliberately finite synthetic population only. It is not a general proof, a workload sample count, source calibration, an implementation test of filter01.py, or blind-review evidence. General correctness rests on the separate analytic argument and its stated assumptions. No old unfavorable results or STOP records were altered.

## Receipts and handoff

- Pre-outcome freeze SHA-256: `cef8f0eb0307c4316429f7d9b81048f57f1267ea22d87372e97f7fbeca4acb33`.
- Complete actual policy/leaf raw: [run01/RAW01.jsonl.gz](run01/RAW01.jsonl.gz), SHA-256 `0c350bf818a5e9168a36a5ebadb2a85b5cbf48163962059fa2d10eea49af25e0`.
- All candidate comparisons: [run01/COMPARISONS01.jsonl.gz](run01/COMPARISONS01.jsonl.gz), SHA-256 `c1d28a78014ba794a7567242961481aca4d441441bce57f2ad542647f1245617`.
- Full provenance: [FREEZE01.json](FREEZE01.json), [run01/EVENTS01.jsonl](run01/EVENTS01.jsonl), [READBACK01.json](READBACK01.json), [STOP_RECEIPT.json](STOP_RECEIPT.json), and [OUTPUT_MANIFEST01.json](OUTPUT_MANIFEST01.json).

All writes stayed inside this assigned folder. No paper, publication, shared-state or other helper files were changed. No delegates, Claude, human evaluations, resets, credits, purchases, paid APIs or automations were used. Task activity and owned processes stop before **14:00 JST**, as recorded in STOP_RECEIPT.json. This narrow assignment is complete; no further experiment or implementation change is left running.

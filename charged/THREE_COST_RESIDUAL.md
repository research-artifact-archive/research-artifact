# Three actual costs: exhaustive residual policy-tree replay

Stage59, `three-cost-residual`, reruns the sole fixed actual-price oracle on all **157,465 games**, with 1,934,433 complete policies and 7,964,521 policy leaves. Python 3.10 or later, standard library only, assertions enabled; Linux/macOS. Public stage timeout is at most 300 seconds; this worker uses 175 seconds overall and 165 seconds for its oracle process.

```sh
python3 -B charged/reproduce.py three-cost-residual --out work/three-cost-residual --timeout 300
```

The actual-price evaluator enumerates policy leaves and benchmark subsets using the fixed `(a,f,b)` prices, with `b >= max(a,f)`, without importing the candidate Top formula, normalization or filter implementation. Only after each raw oracle result is flushed does the separate comparator evaluate the formula. This is a separately written author-side oracle with shared hypotheses and fixed inputs, not blind review or evidence of native costs. The [plan](evidence/RESUMED_20260911_1123/three_cost_residual_check_01/PLAN01.md), [proof/model audit](evidence/RESUMED_20260911_1123/three_cost_residual_check_01/PROOF_AUDIT01.md) and original raw records remain separate from the new replay output.

Replay compares every decoded byte of both original and freshly generated raw/comparison streams, plus all scientific receipt fields. Expected counts include 247,312 mode limits, 943,459 benchmark comparisons, 685,077 nonnegative actual-prefix probes and 190,965 negative-normalized-prefix probes. The fixed historical result has zero disagreements; the replay must compute that result anew. No inputs, catalog entries, policy trees, actual prices, formulas or probes are regenerated or altered.

[Projection map](SOURCE_PROJECTION_MAP04.json) preserves the distinction between original-source hashes and anonymous public bytes. The historical freeze/receipts remain in `fixed/`; a separate working freeze binds the projected files and an obsolete absolute cutoff adapted to a fresh 165-second budget. Both exact diffs are saved. Original execution time is retained as historical resource accounting. Replay is not another scientific attempt, population, proof certificate, native experiment or latency result. No external service is contacted. An incomplete replay reports failure and retains partial output.

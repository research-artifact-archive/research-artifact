# Exact one-job regret when each whole-kernel call is charged

This supplement retains the fixed one-job comparison and its refined all-program proof. In the pre-comparison whole-kernel interface, a program may inspect/prepare outside protection but selects its mode before the counted comparison. It must finish one work-w job with at most r+1 calls in every finite-write environment. The metric is C=L+κQ.

Against the B-informed optimum, the smallest worst additive loss across all hidden budgets is `min(max(w-κ,0),rκ)`. For positive κ<w, choose immediate cached completion when `w <= (r+1)κ`, and the full-r threshold otherwise. The original published137 result bounded the loss of a specific threshold policy; this result optimizes the worst additive loss across all deterministic one-job programs. It does not extend that optimization result to arbitrary workflows or randomized controllers, and no cost is calibrated to elapsed time.

Evidence is in `evidence/RESUMED_20260910_0343/single_job_regret_01/`. The original proof draft and fixed numerical inputs remain unchanged. `PROOF_REFINED.md` corrects the draft's incomplete description of a final comparator call: once B noncompleting calls occur, the final zero-protection call need not be cheap. The refined argument counts all noncompleting calls and uses actual writes bounded by that count, without assuming equality. It explicitly stops the adversary and invokes finite-write completion to exclude infinite free inspections.

The fixed finite comparison includes1404 parameter conditions,11232 budget roots and131040 policy-budget values. Direct informed games agree with the formula, and complete serial fresh-preparation policy enumeration agrees with the minimax regret. All1404 always-cheap variants are rejected as universally inadmissible. Four changed-output/cap controls are detected. Finite enumeration is corroboration; it does not replace the broad program-class proof. All pre-execution and outcome records are retained.

Run the new stage with Python3.10 or later:

```sh
python3 -B charged/reproduce.py single-job-regret --out work/single-job-regret01 --timeout 300
```

The stage recalculates all fixed mathematical rows and requires exact equality of inputs, root outputs and regret vectors. It performs no native run or timing measurement. It is also included in the standard `all` command as stage36.

The adjacent primary-work comparison in `evidence/RESUMED_20260910_0343/closest_repair_work_1157/COMPARISON.md` attributes incremental reuse, repair-cost semantics and bounded iteration. Only the short comparison and retrieval metadata are redistributed; the original articles and author-helper conversations are excluded.

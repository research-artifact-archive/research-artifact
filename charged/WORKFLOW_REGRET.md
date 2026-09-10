# Minimum uniform additive loss for repair workflows

The finite threshold constructor also computes how much cost must be allowed when no exactly common-optimal policy exists. For the fresh-preparation repair workflow interface, let K(B) be the informed minimax cost at write bound B, and let C(P,B) be the worst cost of one budget-unaware, universally capped policy. Then

`min_P max_B (C(P,B)-K(B)) = -Theta(J,r,0)`.

The minimum is attained. Replacing each terminal target K(e) by K(e)+delta shifts every threshold by delta. A feasible policy therefore exists exactly when delta>=-Theta(J,r,0). The emitted selector uses the shifted inequalities, observed dirty masks and retained history; it never receives B. The [proof](evidence/RESUMED_20260910_0343/workflow_uniform_regret_02/PROOF_REFINED.md) treats least consistent budgets, clipping, nonnegative tolls and fixed per-completion constants. This extends the use of the existing model-specific minimax recurrence; it is not a new general dynamic-programming principle or a closed form for arbitrary workflows.

For A with singleton component weights(1,2), followed by C with one component of weight1, use one shared rejection and per-call cost1. The informed curve is2,3,5,5,6 at budgets0,1,2,3,>=4. A policy receiving no budget attains2,4,5,6,6, and its minimum uniform additive loss is1. At per-call cost2, the same workflow has zero minimum loss. These are supplied mathematical costs, not a Roslyn calibration.

## Retained finite comparisons

| Stage | Conditions | Zero loss | Positive loss | Nondominated root vectors | Budget coordinates |
|---|---:|---:|---:|---:|---:|
| Exploration |540|338|202|913|2820|
| Fixed confirmation |5360|3104|2256|12344|40640|

All5900 conditions succeeded; failure, timeout and invalid counts are0. A separate Cartesian composition enumerates every nondominated cost vector over full dirty-mask policy histories, without clipping history counts or using the terminal regret recurrence. Its coordinatewise minima agree with the informed game values; its minimum worst additive loss agrees with the negative threshold root. Every emitted policy attains that loss. Four specific corrupted claims are detected in each stage. These are authored inputs and specific consistency controls, not general defect coverage or mechanically checked proofs. The fixed confirmation follows the exploration and uses the same four selected job types, including a dirty set whose minimum write count exceeds its job's saturation count. Neither stage generated native timing measurements.

The [constructor and selector](evidence/RESUMED_20260910_0343/workflow_uniform_regret_02/regret_compile.py) import the preserved threshold constructor. The selector's API returns a ready job and accepts an observed dirty mask. The study contains complete inputs, raw outcomes, threshold tables and policy vectors, together with the preserved preparation failure and exact restoration receipt.

Run standard stage37 from the repository root:

```sh
python3 -B charged/reproduce.py workflow-regret --out work/workflow-regret
```

The stage recomputes both fixed input lists, all5900 outcomes and all5900 exported vector/threshold files, then checks exact bytes against the archive. It does not collect a new experimental population. All preceding standard stages remain available through `charged/reproduce.py all`. The whole-kernel retained-record interface and source-level merge costs remain separate; this result does not solve their general minimax-loss problems or establish application demand.

# Workflow minimax additive loss: outcome

For the fresh-preparation partial-repair workflow interface, the threshold constructor also computes the exact minimum uniform additive loss: delta* = -Theta(J,r,0). Shifting the comparator target by delta shifts every threshold by the same amount, and yields an executable policy that guarantees cost at most K(B)+delta for every finite write budget without receiving B. The mathematical argument is in PROOF.md. This is a model-specific use of minimax thresholds, not a new general game-solving principle, a closed form for arbitrary workflows, or a model of Roslyn rebase.

The initial540-condition exploration and the subsequent fixed5360-condition confirmation both agree exactly with separate Cartesian enumeration of nondominated full observation-history policy cost vectors. The checker enumerates budget-cost vectors without clipping observed counts or using the terminal regret recurrence. Coordinatewise minima recover the informed curve; minimizing the maximum difference across coordinates recovers the uniform loss. All emitted policies attain the stated bound over full dirty-mask alternatives.

| Stage | Conditions | Zero loss | Positive loss | Nondominated root vectors | Budget coordinates |
|---|---:|---:|---:|---:|---:|
| Exploratory |540|338|202|913|2820|
| Fixed confirmation |5360|3104|2256|12344|40640|

All5900 conditions are SUCCESS; FAILURE/TIMEOUT/INVALID are0. Four specific corrupted claims are rejected in each stage. These are consistency controls, not general defect coverage. The inputs are authored, including a footprint family with c(D)>sigma; no native/timing observations were generated. The fixed confirmation is post-exploration and uses the same chosen types, not held-out input provenance. Both inputs and code were recorded before their execution.

For an example already in the paper's workflow family, let A have singleton component weights(1,2), C have one component of weight1, require A before C, use r=1 and kappa=1. The informed curve is2,3,5,5,6 at budgets0,1,2,3,>=4. No common exact optimum exists, but minimum uniform additive loss is1. The emitted policy has curve2,4,5,6,6 (constant thereafter), attaining that loss. At kappa=2 the same workflow has zero minimum loss, recovering the existing common-optimal example. Costs are supplied mathematical units.

Preparation failure preserved: a namespace collision stopped the first new command at mkdir before science execution. Temporarily replaced plan/proof bytes were restored from their hash-matching public archive and all13 existing namespace files were verified. The new study resides in this distinct namespace; PREPARATION_COLLISION01.json records the incident. No old input, output or adverse result was changed.

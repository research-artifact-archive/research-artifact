# Modeling an update

The quickest executable input is the two-replica [Rolling model](../results/granularity/e6/rolling/v1/inputs/rolling_n02_m01_k01.json). The complete [finite adapter schema](../results/granularity/e6/common/SCHEMA.md) explains every field; `witness.schema.json` gives the structural schema. The inherited FSP frontend is illustrated by [GSM_FG.lts](../tool/models/GSM_FG.lts).

1. Declare each component's old and new finite transition systems, ordinary actions and controllability. A component that does not own an ordinary action stutters under the product rule.
2. Give local transfer domains and **all** possible target states. An omitted source has an empty transfer domain. Nondeterministic outcomes are adversarial; do not keep only a successful outcome.
3. Declare old, new and interval safety testers, their lifetimes and their initial obligations. State each initializer explicitly: an activation-scoped obligation constrains behavior from its start, while a history-dependent residual must represent the admitted prior histories. The artifact does not infer which interpretation matches a real system or establish actual activation-observation conformance.
4. Supply strict precedence constraints only when the contract needs them. Requirements stop and start through explicit boundary events; interval requirements activate at entry.
5. Supply both fixed endpoint controllers, their reachable products/projections and loadable new states. Validate the whole admitted old-entry set rather than only one physical initial state.
6. Run the fine model, then explicit merged controls as appropriate. A merge that collapses strict precedence or noncommuting monitor observations is INVALID, not LOSS.

WIN gives a finite-completion policy relative to this model, not a runtime integration implementation. LOSS means some admitted entry cannot guarantee the specified safe completion. Timeout and OOM are unresolved observations. In the viewer, inspect requirement states and pending actions alongside the physical states; a path through physical states alone does not show requirement lifetime correctness.

For reusable family generators, start with `results/granularity/e6/rolling/`, `canary/`, `policy/`, and `db_rolling/`. Use their canonical versions documented in the main README. Do not overwrite the distributed inputs or count a modified example as an unchanged reproduction.

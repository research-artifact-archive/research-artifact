# Deephaven policy comparison: first exploratory result

All84 native cells completed successfully and passed the separate author trace checker. Five deliberately corrupted trace controls were rejected. Four unchanged upstream regression tests also passed. The first matrix build/run took32.44seconds; the additional regression build/run took15.99seconds. These include Gradle work and are not per-policy timings.

The experiment instruments the pinned upstream snapshot program and adds an opt-in retry-policy hook. It uses a fixed31-row forest, three expansion directives,16 viewport rows, value-only updates and actual update-graph cycles. Selected operation caps are K4 and V176; each observed complete body used K4 or V104. These observations are not a proof that all allowed prefixes satisfy the caps.

Across84 cells there were60 actual update cycles and90 actual inconsistent bodies. Every compiled trace respected its exact chain-DP decisions and its conservative charged-cap guarantee. Every returned viewport matched a separately reconstructed DFS and the source epoch of its successful body.

| Comparator | Compiled lower cost | Equal | Compiled higher cost |
|---|---:|---:|---:|
| upstream | 12 | 9 | 0 |
| threshold | 6 | 15 | 0 |
| protected | 19 | 2 | 0 |

Counts compare21 matched price/schedule cells per comparator. They do not weight any deployment population. Costs are selected work + lambda×selected work while protected. Scheduler work, waiting, allocations, initial tree construction and total CPU work are outside this logical objective. Environment actions are triggered by unprotected bodies; a policy can prevent remaining actions from being triggered. Thus executed cycles may differ across policies. The supplied q is a common maximum; the threshold policy does not receive it.

| lambda | Schedule | Compiled | Upstream2 | Threshold | Always protected |
|---:|---|---:|---:|---:|---:|
| 1 | none | 108 | 108 | 108 | 216 |
| 1 | k_full | 112 | 112 | 116 | 216 |
| 1 | v_full | 212 | 212 | 316 | 216 |
| 1 | v_split | 212 | 420 | 316 | 216 |
| 1 | k_split | 116 | 120 | 116 | 216 |
| 1 | v_two_split | 216 | 420 | 316 | 216 |
| 1 | k_full_v_split | 216 | 424 | 324 | 216 |
| 3 | none | 108 | 108 | 108 | 432 |
| 3 | k_full | 112 | 112 | 112 | 432 |
| 3 | v_full | 212 | 212 | 212 | 432 |
| 3 | v_split | 316 | 628 | 316 | 432 |
| 3 | k_split | 116 | 128 | 116 | 432 |
| 3 | v_two_split | 420 | 628 | 732 | 432 |
| 3 | k_full_v_split | 320 | 632 | 320 | 432 |
| 10 | none | 108 | 108 | 108 | 1188 |
| 10 | k_full | 112 | 112 | 112 | 1188 |
| 10 | v_full | 212 | 212 | 212 | 1188 |
| 10 | v_split | 316 | 1356 | 316 | 1188 |
| 10 | k_split | 116 | 156 | 116 | 1188 |
| 10 | v_two_split | 524 | 1356 | 524 | 1188 |
| 10 | k_full_v_split | 320 | 1360 | 320 | 1188 |

The unknown-budget threshold matches the compiler in many cells; its presence rules out a claim that exact synthesis is indispensable for these native instances. For lambda3 and one split V cycle, both cost316 while the upstream two-attempt fallback costs628. For lambda3 and up to two split V cycles, compiled costs420 versus732 for threshold and628 for upstream. These are declared weighted logical costs on an author-chosen finite matrix, not measured CPU speedups.

The upstream MAX_ROW_KEY nonprogress counterexample, the failed compilation and resource-leak diagnostic from earlier packets, and the previous ALL-modified-column driver are unchanged. General exposed-guard equality remains unresolved and is not implied by this two-stage example. Source-wide prefix bounds, a wider structural stress matrix, actual application budget interpretation, and the closest-work comparison remain substantive adoption obligations.

The native controller in this first development matrix computes the two-stage scalar DP directly in Java. It has not yet imported a policy/certificate emitted by the paper's all-budget curve compiler. Thus this packet validates the native strategy hook and cost ledger, not an end-to-end deployment of the compact compiler. A further same-information baseline (per-job remaining-budget rule) and actual compiler export/import are planned before such a claim.

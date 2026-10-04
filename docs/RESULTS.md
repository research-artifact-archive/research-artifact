# Results and interpretation

All results below are saved observations, not newly selected measurements. Counts include the negative and unresolved cases. The [paper snapshot](../paper/main.pdf) and [integrated supplement](../paper/supplementary_material.pdf) state the formal assumptions; the tables below explain what the evidence does and does not establish.

### Why fine granularity can matter

Five constructed families expose constraints under which merging can lose feasibility; a separate analytical contract shows the reverse direction (Technical Appendix D.2). They are models inspired by update patterns, not measurements of deployed products or estimates of how often the problem occurs in practice.

| Family | Mechanism and result | Interpretation and boundary |
|---|---|---|
| **Rolling** | 70 startup-availability threshold cells agree with `k ≤ n − m`, where `k` is the group starting together and `m` the required ready capacity | The spare capacity limits safe update granularity; reports and the readiness model are assumptions |
| **Canary** | 15/15 local-versus-merged pairs separate when all transfer outcomes, uncontrollable reports and recovery are modeled | A successful branch alone is insufficient; recovery behavior is supplied in the model |
| **Policy v2** | Audit overlap and role nonoverlap require opposite requirement-boundary orders | Merging the individual boundaries in the specified FG contract loses; this is an internal boundary-order comparison, not an impossibility claim about alternative DUCS encodings or a service-continuity guarantee |
| **DB-Rolling v2** | Secondary-first maintenance separates; no-slack controls are both LOSS | Granularity helps only when the contract provides a safe intermediate state |
| **Rolling+Audit** | Transfer merging can lose under the startup-capacity constraint, while requirement-boundary merging wins in the same family | The outcome depends on which commands are merged and on the declared requirement scopes |

The main E6 denominator is **55 pairs: 33 fine-WIN/merged-LOSS, 11 both-LOSS, 10 both-WIN, and 1 incomplete pair**. It also includes Audit, Threads and PC2 cases. The 20 scale pairs, 12 Canary assumption-control pairs, nine Cell reference pairs, and additional PC2 budget attempts are separate; they are not added to 55. The 70 threshold cells and 15 Canary pairs above overlap these analyses and are not 85 independent applications. Canonical versions are **Policy v2** and **DB-Rolling v2**. Earlier versions, rejected checker attempts, counterexamples and failed preparation attempts remain available.

For PC2, the fine model wins but the measured merged attempts time out, including extended budgets. A separate structural argument identifies a joint-calibration safety obstruction. That argument is **not** a measured solver LOSS. Joint transfer domains exist in all 81 independently checked old-product states, so empty transfer domains are not the explanation.

See [all granularity evidence](../results/granularity/), [main pair index](../results/granularity/e6/results_index.csv), [independent game checks](../results/granularity/e6/independent/), and [Rolling's analytic check](../results/granularity/e6/rolling/ANALYTIC_CHECK.md).

### Important null results and diagnostics

| Experiment | Complete reported outcome | What it supports |
|---|---|---|
| **E1: inherited Base/R1 merging** | 54 comparisons, **0 decision changes**; discovered states decrease in 44 and are unchanged in 10 | The inherited models do not demonstrate necessity of fine granularity; the constructed families address a different evidence gap |
| **E2: full construction with UC pruning** | Mac: 16 WIN, 1 LOSS, 10 TO; separate Xeon campaign: 15 WIN, 12 TO | Helps distinguish full construction and UC pruning; this is an incomplete two-factor comparison because on-the-fly exploration without UC pruning is not implemented. Host, budget and repetition differences prevent pooling |
| **E4: finite fixtures / Cell** | Controlled separations; corrected Cell series has 45 trials; original 30 input errors are retained | Mechanism-level evidence, not deployment prevalence; input errors are not LOSS |
| **E5: physical-initial-only transfers** | 18 pairs: **0 separations**, 6 both-LOSS, 2 both-WIN, 10 incomplete; 54 planned jobs: 4 WIN, 12 LOSS, 9 TO, 29 NOT_RUN_DEADLINE | Restricting transfer domains does not automatically create a useful witness under UC quiescence |
| **E6: constructed families** | 55 pairs as above; positive cases and null/negative controls all retained | Establishes that the modeled distinctions can change solvability under the stated assumptions |

[E1/E2 data and scripts](../results/ablation/) and [E4/E5 data and scripts](../results/granularity/) preserve their separate budgets and denominators. We do not describe an independently unidentified “E3” campaign as completed, or present E1–E6 as a single homogeneous experiment.

### Fixed-budget solver comparison: 27 contracts

The fixed comparison uses nine adapted inputs derived from eight source models, with three contracts each, a **64 GiB Java heap** and **1,200-second whole-JVM cap** on the recorded Xeon host. Conditions that complete consistently have **five repetitions**; first-stage failures remain single attempts. The following are same-FG-game methods:

| Method | WIN | LOSS | TO | Decided |
|---|---:|---:|---:|---:|
| **Lazy** | 25 | 1 | 1 | **26/27** |
| **Eager** | 17 | 0 | 10 | **17/27** |
| **Update-first** | 23 | 1 | 3 | **24/27** |
| **Direct-Full** | 14 | 0 | 13 | **14/27** |

Lazy materializes controllable buckets on demand; Eager queries them at expansion time. Both preserve all outcomes of a chosen bucket and use UC priority. Eager can stop before the full game is discovered. Update-first changes the controllable-action order. Direct-Full is an in-house full-construction comparator for the same FG objective, including fixed-new-controller handover; it is not an external DUCS implementation.

The supplementary cost records retain **sampled peak JVM resident memory (RSS, MiB)** for all 14 completed Lazy/Direct-Full pairs. All 14 Lazy medians are lower: Direct-Full/Lazy ratios range from **1.01 to 36.94**, with median **1.95**. Each range spans the five trial peaks. These are Windows JVM-process working-set samples taken every 0.1 seconds over the whole run, including frontend and endpoint preparation, not heap occupancy or solver-only memory. Some ranges overlap, so this is not a claim of statistically significant separation in every pair. Other methods can use less memory: Eager does so in 1/17 completed pairs and Update-first in 12/24. The 13 Direct-Full timeouts are excluded from completed-pair medians and remain in the all-contract results.

Main Figure 3 compares Lazy and Eager states and solver time for all 27 contracts, keeping unresolved Eager and Lazy outcomes visible. Both variants use the same UC pruning. Direct-Full pairs and RSS remain in the supplement.

The result supports completion of more fixed-budget cases by Lazy. It does **not** say Lazy is always fastest: **Update-first has a smaller solver-time median in 8/24 completed comparisons**. In the Travel scaling grid the three on-the-fly methods each finish **20/48** conditions and Direct-Full finishes **18/48**. Other scaling grids, states, queries, RSS and timings are included in the [generated tables](../paper/source/build/generated/) and [scaling analyses](../results/performance/analysis/).

**Separate legacy reference:** the measured traditional paths in the saved DUCS implementation fork give **9 WIN, 13 OOM, and 5 author-instrumentation capture stops (N/M)**. They solve a different subsequent-control objective; preservation of the fixed new controller's continuations was not compared. Do not interpret that row as a same-objective speed comparison. Published DUCS permits staged reconfiguration inside its new environment. The analytical Cell encodings establish neither a general objective-preserving translation nor an encoding-effort advantage, and were not evaluated through native DUCS/GR(1) solvers.

<details><summary><b>All 27 fixed-budget contracts (solver medians in seconds; expand)</b></summary>

| Model / contract | Lazy | Eager | Update-first | Direct-Full |
|---|---:|---:|---:|---:|
| gsm / base | W 0.0224 | W 0.0332 | W 0.0233 | W 0.0416 |
| gsm / r1 | W 0.0228 | W 0.0348 | W 0.0243 | W 0.045 |
| gsm / r2 | W 0.0201 | W 0.0281 | W 0.0225 | W 0.0327 |
| industry / base | W 0.19 | W 14.5 | W 0.542 | W 154 |
| industry / r1 | L 562 | TO | L 461 | TO |
| industry / r2 | W 1.15 | W 2.96 | W 0.455 | W 28 |
| metasocket / base | W 0.0149 | W 0.0302 | W 0.0165 | W 0.0408 |
| metasocket / r1 | W 0.0136 | W 0.0278 | W 0.0147 | W 0.0426 |
| metasocket / r2 | W 0.0152 | W 0.018 | W 0.0154 | W 0.024 |
| powerplant / base | W 0.0463 | W 0.487 | W 0.052 | W 1.85 |
| powerplant / r1 | W 0.125 | W 1.08 | W 0.152 | W 5.51 |
| powerplant / r2 | W 0.18 | W 0.251 | W 0.114 | W 1.01 |
| productioncell_arms1 / base | W 0.0741 | W 26 | W 0.886 | W 157 |
| productioncell_arms1 / r1 | W 0.0793 | W 188 | W 3.15 | TO |
| productioncell_arms1 / r2 | W 6.16 | W 12.2 | W 1.17 | W 77.8 |
| productioncell_arms2 / base | W 2.61 | TO | TO | TO |
| productioncell_arms2 / r1 | W 2.6 | TO | TO | TO |
| productioncell_arms2 / r2 | TO | TO | TO | TO |
| railcab / base | W 0.169 | TO | W 2.26 | TO |
| railcab / r1 | W 3.18 | TO | W 6.74 | TO |
| railcab / r2 | W 15.5 | W 38.7 | W 4.16 | W 283 |
| surveillance / base | W 2.01 | TO | W 2.63 | TO |
| surveillance / r1 | W 18.6 | TO | W 126 | TO |
| surveillance / r2 | W 37.1 | TO | W 16.1 | TO |
| workflow / base | W 0.111 | W 508 | W 0.116 | TO |
| workflow / r1 | W 0.325 | TO | W 0.215 | TO |
| workflow / r2 | W 16.1 | W 23.9 | W 3.18 | TO |

`W` = WIN, `L` = LOSS, `TO` = timeout. Times are solver medians from five complete repetitions, not whole-JVM times. The original interrupted Workflow/R2 Direct-Full run and its separately recorded same-setting TO are both preserved. The full CSV also includes state/query/policy counts, process RSS, all five timings and the separate legacy reference.

</details>

### Extended budgets: ext1–7

These are follow-up diagnostics with their own single-run budgets. They **do not replace the fixed table, change its five-run medians, or turn censored observations into ratios**.

| Campaign | Result | Interpretation |
|---|---|---|
| **ext1**: Travel frontier | 4 WIN | Some fixed-budget boundary cases are solvable with more time |
| **ext2**: Direct-Full CPU extension | 1 WIN, 1 LOSS | PC1/R1 and Industry/R1 decisions agree with fixed Lazy |
| **ext3**: next Travel conditions | 1 WIN, 4 TO | Extra time helps one further case; four remain unresolved |
| **ext4**: 200 GiB heap | 1 WIN, 10 TO, 1 OOM | A larger heap and longer time limit still leave unresolved cases |
| **ext5**: Travel, 200 GiB | 2 TO, 2 SKIP | Skipped conditions are explicitly unexecuted, not timeouts |
| **ext6**: Legacy, 200 GiB / 3,600 s | 11 OOM, 7 instrumentation-profile stops; 0 decisions, 18 attempts | Profile stops are N/M, not evidence of a general Legacy capacity limit |
| **ext7**: Eager, 200 GiB / 7,200 s | 3 WIN, 1 LOSS, 5 TO, 1 OOM; 10 attempts | Four decisions match fixed Lazy; three WINs resolve cases where the 200 GiB Direct-Full extension remained undecided |

ext1–5 comprise **27 planned conditions: 7 WIN, 1 LOSS, 16 TO, 1 OOM, 2 SKIP, 0 pending**. All seven campaigns have their [original configuration and per-run data](../results/performance/raw/), including stderr, environment and negative outcomes. The [extended-budget CSV](../paper/source/build/generated/ext-budget.csv) records each condition’s heap limit and 7,200-second whole-JVM cap for ext1–5.

The three completed ext7 WINs are Railcab/base, Workflow/R1 and Surveillance/R2; the LOSS is Industry/R1. Eager discovers approximately **60–68,186 times** as many states as fixed Lazy on those three WINs. These are discovered-state counters, **not full-game sizes**, and Eager need not visit the same states as Full+UC. ext7 timings are single-run values, not medians. RSS is sampled process memory, not Java-heap occupancy. TO/OOM cells have no final state count and receive no state ratio.

### Correctness and scope checks

The saved correctness suite contains **46 models** with independently derived expectations: **18 WIN, 24 LOSS, 4 INVALID**, tested in 92 jobs. The formal witness suite adds **14 jobs: 10 WIN, 4 LOSS**. The no-Java reproduction also checks drawn witness edges and transfers, 27 declared contract sizes, completion ranks, frontend lookup, quiescent goals, loadable targets and a separate contract-repair example. That repair wins from all 131 admitted roots while preserving the original 42 losing entries as a separate result; it does not replace the original contract's LOSS.

The core finite E6 independent checker reconstructs endpoint products and whole games in Python, with saved audits of 182 completed core trials over 148 distinct input/merge games and 12 rejected corrupt-certificate controls. Additional checks cover the newer canonical versions and controls. The Java native checker shares frontend/semantic code with the solver; all implementations and independent checks are from the same author team. These checks increase confidence but do not establish implementation correctness for every possible input.


## Preparation and initialization costs

[All-contract preparation data](../paper/source/build/generated/rq3-preparation.csv) retain the definition and adapter intervals, activation-closure counts, five-run ranges and missing cells from 405 completed runs. For example, Lazy PC2 Base/R1 adapter medians are 13.872/14.221 s, compared with solver medians 2.609/2.602 s. The adapter interval includes more than closure construction. Workflow has 52,608 activation-closure tuples; these are not discovered update-game states. S4.3 distinguishes these global preparation costs from lazy game exploration.

## Saved-evidence analyses

[The claim map](CLAIMS.md#rq2-initialization-and-saved-policies) separates accepted lookup cells, actual saved activation keys, and completeness of the accepted activation domain. [Threads expansion](../paper/source/evidence/threads_saved_serialization/) covers ten saved policies; [Railcab](../paper/source/evidence/railcab_saved_activation/) covers two saved policies; [command observation](../paper/source/evidence/command_observation/) retains both its analysis and negative controls. These additions analyze preserved inputs and policies and do not add performance measurements.

Return to [results by question](../results/README.md), [the claim map](CLAIMS.md), or [the paper reading routes](../README.md#find-the-evidence-for-a-claim).

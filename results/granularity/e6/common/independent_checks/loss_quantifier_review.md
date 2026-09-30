# LOSS quantifier and counterstrategy review

Reviewed read-only on 2026-09-29. No solver, input, raw result, certificate, or reviewed script was changed. No Java process or full experimental game enumeration was run for this review.

The reviewed implementations have the same LOSS quantifiers as the fixed E1 certificate checker. No algorithmic quantifier defect was found. Two explanatory phrases in the extractor should be narrowed as described below; neither changes its checked response graph or a measured decision.

## Reviewed sources

Paths below are relative to `experiments/witness_20260929/e6/`, except the Java references.

| Source | SHA-256 |
|---|---|
| `independent/check_games_v3.py` | `f7f155357699e15aeae6657b6f02849ade82da14c6015ffa8c674ce49d15b0f8` |
| `independent/extract_counterstrategies.py` | `88885744d6c2b87b82a70a28a7eef573f358ea6c9d0c24e825b67f3dd538334b` |

Java references are in the read-only E1 source directory `experiments/ablation_20260928/source/mtsa/src/main/java/ltsa/updatingControllers/otf/`. The fixed E1 JAR SHA is `ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5`.

## Local quantifiers

Let `L` be the returned losing certificate region, `U(q)` the enabled uncontrollable events, and `C(q)` the enabled controllable events, including eligible update events. Enabled means a nonempty `Post` bucket. The checked obligations are:

- `L ∩ Q0 ≠ ∅` and `L ∩ Goal = ∅`.
- Unsafe states in `L` need no successor obligation: safety has already failed.
- At a safe state with `U(q) ≠ ∅`, there exist an event `u ∈ U(q)` and an outcome `q′ ∈ Post(q,u) ∩ L`.
- At a safe state with `U(q) = ∅`, for every `c ∈ C(q)` there exists an outcome `q′ ∈ Post(q,c) ∩ L`.
- If both sets are empty, the last condition is vacuous. This is a safe non-goal deadlock and loses strong completion.

These are exactly the Java obligations in `OtfDucsCertificateChecker.java:144–188` and the Python obligations in `check_games_v3.py:241–249`. A bucket need not have *all* its outcomes in `L`; the adversary can select one losing outcome. Conversely, without UC it is insufficient for only one controller event to have a losing outcome: every enabled controller event must have one.

The independent attractor uses the dual conditions (`check_games_v3.py:192–207`): all outcomes of all enabled UC buckets must already be ranked, or, when no UC is enabled, at least one controller bucket must have all outcomes ranked. `enumerate:183–190` expands only safe, non-goal states, so unsafe and goal states are terminalized consistently with these objectives.

## UC priority does not erase ordinary controllable Post

`FineGrainedSuccessorOracle.java:199–206` returns normal-action Post before testing the UC guard; the guard applies to update actions. Likewise, `check_games_v3.py:155–159` first retains all enabled normal buckets and suppresses only the update-action construction when UC is enabled. The goal test also excludes enabled UC (`FineGrainedUpdateProblem.java:326–331`; Python `goal:146–151`).

At a UC state the canonical WIN certificate suppresses controllables and retains all UC outcomes (Java checker `100–112`; Python `230`). For LOSS, selecting one UC event and one losing outcome describes an admissible adversarial scheduling choice. It does not assert that the physical ordinary controllables have become disabled. There is no fairness assumption that would force the scheduler eventually to choose an enabled controllable instead.

This distinction is visible in the saved Canary merged certificate: state 1 has UC `reportB_2` and ordinary C `restart_1`; state 2 has UC `reportB_1` and ordinary C `restart_2`. Both buckets remain present in independent Post. The environment can choose the remaining report before recovery. Descriptions such as “ordinary recovery is disabled until all reports finish” would be false for these states; “the environment can force the reports before recovery” is supported.

## All initial states for WIN, a losing initial state for LOSS

The Python interpreter constructs `Q0` from **every reachable old endpoint state**, not just the old endpoint LTS initial node (`check_games_v3.py:93–104`). A WIN verdict requires every root to belong to the strong attractor (`267`). A WIN certificate includes all roots and exactly the strategy-reachable rank domain (`217`, `236–240`), matching Java `OtfDucsCertificateChecker.java:38–42,132–139`.

A LOSS certificate needs only a nonempty intersection with `Q0` (Java `147–150`; Python `242`). One losing possible hot-swap state refutes a guarantee over all hot-swap states. This does not establish that every initial state loses. Nor is `certificate_states` necessarily the size of the entire game's losing region. The extractor correctly starts its response reachability from `Q0 ∩ L` (`extract_counterstrategies.py:56–60`). Its `initial_states_in_region` field is the list of certified losing root IDs, not the full initial-state set.

For the six saved reports in `independent/counterstrategies_with_controls/`, the observed numbers of all roots / certified losing roots are: Canary product 1/1, Policy global boundaries 2/2, DB joint-secondary 1/1, DB no-slack 1/1, Threads saturated 8/8, and Canary no-recovery 1/1. These particular reports happen to cover every root; the implementation correctly permits partial-root LOSS certificates.

## Extracted response graph

The construction (`extract_counterstrategies.py:29–42`) selects one enabled UC event/outcome at UC states. At other safe states it selects one retained outcome for **each** enabled controllable bucket. It records deadlocks and stops at unsafe states. The separate checking loop (`43–55`) verifies actual Post membership, membership in `L`, exclusion of goals, and the required UC/C event coverage. Thus the graph supplies adversarial responses to every possible controller event at no-UC states, rather than exhibiting just one losing path.

From each listed losing root, following this response rule keeps the execution outside goal; safety may fail, a safe deadlock may be reached, or an infinite safe goal-avoiding execution may occur. A controller that disables every C event at a no-UC state simply deadlocks outside goal. The graph is explanatory postprocessing of a checked E1 region, not a returned E1 counterstrategy object and not an additional synthesis trial.

The reverse search at lines 61–67 is **existential** reachability of unsafe states in the chosen response graph. Therefore:

- A state outside `can_reach_unsafe` has no path to unsafe under this selected response graph. If response-reachable, it witnesses safe goal avoidance or deadlock.
- Membership in `can_reach_unsafe` only establishes an available graph path. It does not prove that unsafe is forced against every controller event choice.
- Zero `response_reachable_safe_states_without_any_unsafe_path` does not rule out a safe infinite path. For example, the saved no-recovery report has zero such states; this does not contradict the separately checked safe non-goal explanatory trace.
- `unsafe_states` and `safe_deadlock_states` describe the entire supplied region; `response_reachable_states` explicitly identifies the part reachable under the selected response rule. Do not silently describe all region states as response-reachable.

Two wording corrections are recommended, without altering this reviewed code:

1. Line 61, “Backward existential reachability distinguishes forced obstruction types,” overstates the search. Use “Backward existential reachability identifies states with no path to unsafe in the selected response graph.”
2. Line 73, “finite executions either reach unsafe/deadlock or continue forever outside goal,” mixes finite and infinite executions. Use “Every maximal response execution either reaches unsafe or a non-goal deadlock, or is infinite and remains outside goal; no fairness is assumed.”

## Focused executable checks

In-memory finite abstract graphs exercised the actual v3 `solve` and `certificate` methods. These are validation fixtures only, not witness inputs or experimental trials. All six expectations passed:

| Fixture | Expected and observed result |
|---|---|
| UC self-loop plus ordinary controllable escape to goal | LOSS region accepted; the C escape does not defeat adversarial UC scheduling. |
| One C bucket with one goal outcome and one losing-loop outcome | LOSS region accepted; adversarial outcome quantification is existential for LOSS. |
| Two C events, one losing-loop event and one all-goal escape | Proposed LOSS region rejected. |
| Two initial states, one goal and one UC losing loop; certificate contains only the latter | LOSS certificate accepted; exactly one of two roots is winning. |
| Safe non-goal deadlock | LOSS certificate accepted. |
| UC event whose only outcome is goal | Proposed LOSS region rejected. |

The saved six response reports were also read to check their root counts and enabled UC/C overlap against v3 Post. This review does not extend the independent interpreter to the FSP-specific PC2 export or claim a new complete-game measurement.

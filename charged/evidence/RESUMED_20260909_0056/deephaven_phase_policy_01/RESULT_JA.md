# Cycle-phase finite-DP policy: exploratory result

All108 new native cells succeeded (17.24s build/run) and passed the separate author trace checker. Six corrupted traces were rejected. The native runs executed74 cycles and101 inconsistent callbacks. The source hooks are unchanged from prefix_import_02; no repeated regression is needed for adding this test class.

The finite DP over all nonempty clock-boundary sequences confirms an initial lambda3/q2 cap of420 for the synchronized driver, compared with424 from the flat2q all-budget compiler. It is a finite r-sized DP, not an all-budget compiler import. The proposed simplified recurrence agreed on the three fixed price profiles for both phases, all4 unfinished masks, and r0..6 (56 states/profile); this finite check alone is not a proof.

The pre-outcome fixed-script cost prediction332 was **not realized**. On cross_stage/lambda3, the phase policy cost124: K4 fails on START1, K16 completes protected after draining cycle1, and V104 succeeds. The script's V1 COMPLETE is now a recorded SKIP_CLOSED_CYCLE; its later START2 was tied to V2, which is never reached. Only one cycle executes, versus two for the old flat-budget policy's424 trace. The predicted332 was a bound for an adaptive continuation using the remaining cycle, not the exact outcome of this fixed attempt-indexed script. This distinction is preserved; 124vs424 must not be described as a reduction under identical realized writer activity.

All policies see the same script rule and q bound; control decisions can suppress later update requests. These are adversarial-script comparisons, not replay of the same completed update workload. The model-value reduction420vs424 is a separate, small guarantee comparison. No script in the current matrix was deliberately added after outcomes to attain420. A new declared-q/quiet script or policy-dependent adversary would require a new input protocol.

| Phase DP / baseline | Lower | Equal | Higher |
|---|---:|---:|---:|
| phase_protected_tie / phase_local_budget | 12 | 22 | 2 |
| phase_protected_tie / curve_protected_tie | 11 | 23 | 2 |
| phase_protected_tie / curve_fast_tie | 2 | 32 | 2 |
| phase_protected_tie / local_budget | 12 | 22 | 2 |
| phase_protected_tie / upstream2 | 18 | 18 | 0 |
| phase_protected_tie / unknown_budget_threshold | 12 | 21 | 3 |
| phase_protected_tie / always_protected | 33 | 3 | 0 |
| phase_fast_tie / phase_local_budget | 12 | 22 | 2 |
| phase_fast_tie / curve_protected_tie | 11 | 23 | 2 |
| phase_fast_tie / curve_fast_tie | 2 | 32 | 2 |
| phase_fast_tie / local_budget | 12 | 22 | 2 |
| phase_fast_tie / upstream2 | 18 | 18 | 0 |
| phase_fast_tie / unknown_budget_threshold | 12 | 21 | 3 |
| phase_fast_tie / always_protected | 33 | 3 | 0 |

There are36 matched price/script cells. Both phase-DP tie choices realize the same costs in this matrix. They are more expensive than the same-phase-information local rule in2cells; minimax optimization does not imply pointwise script dominance. All cells and comparisons remain in SUMMARY01.json.

NATIVE_SCOPE_ADDENDUM.md limits this result to synchronous notification+completion: an unrestricted notification while still Updating needs additional state and a separate proof. There is also no standalone wait or acquire/release control action. Thus this exploratory improvement does not establish a whole-program or unrestricted native optimum, or replace the paper's atomic-callback normal-form theorem.

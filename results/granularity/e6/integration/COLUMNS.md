# Integration CSV columns

`results_index.csv` has one main comparison per constructed family/parameter tuple. The checked core is built by `integration/build_handoff.py`; `integration/build_campaign_index.py` adds every preregistered pair, including incomplete cells. The latter is the campaign refresh command and checks source CSVs against raw JSON and certificate hashes. Missing measurements must not be filled from expected values.

- `family`, `params`: family and explicit parameter tuple; `mechanism`: M1 (unreachable joint premise), M2 (readiness/availability), M3 (adversarial outcome/recovery), M4 (opposing boundary orders).
- `contribution`: L1 (local WIN / all-at-once LOSS), L2 (set-valued transfer), L3 (Lazy/Full exploration), boundary, or negative_control. These are evidence labels, not independent counts.
- `anchor`: verified primary-source URL(s); `location`: canonical version directory relative to e6.
- `fine_decision`, `merged_decision`, `class`: measured decisions and `witness` (WIN/LOSS), `both_loss`, or `both_win`. Other/incomplete outcomes must be separately retained and cannot enter a completed-pair count.
- `comparison`: E1 merge mode used in this pair. Policy uses boundaries; current other main rows use transfers.
- `cert_checks`: independent endpoints, E1 certificate/Link (WIN only), family mechanism audit, and generated/E1 reachable-Post equality status.
- `fine_job`, `merged_job`, `direct_full_job`: exact IDs under the row's `location/raw/series/`.
- `fine_states`, `merged_states`, `direct_full_states`: states discovered during synthesis, not endpoint or Link-product states.
- `fine_rank`, `direct_full_rank`: maximum rank in the returned WIN certificate; empty for LOSS. Ranks need not be the optimal completion bound or equal between solvers.
- `fine_loss_certificate_states`, `merged_loss_certificate_states`: checked discovered losing-certificate cardinality; empty for WIN. Not a maximum whole-game losing-region claim.
- `fine_queries`, `merged_queries`, `direct_full_queries`: successor queries during synthesis. A nonempty bucket can have several outcomes, so queries, enabled buckets and materialized transitions are distinct.
- `fine_solver_seconds`, `merged_solver_seconds`, `direct_full_solver_seconds`: actual Mac synthesis wall-clock seconds, one trial; descriptive only. Preparation and checking/Link time are separate in the source summaries.
- `fine_input_sha256`, `jar_sha256`: exact measured input and fixed solver JAR digest. Coarse hashes, adapter/classes and schedule hashes are in per-family freeze files and summaries.
- `loss_reason`: diagnosis derived from the model invariant and checked losing certificate. For a both-LOSS pair, gives the additional fine-contract failure.

`integration/completed_run_counts.csv` counts the original 182 core trials only. `integration/all_registered_run_counts.csv` counts the original 393 trials across nine series plus the two explicitly authorized PC2 7,200s trials as a tenth, separate series; columns are family, total trials, WIN/LOSS/TO/OOM/ERROR/INVALID_CERTIFICATE/INVALID_INPUT/NOT_RUN/NOT_STARTED/RUNNING counts, and the exact source-summary SHA-256. Separate validation-only replays and historical failed designs are retained but are not counted as new trial cells. `integration/status.json` records source summary hashes and aggregation time. `rolling/v1/tables/threshold.csv` lists all 70 n,m,k cells, including every losing cell, separately from the 15 fine/all-at-once pairs. Source `summary.csv` files include status, expected decision and expected check, discovered/expanded states, bucket/outcome counts, all timing phases, exit status, exact input/JAR/freeze hashes, timestamps, raw result/certificate paths, and validation errors. `NOT_RUN`, TO, OOM, invalid and failed checks must remain distinct from LOSS.

## Campaign coverage and pending cells

`population` separates core examples, operational controls (Threads), the original-plant attempt (PC2), scale extensions (Rolling n7..16), and assumption controls (Canary interventions). Every frozen parameter pair is indexed before it completes. `fine_status`, `merged_status`, `direct_full_status`, and where available `generated_status` retain the source state. `class=incomplete` is outside all three completed decision categories. The additional `preregistered_mechanism` is a hypothesis/structural account, never a missing decision. `loss_reason` is not populated from a timeout. `integration/core_status.json` retains the original 34-pair core aggregation; `integration/status.json` reports current counts by population and main-comparison counts.

The PC2 fixed FSP CLI records solve plus internal check time, so `*_solve_and_internal_check_seconds` is distinct from `*_solver_seconds`, which stays blank for that route. Generated JSON-family summaries measure the latter separately. No total JVM or combined-check timing is relabeled as solver time. Every numeric field for an uncompleted synthesis stays empty.

## Added reference, budget and validation fields

`population=reference_e4` identifies nine Cell_n comparisons read from the unchanged E4 corrected series. They add index coverage for the requested main table, not E6 trials or main witnesses. `location=../e4_2_corrected` is an external dependency of the E6-only public snapshot.

`e1_merge_equivalence` records generated-coarse versus E1 full-Post equivalence only when actually checked. `NOT_GENERATED_SEPARATELY` identifies E4/PC2 contracts measured directly with E1 merge. `e1_merge_scope` explains the comparison. `independent_v3=PASS` denotes the complete independent JSON game and certificate audit; `PASS_CERTIFICATE_SCOPE` uses the v3 Post interpreter on saved certificates plus separate structural checks for large Rolling. `NOT_APPLICABLE_FSP` and `NOT_APPLICABLE_E4_SCHEMA` retain explicit limits. `independent_validation`, `_scope`, and `_report` locate the actual independent check; they do not equate an endpoint audit with a full Post reimplementation.

For PC2, `*_host`, `*_campaign`, and `*_timeout_seconds` state the selected source. The terminal authorized extended trial is used once per comparison; until termination, the original measured 1,200s status remains and `*_extended_7200_status` records progress separately. `*_original_1200_status` always preserves the old result. `*_raw_directory` locates a selected extension. TO/OOM/ERROR leave all synthesis counters empty. No cross-host timing selection is made. `threshold_max_winning_k`, `threshold_tested_k_count`, `_check` and `_source` bind Rolling main rows to all 70 grouped-transfer cells; they do not add pair counts.

## Received Xeon rows and early finalization

The selected comparison columns remain Mac observations. Added `xeon_{fine,merged,direct_full}_*` columns copy each received host cell, including whole-JVM seconds and sampled RSS; `xeon_acceptance_status` and `xeon_comparison_scope` retain provenance limits. `all_host_budget_table` points to eight separately keyed host/campaign/cap rows. Exit code and runtime class digest are unavailable in all three received raw records and are not filled. The index stays at 96 comparison rows. Trial totals are 395 Mac plus 3 received Xeon = 398; this is distinct from the 55 main comparisons. Early finalization changes only reporting eligibility; removing the added Xeon columns reproduces the pre-import index SHA exactly.

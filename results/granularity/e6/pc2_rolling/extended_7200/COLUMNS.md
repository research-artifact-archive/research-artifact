# Column interpretation

`results.csv` has exactly the two newly authorized 7200-second trials. `host_budget_comparison.csv` keeps the three original Mac/32g/1200-second trials and two Mac/32g/7200-second trials as separate rows. `xeon_plan.csv` contains plans only (`NOT_COLLECTED`), using the existing launcher's 200g/7200-second defaults; it is not a measurements table.

- `campaign`, `host`, `heap`, `timeout_seconds`, `trial`, `job_id`, `solver`, `merge`: identity of a distinct trial. `direct_full` with `merge=none` explores the fine contract fully; it is not merged-transfer synthesis.
- `status`: raw process outcome. `raw_diagnostic_decision` separately records any retained diagnostic verdict; an invalid or timed-out process is never promoted from it.
- `states_discovered`, `successor_queries`, `materialized_transition_outcomes`: counters emitted by fixed E1 and cross-checked with the diagnostic summary. Outcomes are not distinct buckets. `enabled_buckets` is blank because the fixed CLI does not directly instrument it.
- `worst_completion_rank`: maximum rank of the returned strategy-reachable WIN certificate, not necessarily an optimal bound. `losing_region_states`: returned discovered-state LOSS certificate size, not the whole-game losing-region cardinality.
- `certificate_states`, safe/unsafe partition counts, and initial-state counts come from the retained diagnostic. WIN must contain all initial states; LOSS needs at least one initial state.
- Native checker columns refer to the original E1 same-semantics certificate/Link validation. Independent local-plant/controller domain checks are separate validation artifacts and are not another update solver.
- Preparation and solve-plus-internal-check seconds come from CLI milliseconds. `whole_jvm_seconds` includes process preparation/checking and any timeout termination grace; the enforced whole-JVM deadline is `timeout_seconds`. All Mac times are reference measurements, not cross-host comparisons.
- Incomplete, TO, OOM or invalid-result counters remain blank. `expectation_check` does not overwrite a contrary verdict. `validation` and `raw_table_audit.json` retain diagnostic/CLI inconsistencies.

All source/class/input hashes and old raw are protected by `build/frozen_manifest.json`. The analyzer is derived postprocessing written while the long-running campaign is active; its SHA is recorded in every audit output. It is not part of the solver or of the already frozen execution code.

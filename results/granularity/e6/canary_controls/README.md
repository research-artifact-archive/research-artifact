# Canary dependency controls

These two controls expose assumptions behind the original finite Canary witness. They were registered before execution in DAILY on 2026-09-29 at 17:27:53 JST. They are not new operational incident reconstructions or attempts to increase the count of favorable witnesses. Original Canary files remain unchanged.

Every n = 2,3,4 and every m = 1,…,n−1 is included. Each of the six parameter points is evaluated under both controls:

- `healthy_only`: change only H → {HP,BP} to H → {HP} for each component's transfer. All physical edges, reports, recovery, monitors, initializers, and endpoint contracts stay the same. Fine and all-group are expected WIN.
- `no_recovery`: retain both transfer outcomes and remove only each B -- restart_i → H edge. Ordinary/controllable action declarations and the monitor's restart observation remain present, but the physical restoration action is unavailable. A selected BP outcome can report to B and can never reach H again, while the loadable goal requires all H. Fine and all-group are expected LOSS.

HP is physically healthy but not yet reported; BP is physically broken but not yet reported. The interval tester continues to track reported health, so physical health is separately checked over every returned WIN-certificate state. This distinction is the same as in original Canary. The no-recovery control deliberately exposes the restoration assumption; it does not assert that the real CrowdStrike incident had no recovery path. Original restart denotes abstract controllable restoration, not a claim that a simple restart repairs any particular incident.

Primary inspiration is the staged rollout/telemetry discussion in [CrowdStrike's preliminary post-incident review](https://www.crowdstrike.com/en-us/blog/falcon-content-update-preliminary-post-incident-report/) and [technical root-cause analysis, page 6](https://www.crowdstrike.com/wp-content/uploads/2024/08/Channel-File-291-Incident-Root-Cause-Analysis-08.06.2024.pdf). Those sources motivate staged exposure and feedback, not the finite control assumptions tested here.

## Fixed schedule and protection

The schedule contains 12 conditions × 4 variants = 48 trials: fine Lazy, E1 merged-transfers Lazy, generated all-group Lazy, and fine Direct-Full. Order is increasing n, increasing m, healthy-only then no-recovery, followed by the four variants in that order. Every merged Lazy trial also compares the full reachable Post relation to the generated all-group contract.

Each trial is one serial JVM, 32g heap, a whole-JVM 1,200 s cap, and no retry. Family order is PC2, Threads, Rolling scale, then these controls. No new trial starts at or after 2026-09-30 09:39 JST; unstarted cells remain NOT_RUN_DEADLINE. All negative results, unexpected outcomes, timeouts, errors, preflight files, and partial runs are preserved. Expected outcomes never fill missing measurements.

Only the existing E1 JAR is used, SHA-256 `ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5`. The common adapter, construction helper, and harness remain frozen. No solver/JAR/source changes are introduced. The generator verifies original input hashes against Canary's frozen manifest and makes byte-identical reference copies. The independent validator checks those copies against the originals and permits only the stated control edit, identity/metadata fields, and existing fine/all grouping. It independently reconstructs all 48 endpoint products, checks finite reports, and verifies the no-recovery graph's closed {BP,B} region.

`v1/inputs/` holds the 24 new inputs, `reference/` the 12 original copies, `config.json` the fixed schedule, and `build/frozen_manifest.json` the input/JAR/code hashes. Execution uses the unchanged `e6/tools/run_family.py` phases freeze, preflight, run, analyze, and audit. The global JVM lock enforces serial measurements. Aggregation always uses a fresh subprocess.

## Outputs

`tables/results.csv` retains all 48 rows using the common schema: measured decision/status, counts for discovered states/queries/nonempty buckets/outcomes, returned WIN rank or discovered LOSS-certificate size, measured times, input/JAR/certificate SHA values, expected check, and raw artifact paths. Mac times are reference values only. `tables/pairs.csv` retains all 12 conditions, original measured fine/merged decisions and their raw source SHA values, all four new decisions/counts, category, generated equivalence, and DF consistency. Categories separately retain witness, null, both_loss, reversal, and incomplete.

`tables/certificate_checks.json` checks WIN physical health and rank descent, or records up to three returned LOSS states in the irreversible broken region. This local obstruction is not a unique causal explanation. E1 independently validates the full returned certificate. `mechanism_reasons.csv` provides one explanatory sentence per completed cell. `table_canary_controls.tex` is the compact S4 fragment; common `results.tex` retains all cells. Rank is a returned completion bound, not an optimum; the losing region is a discovered certificate, not the whole game's largest losing region.

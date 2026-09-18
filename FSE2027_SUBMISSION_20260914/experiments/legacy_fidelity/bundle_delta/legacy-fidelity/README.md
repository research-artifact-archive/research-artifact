# Legacy fidelity reference experiment

This is a separate reference experiment on the original monolithic benchmark inputs. It does not extend the 27-instance RQ3 denominator or assert identical games across the two tools. The Mac trials are correctness checks only; their times/RSS must not enter the Xeon results or paper performance comparisons.

## Fixed tools and input construction

- **Lab-maintained build of the original DUCS source**: source commit `e1bf040b83e36b36308bce22e280133682986250`; fixed shaded JAR SHA-256 `4ab198ba14c9f0f829c36808025aefc063e2a3a0836679490179cc407e6133e5`, 672,505,060 bytes. This is the build used for the supplied GUI log, not an identified publication release binary. `cli/PublishedMtsaRunner.java` is a separate adapter compiled against that JAR. The underlying source and JAR are unchanged. The shaded JAR is self-contained for these calls; the pilot required no extra classpath dependencies.
- **Fork legacy path**: existing `SingleCompositionRunner`, Traditional DUCS mode; frozen JAR SHA-256 `fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07`. It remains in the previously installed bundle; this delta does not replace it.
- Original model copies come from the public-lineage build's `target/classes/UnpackagedExamples/Update-TSEcaseStudies/2017-TSE-*.lts`. Each agrees byte for byte with the source-commit resource and the corresponding JAR resource. `prepare_package.py` only reads that tree.
- `inputs.csv` records generated paths, source/input digests, changed-line counts, and missing conditions. All 8 supplied model files have exactly 3 fluent declaration lines changing `beginUpdate` to `hotSwapIn` for the fork. Other occurrences, assertions, declarations, and models remain unchanged. Empty-transition conditions only toggle the designated `transition =` assignment comments. Each input has its complete diff.

| Model | Supplied transition | Empty-transition condition | Composite targets |
|---|---|---|---|
| GSM | absent | T_NO_TP | UPDATE_CONTROLLER |
| Industry | T | T_Empty | UPDATE_CONTROLLER |
| MetaSocket | native T_FROM_DES64 / DES128 / DES64COM / DES128COM | missing; no invented condition | all 8 UPD composites |
| PowerPlant | NoTransition | missing; no named T_NO_TP/T_Empty/NO_TP | UPDATE_CONTROLLER |
| ProductionCell | T_SWITCH_TO_NEW_ASAP | T_NO_TP | UPDATE_CONTROLLER |
| Railcab | absent | T_NO_TP | UPDATE_CONTROLLER |
| Surveillance | absent | T_NO_TP | UPDATE_CONTROLLER |
| Workflow | absent | NO_TP | UPDATE_CONTROLLER |

MetaSocket targets: UPD64_128, UPD64_64COM, UPD128_64, UPD128_128COM, UPD64COM_64, UPD64COM_128COM, UPD128COM_128, UPD128COM_64COM. Each retains its supplied transition and the absence of `nonblocking`; the other models retain their supplied `nonblocking` keyword. There are **15 supplied targets + 6 empty-transition targets = 21 conditions per tool**, **42 first trials**, and at most **210 total trials**. The four missing tool/condition rows remain in `inputs.csv` and are not silently counted as losses.

## Private Xeon delta and commands

`fg-ducs-xeon-campaign-legacy-fidelity.zip` is a **private machine-transfer package**. Its shaded JAR is not for the public artifact or release. Public packaging may copy the adapter source, generated inputs/diffs, scripts, configs, and sanitized raw data, but must exclude `lib/`, `*.jar`, `build/`, and this ZIP.

With all preceding campaigns stopped/completed, expand the delta over the already installed campaign directory, e.g. `C:\FGDUCS`. The delta adds `legacy-fidelity/`, two configs, and a comparison collector; its copied `scripts/campaign.py` adds a `published_mtsa` backend, and its copied `run-all.ps1` registers the two campaigns. Existing configuration files, original input files and fork JAR are not replaced. The Mac source bundle and original ZIP remain unchanged.

Requirements are unchanged: Windows Xeon W-2265, at least 240 GiB RAM and 50 GiB disk free, 64-bit JDK 17 and Python 3.10+ on PATH. Every trial is one JVM with `-Xmx64g`, a 1200-second wall cap, serial execution (`parallel_trials=1`), process-tree termination and RSS sampling. The existing Windows probe runs before trials. The new adapter and argument construction have been checked on macOS; the new delta has not yet been executed on Windows.

```powershell
# Run from the existing bundle after overlay extraction.
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-all.ps1 -Campaigns legacy_fidelity_published,legacy_fidelity_fork
# To inspect plans without starting any synthesis JVM:
python .\scripts\campaign.py --config legacy_fidelity_published --stage plan
python .\scripts\campaign.py --config legacy_fidelity_fork --stage plan
# Rebuild only the cross-tool table from collected results:
python .\scripts\collect_legacy_fidelity.py --root .
```

The driver runs stage1, stage2, then collect separately for each tool. Stage1 is repetition 1. Only valid SUCCESS/UNREALIZABLE stage1 cells receive four more planned repetitions. TIMEOUT/OOM and abnormal/invalid outcomes are retained and never retried. If a later repetition fails, remaining repetitions are explicit SKIPPED_AFTER_RESOURCE_FAILURE or SKIPPED_AFTER_INVALID_OR_INCONSISTENT rows. Five complete, consistent runs are required for median/min/max. Successful runs from a censored group do not receive a median. All 42 first-trial cells remain in the tables.

Worst-case cap sums: **each tool 21 × 1200 s = 7 h in stage1**, additional 84 × 1200 s = 28 h; **both tools stage1 14 h, additional at most 56 h, total at most 70 h**, plus startup, compilation, probes, collection, and disk overhead. The small Industry pilot does not justify a runtime guarantee for all other models. This is not guaranteed to finish overnight.

Return complete `raw/legacy_fidelity_published/`, `raw/legacy_fidelity_fork/`, `raw/legacy_fidelity_comparison.csv`, and the new launcher logs to `experiments/legacy_fidelity/raw/xeon/`. Keep the results separate from RQ3. `summary.csv` and `stage1.csv` retain states/transitions and statuses; `legacy_fidelity_comparison.csv` pairs all 21 conditions, flags MATCH/MISMATCH/UNDECIDED, and preserves tool-specific statuses and invalid/inconsistent indicators. A run interrupted before completion must remain explicit, not become LOSS.

Times have different internal scopes: the published adapter records `compile + continueCompilation + applyComposition` because the nested updating controller is synthesized during `continueCompilation`; the fork exposes its native solve-control-problem interval. Do not ratio these two internal columns as equivalent timings. Five-run end-to-end JVM wall times may be shown as reference timings under the common cap, with that scope stated. This comparison supplies no FG certificates or endpoint checker; those are not fabricated or required for either legacy tool.

## Mac pilot and decision V

Fixed Mac settings: 24 GiB physical RAM, JDK 17, 16 GiB JVM heap, 1200 s per trial, one final trial per cell; no timing/RSS use in paper performance. Decision V changed only the three specified fluent declarations in the prior T_Empty copy. Its completed fork trial is reused by raw reference, never executed again. Its input is byte-identical to the final generated fork Industry/T_Empty input. During generator cleanup, only leading indentation on uncommented transition assignments was preserved more exactly; the prior published pilot input differs by that whitespace only, with the same assignments and formulas.

| Input | Original-source lab build | Aligned fork |
|---|---|---|
| Industry / supplied T | SUCCESS; 3,050 states / 9,496 transitions | SUCCESS; 3,050 / 9,496 |
| Industry / T_Empty | SUCCESS; 2,312 / 6,615 | SUCCESS; 2,312 / 6,615 (decision V) |

Raw paths: `raw/mac_pilot_published_adapter_fix`, `raw/mac_pilot_fork`, and `raw/mac_v_industry_empty`. `raw/mac_pilot_published` preserves both **initial adapter CRASH** trials: compilation had already generated the 3,050/2,312-state controllers, but the first adapter incorrectly required the outer named composite to have the inner UpdatingControllerCompositeState Java type. The separate adapter was fixed, without modifying either tool or inputs, and the final two published cells were executed once under that adapter. These development failures remain available and are excluded from any performance data. No fork cell was repeated. `run_pilot.py --adapter-fix` documents that correction and refuses overwriting completed raw runs. `pilot_summary.csv` points to each underlying result.

The final adapter adds a narrowly scoped LTSCompositionException classification after the successful Industry pilot: an explicit completed inner DUCS no-controller log is required to preserve LOSS. Four Java classification assertions verify this path without invoking synthesis; the already validated WIN path is unchanged. The final module has a new digest recorded in its config; the pilot raw retains the preceding module digest. No synthesis was repeated for this exception-only correction.

The public adapter follows the GUI's compile → continueCompilation → applyComposition route. It checks the requested composite exists (avoiding the compiler's fallback to an unrelated composite), writes native logs, and emits a structured result CSV. Null composition alone is not converted to LOSS: a completed explicit DUCS no-controller result is required. The public API wraps this result in LTSCompositionException when flattening a named outer composite; only that explicit combination becomes LOSS. Other exceptions remain CRASH. Its adapter JAR and synthesis JAR digests are checked before Xeon execution. Source and bytecode are separately packaged; no original class is patched.

## Local preparation and checks

From this directory, `python3 prepare_package.py` generates inputs/configs and compiles only the separate adapter using JDK 17, then `python3 assemble_delta.py` creates copies of the runner/driver. These preparation commands use the adjacent private source tree and existing rq3_xeon bundle; they never rebuild MTSA. Existing raw must be preserved. `python3 check_fidelity.py` (7 checks) and `python3 bundle_delta/scripts/check_orchestration.py` (9 checks) are infrastructure fixtures only and start no synthesis JVM. `cli/PublishedMtsaRunnerCheck.java` supplies 4 additional classification assertions; its raw log is `raw/adapter-classification-check.log`. The initial fixture assertion failure about an absolute output path is retained in `raw/fidelity-checks-initial.log`.

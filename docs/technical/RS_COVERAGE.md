# Residual initialization coverage

Module: `FSE2027_SUBMISSION_20260914/experiments/rs_coverage/` in the restored research workspace, or `results/initialization/` in the public layout.
Use `python3 reproduce/check.py --output work/check` at the public repository root for the complete isolated saved-evidence check. Follow the [current reproduction guide](../REPRODUCTION.md) for workspace restoration; the historical module commands below use that restored layout and write module-local CSVs, so run them only in a disposable workspace copy. The [initialization overview](../../results/initialization/README.md) links the additional reference-meaning checks and distinguishes them from the preserved H/A/E classifications.


This standalone module classifies the actual compiled NEW and UPD safety monitors for the nine benchmark models and their base/R1/R2 contracts. It performs no controller synthesis, endpoint-product construction, benchmark replay, or source/model modification. Its H/A/E classifications test plant-independent sufficient conditions. Failure of one condition leaves that condition inconclusive for actual plant histories. Separate later lookup and R1 evidence, described below, supplements these preserved results.

The historical **H (history-inclusive)** classification contains **273 requirement occurrences: 138 NEW and 135 UPD; 273 classified, 0 fluent-determined, 0 exact residuals certified, 273 RS untested, 0 unclassified**. These columns and their original logs are preserved. Repeated NEW requirements remain in the denominator. Every failed H condition has two concrete histories with the same referenced-fluent valuation and different monitor states, one being absorbing ERROR. All recorded H counterexamples use actual labels; none require the `__OTHER__` representative.

The **A (activation-safe)** check establishes RS inclusion for **138/138 NEW occurrences** under the stated interpretation. Equality is conditional on an actual non-error activation entry with a **nonempty actual safe-history set**; if that set is empty, its language intersection is universal and inclusion is automatic. Plant-specific nonemptiness is not checked here. The **syntactic E-prime condition certifies exact entry-scoped initialization for 89/135 UPD occurrences**; the remaining **46 occurrences reference event predicates and are unverified by that condition**. These are not 46 semantic counterexamples. A later source-specific guarded-invariant check supplies exactness evidence for all 46 R1 occurrences under the supplied entry interpretation; it does not alter the earlier classification columns.

The earlier **E** computation remains intact: it left all 135 valuation-parameterized reference-language comparisons unperformed and recorded `rs_E_exact=false`. Its separate diagnostics found observer synchronization for 89/135 and compiled boundary/reset consistency for 135/135; those diagnostics still do not constitute proofs. E-prime supplies a different sufficient proof using the saved declared-fluent definitions and the absence of update events before entry. Its results are appended in `rs_E_ah_*` columns, without replacing the historical H, A or E results.

## Reproduce the classification without Java

Python 3.10 or later and its standard library suffice. From the module directory, in a disposable package copy:

```sh
python3 check_tests.py
python3 check_coverage.py
```

The checker reads the final exports in `raw/expanded-predicates/` and unchanged first-trial outputs below `../rq3_xeon/raw/rq3/runs/`. It writes `summary.csv`, `contract-coverage.csv`, and the following files to `../../paper/build/generated/`:

- `rs-requirements.csv`: per-occurrence classifications, product sizes, initializer type, boundary state, and witness histories.
- `rs-model-summary.csv`, `rs-model-table.tex`, `rs-counts.tex`: model totals, the supplement table and count macros. The retained macros `RSEExactUpd=89` and `RSEUnverifiedUpd=46` use the syntactic check only; the latter does not summarize the later R1 evidence. `RSEAHExactOccurrences=89` and `RSAHEUnverifiedOccurrences=46` expose the corresponding aggregate counts. `RSAInclusionNew=138` distinguishes A inclusion from `RSAExactNew=138`, whose equality claim remains conditional. Historical `RSEExactOccurrences=0` and `RSAEUnverifiedOccurrences=135` retain the earlier computation, as do the old model-summary columns; appended `e_ah_exact_sufficient` and `ae_ah_unverified` provide the current counts. `RSNewOccurrences`, `RSUpdOccurrences`, `RSUpdateOccurrences` and all H macros remain available. `RSEObserverSyncOccurrences` and `RSEResetConsistentOccurrences` remain diagnostics, not exactness proofs.
- `contract-coverage.csv`, `contract-model-table.tex`: contract-element coverage.

Use `--exports DIRECTORY`, `--raw-root DIRECTORY`, and `--output DIRECTORY` to change the input or generated-output locations. `--raw-root` is the directory containing `rq3/`; the default is the preserved campaign raw directory. Missing saved census values remain `UNMEASURED`. In particular, PC Arms=2/R2 has no saved final transfer census, so its multi-target status is `--`; its earlier printed loadable-endpoint count is available. No additional synthesis is needed or performed to fill missing census values.

## H: what is checked

For each requirement, `check_coverage.py` explores the full reachable product of its compiled deterministic safety monitor and the fluents referenced by its formula. The initial fluent valuation comes from the declared initial values. Event predicates use their compiler-expanded action sets and become false after any non-initiating event. Ordinary fluent initiation takes precedence over termination; other events preserve the value. Events absent from a monitor alphabet stutter; a missing transition for an event in that alphabet leads to ERROR. ERROR is absorbing while the fluent observers continue to evolve.

The finite alphabet contains all monitor and fluent labels for the model plus one representative for all remaining ordinary labels. The product checks all free histories, without plant, safe-history, update-once, or activation-domain restrictions. Thus a failed check is an overapproximation witness, not necessarily a realizable plant trace or an RS violation. The 200,000-pair cap and unsupported nondeterminism produce `UNCLASSIFIED`, never a proof. The final classification has no such cases (4,686 product pairs in total; at most 128 per occurrence).

Equal fluent valuations must determine the same monitor state, **including ERROR**. A single non-error state does not ensure this. For GSM NEW `P_NEW_DECODE`, the empty history reaches monitor state 0 with `decode.2=false`; `decode.2, decode.3` reaches ERROR with the same valuation. A language rejected in the past remains rejected even after its event fluent returns to false.

The actual initializer is checked separately:

- **NEW:** the frontend uses its non-error fluent-valuation lookup. An exact certificate requires the free-product condition and agreement between the actual lookup observers and the independently extracted referenced observers. All 138 NEW observer definitions agree, but all 138 free-product checks fail. Since the condition fails, `initializer_matches=false` denotes failure of this sufficient certification, not a separately established mismatch for an actual plant history.
- **UPD:** the frontend supplies a constant monitor state obtained by consuming `hotSwapIn` once from monitor state 0, for every old root. It does not use the NEW lookup. The separate sufficient initializer check compares that constant with the state after every free prehistory followed by `hotSwapIn`. This is deliberately stronger than checking actual entry histories. A failure leaves that history-relative condition untested.

An exact result requires both fluent determination and compatibility with the initializer actually used. The monitor residual wrapper alone does not certify correspondence with the complete activation history.

## A: safe histories and the frontend selection rule

The A exploration keeps only non-ERROR prefix states and records the immediate ERROR frontier without expanding it. Every update label (`hotSwapIn`, `hotSwapOut`, and the stop/start/reconfigure labels) may occur at most once in a prefix. Labels that have the same complete monitor/observer transition effect are grouped with a bounded counter; the counter's bound is the number of distinct labels, and witness paths use each distinct label at most once. Updates stuttering on all monitor states and all observer values can be projected away. Ordinary actions remain unrestricted. This quotient preserves the reachable monitor/valuation pairs and avoids an irrelevant exponential mask over indistinguishable update labels.

For every fluent valuation, the checker compares all safe monitor states by a separate DFA-pair search. It checks equality of their complete finite safety-continuation languages, including ERROR rejection; state numbers need not agree. Continuations are compared over all words, which is stronger than comparing only one-shot update continuations. A distinguishing continuation is retained when equivalence fails.

The frontend lookup construction itself uses unrestricted update histories, gives ERROR entries priority, and selects the smaller ID among language-equivalent non-error states. The checker reconstructs that rule from the saved monitors and observer definitions on its overapproximating alphabet, and checks **all possible non-error selections**, including valuations that the reconstructed larger alphabet would mark ERROR. This covers the actual alphabet's possible non-error choices as well. At this initial classification stage, the materialized frontend lookup table had not been exported: this was a source-rule reconstruction and language check, rather than a direct table comparison. The preserved `a_lookup_evidence` columns record that historical scope and its reconstructed non-error/error entry counts. The later independent table comparison described below supplies the missing direct evidence without rewriting those columns.

The observer definitions exported for the actual frontend must also agree with the independently extracted definitions. A successful A result applies to an actual lookup entry that enables activation and has at least one actual safe history. It does not prove that such a history exists at every reachable physical state, or that every free valuation is a physical activation state. If the actual safe-history set is empty, its language intersection is universal: inclusion holds automatically, but equality with an ordinary monitor language does not follow. `a_actual_safe_history_nonempty` therefore remains `NOT_CHECKED_WITHOUT_PLANT` throughout the benchmark table.

## Historical E: entry-valuation diagnostics and missing reference semantics

The E exploration computes every referenced-fluent valuation reachable from declared initial values by a free pre-entry history. `hotSwapIn` is excluded from the prehistory; every other update label may occur at most once. Such prehistories intentionally include stop/start/reconfigure actions even though those actions cannot precede entry in the actual game. The checker then consumes `hotSwapIn` exactly once in the observer vector and compares the resulting vector with the canonical vector obtained from declared initial values. It separately verifies the saved boundary state against the compiled monitor's one-step transition and compares their continuation languages.

The result is observer synchronization for 89/135 UPD occurrences and compiled reset consistency for 135/135. The remaining 46 observer cases have explicit differences. For example, GSM R1's free prehistory `stopOldSpec_P_DECODE` makes `AfterStopBeforeStart_P_NEW_DECODE` true, and `hotSwapIn` leaves it true; the canonical post-entry value is false. This is an **observer-difference witness**, not a language-inequivalence counterexample, and that prehistory is outside the actual pre-entry game.

The monitor DFA stored in the exports accepts `(state, action)`, not `(state, valuation, action)`. Reusing its initial state for each valuation would make the requested language comparison tautological. The original formula, a valuation-parameterized semantic initializer, and monitor reconstructions for altered initial valuations are absent from these exports. Consequently **the historical E analysis left all 135 reference-language comparisons unperformed and exactness unverified by that analysis**, including the 89 synchronized observer cases. Its CSV fields retain `e_reference_language_available=false` and `e_exact_sufficient=false`; neither diagnostic is promoted to a proof. The syntactic extension below establishes a separate syntactic sufficient condition for a subset, without changing those fields or pretending to perform the missing comparisons.

The requested CSV columns `rs_A_exact` and `rs_E_exact` alias `a_exact_sufficient` and `e_exact_sufficient`; their companion `rs_A_note`, `rs_E_note`, `rs_A_witness`, and `rs_E_witness` preserve the conditional scope and the distinction between observer differences and missing reference-language evidence. `NOT_APPLICABLE` separates NEW-only A and UPD-only E fields.

The A/E extension invoked no Java and left the monitor exports, benchmark inputs, JARs, previous H logs, and H result fields unchanged. The earlier execution logs are `raw/ag-ae-classification-20260919-v2.log` and `raw/ag-ae-checks-20260919-v2.log`; the first successful logs without the `-v2` suffix are retained from before adding the requested column aliases.

## Syntactic E-prime: declared update-stage fluents

`check_entry_stage_syntax` reads the existing `referenced_fluents` definitions. A UPD occurrence passes only if every referenced observer has `kind=declared_fluent`, a declared Boolean initial value, and expanded initiating/terminating lists containing only the recognized update labels: `hotSwapIn`, `stopOldSpec`, `startNewSpec`, `reconfigure`, or the latter three followed by an underscore and a nonempty component/requirement suffix. Broad prefixes such as `stop*` are not used: plant actions such as `stopPump` and `startPump` fail the check. Wildcards, implicit action predicates, unknown kinds and missing definitions do not certify. `hotSwapOut` is excluded from this syntactic label class; the older A/E one-shot predicate is unchanged.

No update label can occur before entry in the supplied game, so these declared fluents have their declared initial values at every entry. Lemma E-prime therefore does not need to reconstruct a different monitor for an altered entry valuation. The checker additionally requires monitor initial state 0, the constant-after-`hotSwapIn` initializer mode, a deterministic saved DFA, and agreement between its one-step boundary and the saved boundary, which must be a valid non-ERROR state. Under the stated entry-scoped meaning, that constant initializer is exact. Neither observer synchronization alone nor a fluent's name is used to certify it.

The E-prime result is 89 exact and 46 UPD occurrences unverified by this condition. All 46 excluded occurrences reference `event_predicate` observers: 43 action-set occurrences plus three Industry/R1 occurrences with individual action predicates. They also reference declared update-stage fluents; the event predicates are the reason they fall outside E-prime. No declared plant fluent causes an additional exclusion in this cohort. All 135 boundary checks pass, but that fact alone remains insufficient. The counts come from the saved definitions, not the expected 89/46 split.

The appended columns are `rs_E_ah_exact`, `rs_E_ah_basis`, `rs_E_ah_update_only`, `rs_E_ah_referenced_labels`, `rs_E_ah_excluded_observers`, `rs_E_ah_boundary_matches`, `rs_E_ah_boundary_check`, and `rs_E_ah_note`. They expose the inspected labels, excluded observers and reasons, initializer evidence, and the `LEMMA_E_PRIME` proof basis. NEW rows are `NOT_APPLICABLE`. Historical `rs_E_exact`, `e_exact_sufficient` and all other existing fields retain their original meanings and values.

The CSV writer checks every previously saved field in its original row, including H, A and earlier E, before writing. It retains the complete old header in its original order and appends syntactic columns only; it refuses changed values, missing rows or reordered rows. The same check protects generated per-requirement and per-model CSVs. No raw file, model, configuration, JAR or saved export is changed. The printed `ALL_EXISTING_COLUMNS_AND_ROW_ORDER_UNCHANGED` line confirms the check when regenerating the classification. The retained S4 classification table uses the syntactic condition for its displayed E count; the historical columns remain available in the CSVs. S3/S4 separately explain and record the additional R1 guarded-invariant result.

## Later direct frontend lookup evidence

Package-root `evidence/frontend_lookup_demo/` contains a separate materialization of the normal frontend's `SafetyStateMapping` for all 27 model/variant inputs. The frozen JAR and model bytes match the saved campaign. These are fresh frontend objects, not recovered objects from the measurement JVMs. That recorded export compiled the endpoint controllers but did not run the FG update-game solver; its elapsed times are excluded from performance comparisons. Rechecking the saved exports requires only Python.

The independent `verify_saved.py` matches **138/138 NEW tables and all 1,587 entries: 900 non-error and 687 ERROR**. It checks all 408 observer columns and 31,176 observer transitions. Every table's actual alphabet differs from the earlier reference alphabet, and 114 require column permutation; the comparison explicitly reconciles those differences before matching every key and value. It reconstructs repeatable-update table traversal, the first ERROR frontier, ERROR priority and the minimum-ID rule for language-equivalent safe states. Counts include repeated requirement occurrences across variants.

These data contain no initially-true observer columns, safe/ERROR key collisions, or multiple safe states requiring nontrivial language-equivalence checks. The recorded negative checks detect five mutations of real export copies and exercise initially-true normalization and ERROR priority in two separate Python cases; they do not establish coverage of those unused Java branches. Direct table agreement does not establish physical-state decoding, construction of the entire activation domain, completeness of application histories or nonemptiness of actual safe histories. A non-error lookup value alone is not an RS proof.

## Later guarded-invariant R1 evidence

Package-root `evidence/verify_r1_entry_invariant.py` and `evidence/r1-entry-invariant-verification.csv` record a separate sufficient condition for the 46 R1 occurrences excluded by E-prime. The script reads the source formulas and saved monitor/observer exports. Each formula has the pure invariant form `always (G implies not A)`: `G` is a default-false declared guard changed only by the declared update commands, which cannot precede actual entry, and ordinary-action predicates `A` reset at entry. The checker verifies the source/export action sets, reset behavior, constant non-error boundary, and every saved non-error DFA transition against the invariant.

All **46/46** rows have `static_entry_invariant_condition=PASS`; seven negative mutations are recorded separately. This supports exact initialization for the supplied E entry interpretation, complementing the 89 update-stage occurrences. It is not a proof of H, application-history completeness or runtime conformance. The original `rs_E_exact=false`, E-prime's 46 exclusions, and their witnesses remain unchanged; they describe the earlier conditions rather than the outcome of this additional proof. Reset consistency or a non-error boundary alone remains insufficient.

From the package root, after restoring result assets, reproduce the saved comparisons in a fresh output directory:

```sh
python -B evidence/reproduce_supplement.py --output replication/supplement-check
```

This runs eight saved-evidence groups, including the direct lookup and guarded-invariant checks, without a JVM. It compares regenerated outputs with the preserved CSV/JSON. The optional newly generated `rs-editorial-numbers.tex` derives 46/46 from the guarded CSV; it is separate from the historical classification macros and is not a previously saved manuscript macro.

## Read-only monitor export

The authoritative final JSON files are in `raw/expanded-predicates/`. They were produced by `cli/RsCoverageExport.java`, compiled as a separate class against the unchanged experimental JAR. The exporter parses each input, compiles its safety monitors, exports transitions, and reads fluent definitions. It never calls `continueCompilation`, updating-controller composition, the endpoint solver, or the game solver.

To reproduce those exports where the exact frozen experimental JAR is available, use JDK 17 with `java` and `javac` on `PATH` and select a **new** output directory:

```sh
python3 export_monitors.py --repository /path/to/repository --output raw/new-monitor-export
python3 check_coverage.py --exports raw/new-monitor-export
```

`--repository` contains `Implementation/`; `--jar` optionally supplies its exact experimental JAR separately. The driver verifies the JAR and all nine model digests against the saved campaign `environment.json`, imposes a 60-second cap and 2 GiB heap per monitor-only export, and refuses an existing export directory containing JSON or logs. A rebuilt JAR with different bytes is rejected for this exact frontend export. The frozen JAR is not included in the public artifact. Compiled helper classes under `build/` are also excluded; the Java source and saved exports are sufficient for inspecting the computation.

The fixed experimental JAR digest is `fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07`. Export logs retain command arguments, input/JAR digests, stdout/stderr, exit codes, and elapsed time. Personal path prefixes in logs are replaced by `<MODULE>`, `<REPOSITORY>`, or `<USER_HOME>`; these are location placeholders. Elapsed values describe monitor compilation only and are not synthesis-performance measurements.

Initial extraction diagnostics directly under `raw/` are retained but are not classification inputs. The initial exporter applied the NEW fluent helper to UPD formulas too; its pretty-printed set/range parsing did not always reconstruct expanded event sets. UPD does not use that helper for its production initializer. The final exporter reads the compiler's expanded action-predicate vectors for the independent reference observers and separately records the actual NEW frontend observers. This distinction fixes the diagnostic extraction without changing a benchmark model or initializer.

## Frontend correspondence

Source paths below are relative to `Implementation/Source Code/maven-root/mtsa/src/main/java/`. Line numbers refer to the inspected frozen experiment source.

| Concern | Source and behavior |
|---|---|
| Parse without synthesis | `ltsa/lts/LTSCompiler.java:172–191`; `compile()` parses only. |
| Actual NEW and UPD monitors | `ltsa/lts/CompositionExpression.java:388–410` compiles NEW safety constraints and removes the property marker; `ltsa/updatingControllers/synthesis/UpdatingControllersUtils.java:302–326` compiles UPD constraints directly. |
| Referenced fluent definitions | `ltsa/lts/ltl/FormulaFactory.java:29,79–98` contains expanded action predicates; `ltsa/lts/UpdatingControllersDefinition.java:613–705` constructs the frontend's NEW observers. |
| NEW lookup generation | `ltsa/lts/UpdatingControllersDefinition.java:1781–1855` explores monitor/observer pairs; ERROR entries take precedence but are not expanded. Two non-error states at one valuation require equivalent error languages; equivalent states use the smaller state ID (`1864–1893` checks those languages). Post-error fluent restoration is therefore outside this table-generation traversal. |
| Global physical observers | `ltsa/updatingControllers/otf/MtsaRevisedOtfDucsAdapter.java:1411–1480,1539–1590,2598–2630` attaches the shared observer vector to component 0, advances it on ordinary actions, and preserves it through component transfers. |
| NEW candidate physical states | The same adapter at `1985–2016` closes all old endpoint roots under ordinary steps and available component transfers, without full game-monitor restrictions. At `2073–2099,2153–2176`, each physical candidate with a non-error lookup gets a NEW activation entry; it is not restricted to all components already being new. |
| UPD boundary initializer | The same adapter at `1620–1637,2179–2198` computes one step from monitor state 0 on `hotSwapIn` and assigns the resulting constant to every old root. |
| Consuming an activation event | `ltsa/updatingControllers/otf/FineGrainedSuccessorOracle.java:499–516` steps already active testers on the start event, then inserts the NEW tester at its lookup state. The newly inserted tester does not consume its own start event. |
| Residual wrapper | The adapter at `2210–2231` builds a wrapper from the same monitor. `ltsa/updatingControllers/otf/ActivationSpec.java:80–99` checks equivalence between the supplied monitor/residual states; this does not independently inspect activation histories. |

`check_tests.py` retains the ten original semantic controls, including replay of all 273 H witnesses. Ten earlier controls cover A language equivalence versus state identity, distinguishing continuations, the empty-safe-history limitation, ERROR-priority lookup entries, one-shot label grouping, observer disagreement, E's distinction between reset consistency and semantic evidence, and the complete saved A/E cohort. Nine syntactic controls cover true/false initial valuations, event predicates and plant-action prefixes, absent definitions, incorrect/ERROR boundaries and initialization modes, NEW applicability, append-only preservation and the saved syntactic certificates. All 29 pass. `raw/checks.log` is the original result; the unchanged A/E log named above records the historical twenty controls. The commands above reproduce the current 29-test suite without Java or synthesis.

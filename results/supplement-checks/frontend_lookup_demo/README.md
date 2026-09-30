# Direct comparison of frontend NEW lookup tables

This check freshly materializes the normal frontend's `SafetyStateMapping` for
all 27 application inputs (nine models × Base/R1/R2), using the unchanged JAR
and byte-identical input files used by the saved application campaign. It is
not a recovery of objects from the earlier campaign's JVMs. It is a functional
output check, not a new synthesis-performance measurement.

All 27 separate JVM attempts completed on their first attempt. There are no
failed, timed-out, retried, or unrun targets. Each attempt had a 120-second limit
and a 2 GiB Java heap limit; all Java executions finished before the prescribed
aggregate cutoff. Elapsed fields in `meta.json` are execution context only.

| Scope | Result |
|---|---:|
| Fresh frontend exports | 27/27 |
| NEW requirement tables exactly matched | 138/138 |
| All actual table keys checked | 1,587 |
| Non-error / ERROR entries | 900 / 687 |
| Observer columns / state-event transitions checked | 408 / 31,176 |
| Data mismatches | 0 |

These totals count every requirement instance in every variant, including
repeated endpoint requirements; they do not claim 138 distinct formulas.

## What was executed and saved

`FrontendLookupExport.java` is an external class compiled against the frozen
JAR. It invokes `LTSCompiler.compile()` and
`continueCompilation("UpdCont_OTF_FG" + variantSuffix)`, then reads
`UpdatingControllerCompositeState.getSafetyStateMapping()`,
`getSafetyComponentsMap()`, and `getNewSafetyLTSs()` directly. Normal frontend
compilation synthesizes the old and new endpoint controllers. The exporter
does **not** apply composition to the returned updating-controller state, call
the FG game solver or its adapter preparation, enumerate `physicalClosure`, or
construct `ActivationSpec`. It rejects a recorded FG solver outcome.

`run_once.py` contains the exact bounded run procedure and refuses to overwrite
an existing `runs/` directory. `compile.log` records its external compilation.
`runs/<family>__<variant>/` contains the full `lookup.json`, stdout, stderr, and
`meta.json` for that one attempt. Metadata records the command, Java version,
input/JAR/exporter digests, exit status, and output-file digests. No saved
campaign file, original model, Java source, JAR, or earlier checker was modified.

The frozen JAR is:

```text
FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/bundle/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar
SHA-256: fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07
```

The model/variant list comes from
`FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/configs/rq3.json`.
`run_once.py` checks model bytes against that campaign's
`raw/rq3/environment.json` before and after the run.

## How the independent comparison works

`verify_saved.py` uses only the Python standard library. It reads the earlier
monitor and observer exports in
`FSE2027_SUBMISSION_20260914/experiments/rs_coverage/raw/expanded-predicates/`
and the earlier `rs_coverage/summary.csv`; it does not import or execute the
original checker or the Java table-construction code.

1. Compare the actual monitor state conventions, alphabets, and complete
   transition sets with the saved monitor. Match each actual observer column
   to its saved frontend fluent by name and verify its initial value and
   initiating/terminating events. Match frontend and reference observers by
   semantic signatures, since event-predicate names may differ.
2. Retain the **actual runtime column order**. Normalize observer state 0 to
   its declared initial Boolean value and state 1 to the opposite value. Thus
   state 0 is not assumed to mean false. Independently check every exported
   two-state observer transition against these Boolean event rules, including
   wildcard termination and initiating-event precedence.
3. Reconstruct the full table by exploring monitor/Boolean-observer products
   over the actual frontend alphabet. Update labels may repeat during this
   table construction; this is not a one-shot physical execution analysis.
   Events outside the monitor alphabet stutter; a missing in-alphabet edge
   reaches ERROR. Explore safe prefixes and their first ERROR frontier, never
   successors of ERROR. ERROR has priority when both safe and ERROR prefixes
   produce the same key; language-equivalent safe states use their minimum
   state ID. Compare every key and value, including ERROR entries and absence
   of additional keys.
4. Independently reconstruct over the earlier checker's model-wide alphabet
   and referenced-fluent order. Compare all non-error values and ERROR counts
   with its saved CSV, then permute to the actual column order and compare the
   complete table again. All comparisons match.

Alphabet and order differences are retained in `verification_details.json`.
The actual frontend alphabet has 10–62 labels; the reference alphabet has
10–54 labels and includes `__OTHER__`. All 138 comparisons have an alphabet
difference, and 114 tables require a column permutation relative to the saved
reference order. Equality was checked after these explicit reconciliations,
not inferred from alphabet or array equality.

There are no initially-true observer columns, no safe/ERROR key collisions,
and no multiple safe states requiring nontrivial language-equivalence checks
in these 27 Java exports. Consequently these data do not exercise those Java
implementation branches. The Python checker includes two separate synthetic
units for initially-true index normalization and ERROR precedence.

`negative_checks.json` reports seven detected counterfactual errors: five
changes to copies of saved real exports (safe entry → ERROR, ERROR → safe,
deleted key with an adjusted entry count, omitted observer transition, and
swapped columns without permuting keys), plus the two synthetic Python units.
The actual saved exports remain untouched.

## Inspect and reproduce

From the repository root, recheck every saved result without running Java:

```sh
python3 FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/frontend_lookup_demo/verify_saved.py
```

This writes `lookup_check_summary.csv`, `verification_details.json`, and
`negative_checks.json` in this directory. The first gives all 138 outcomes; the
second includes actual and reconstructed normalized tables and alphabet/order
differences. `run_summary.csv` gives all 27 JVM outcomes.

For a fresh, separate export, use Java 17 and an unused output filename; the
exporter itself refuses to overwrite output. For example:

```sh
LOOKUP_DEMO=FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/frontend_lookup_demo
LOOKUP_JAR='FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/bundle/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar'
mkdir -p "$LOOKUP_DEMO/reproduction/classes"
javac -cp "$LOOKUP_JAR" -d "$LOOKUP_DEMO/reproduction/classes" "$LOOKUP_DEMO/FrontendLookupExport.java"
java -Xmx2g -Djava.awt.headless=true -Dmtsa.evaluation.enabled=false \
  -cp "$LOOKUP_DEMO/reproduction/classes:$LOOKUP_JAR" \
  ltsa.lts.FrontendLookupExport Implementation/Experiment/Models/GSM_FG.lts \
  UpdCont_OTF_FG "$LOOKUP_DEMO/reproduction/gsm_base.json"
```

The per-attempt `meta.json` records the corresponding invocation for each of
the other 26 cases. The dated `run_once.py` preserves the original cutoff and
is intentionally not an overwrite/retry command. The example above has not
been executed as an additional attempt. Public packaging must retain the
referenced inputs, frozen JAR, earlier exports/CSV, and their relative paths,
or explicitly adapt these paths; this directory alone is not a standalone
artifact package.

## Interpretation and limits

The new evidence closes the gap between a source-rule reconstruction and the
**actual frontend NEW lookup table objects** for these inputs and this JAR.
It does not export or check physical-state-to-observer decoding, the expanded
`ActivationSpec` domain or selected physical activation entries, actual plant
histories, nonemptiness of the safe-history reference for those entries, or
any UPD initializer. It therefore does not independently establish the full
physical initializer or unconditional RS. The earlier conditional RS results
and all historical checker fields remain unchanged.

Source entry points for the saved revision:

- `ltsa/lts/LTSCompiler.java:259`: frontend `continueCompilation`.
- `ltsa/lts/UpdatingControllersDefinition.java:576–611, 691–704`: actual
  observer alphabet, columns, and table construction.
- The same file, `1728–1774`, `1781–1853`, and `1901–1935`: Boolean encoding,
  table construction, and monitor stepping.
- `ltsa/updatingControllers/structures/UpdatingControllerCompositeState.java:553–559`:
  the two actual mapping getters.
- `ltsa/updatingControllers/otf/MtsaRevisedOtfDucsAdapter.java:1325–1346, 1985, 2073`:
  downstream physical closure and NEW activation construction, which this
  exporter does not invoke.

These paths are relative to
`Implementation/Source Code/maven-root/mtsa/src/main/java/`.

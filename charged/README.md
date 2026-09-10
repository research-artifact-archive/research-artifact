# Charged atomic-call retry policies

This supplement contains the charged-call research revision, including exact resource bounds attained without a writer-budget input, the sharp independent-job price ratio, the mixed-price reduction, checked cursor policies, Java integration, source-instrumented Deephaven case, and all retained experimental outcomes. The earlier zero-fee package remains in `../package` and its history. These are authored research inputs and implementations; declared charges do not estimate elapsed time.

The current portable implementation is `charged_compact_03`. Inputs satisfying the proved price and dependency conditions use a linear-size cursor artifact. Other inputs use the general all-reachable-set compiler. The general fallback can require exponentially many unfinished sets; specifying a large binary budget alone does not enlarge the compact artifact.

## Compile and query

Run from the repository root with Python 3.10 or later; the compact implementation and standard replay need only the standard library. Keep assertions enabled. All output paths below must be new.

```sh
python3 charged/compact.py compile --input charged/examples/mixed.json --out work/mixed-policy.json
python3 charged/compact.py check --artifact work/mixed-policy.json --input charged/examples/mixed.json
python3 charged/compact.py query --artifact work/mixed-policy.json --input charged/examples/mixed.json --budgets 0 1 2 4294967296
```

`compile --general` forces the general route. `check` and `query` accept an optional expected input; an explicitly supplied null, float, or boolean in an integer field is rejected. JSON duplicate keys are rejected. The old `charged/retry.py` remains available for the earlier general-basis artifact format.

Each job is `[w,p,g,v,r]`, with positive integer work `w` and nonnegative integer fees/premium. `edges` contains distinct directed index pairs, with no cycle. The original callback fee is `k=g+r`; the unavoidable baseline is the sum of `c=w+min(v,k)`. Let `delta=k-min(v,k)` and `P=p+delta`. The compact route requires `p*delta=0` for every job, and nondecreasing effective `t` along every edge, where `t=min(c,w+p)` if `delta=0`, otherwise `t=c`. The original prices and baseline remain in the artifact.

The example mixes a positive-delta zero-premium job and a cached-completion job. It has baseline 6 and three-mode cap 8 at budget 1; the two-mode optimum is 9. These are exact declared-charge values, not measured Java latency. The theorem, sufficient conditions and counterexamples are described in [the guide](THEORY_AND_IMPLEMENTATION.md).

`runtime.Policy` exposes `entry`, `choose(budget,state)`, `excess`, `total`, and `advance(budget,state,mode,outcome)`. Constructing a policy checks and copies its artifact. Always execute the returned original call and report its actual match/mismatch outcome. Cheap failure keeps the cursor; cached failure advances it; both consume one token. `advance` rejects an unselected mode or a failure of protected execution. This is a policy/data API, not automatic rewriting of arbitrary Java programs.

## Reproduce preserved evidence

```sh
python3 charged/reproduce.py verify
python3 charged/reproduce.py all --out work/charged-all --timeout 300
```

The driver verifies the public provenance, then runs each stage in a separate process with a fresh output directory. `--quick` is a smoke subset and must not be reported as full reproduction. The full driver retains original measurements and rechecks them; its elapsed times are replay times, not additional benchmark samples. The evidence tree is about 1.8 GB unpacked. Two oversized repeated-input ledgers use lossless gzip; original/decoded/container hashes are recorded, and the reader verifies them.

| Stage | Full evidence checked |
|---|---|
| `curves` | 3,183 general charged inputs, direct/basis agreement, serialized artifact hashes and 11 controls |
| `native` | 3,094 ordinary and four native-control records; 12 record and 11 sequence controls |
| `deephaven` | 216 prefix, 12 public-graph, 108 phase-aware and 36 changing-Action records, plus strengthened checker controls |
| `scale` | 224 original and 144 strengthened general-method units, saved certificates, 76 conformance inputs and 11 controls |
| `calibration` | All 72 JMH cells/720 measurements and the retained failed fee fit |
| `ordering` | 874 charged-order inputs, 17,424 common-price probes, and the later two-instance counterexample |
| `refutations` | Retained primitive/exposed-guard counterexamples and their complete fixed input groups |
| `compact` | The same 19,485 compact/fallback inputs under the byte-identical 03 semantic core, 527,409 branches, 29 controls and 14 CLI controls |
| `compact-native` | 606 ordinary and four native-control records, 208 replay maxima, eight record/five sequence/nine saved parser controls |
| `compact-scale` | All 420 and 180 compact-comparison units, all 366 successful artifacts/value outputs, full failure partitions and the second study's closed form and 36 exact root shapes |
| `price-bounds` | All 13,302 first-study units and 1,866 second-study units; direct values, saved large/general artifacts and huge-budget tails |
| `resource-frontier` | 5,421 DAG/weight inputs and all 265,629 budget/slack roots |
| `resource-vector` | 2,442 raw records, all 96 strictly guarded tables, 576 replay groups, the preserved old-checker counterexample and aggregation controls |
| `resource-frontier-native` | 9,314 raw records, 128 finite tables, 1,024 replay groups and all native-study controls |
| `budget-blind` | 128 cases, 17,714 original native records, 1,280 group maxima, three-state oracle tables and 8/5/4 controls; selector has no B input |
| `universal-work` | Post-outcome W,L,Q formulas from all 17,200existing path records/1,280 groups, including160r=0 groups; zero new measurements |
| `universal-order` | All 86,662legal orders/2,773,184budget-slack checks on5,519fixed inputs; input-bound greedy constructor, scan checker and 7artifact controls |
| `adaptive-work` | 5,519 observed inputs/176,608 adaptive threshold-family roots |
| `probe-blocking` | All 4,320 measurements/1,440 warmups,12 integer references,24 medians and 12 controls; bootstrap intervals preserved but not recomputed |
| `roslyn-source` | All 6,453saved native records and 8 reentry outcomes, including one original TIMEOUT; both full timing summaries |
| `protected-tail` | All 176,640 equation roots,2,552 native paths/144maxima and 8 controls;285 strict W improvements,176,355ties |

The 14 CLI controls deliberately retain two erroneous null acceptances by the old 02 CLI. They do not make those acceptances valid in 03. The 19,485-input study is not counted again as an independent 03 experiment: constructor, checker and runtime are unchanged between 02 and 03, with a separate CLI correction.

Optional Java replay requires JDK 17:

```sh
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py native-java --out work/native-java --timeout 300
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py compact-native-java --out work/compact-native-java --timeout 300
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py resource-vector-java --out work/resource-vector-java --timeout 300
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py resource-frontier-java --out work/resource-frontier-java
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py budget-blind-java --out work/budget-blind-java --timeout 300
```

The compact Java fixture supports at most five jobs and prices at most 1,000,000. It keeps the original callback/kernel/writer bodies while changing the loader and selector. New executions generate fresh raw records and fresh causal certificates; fixed corruption controls remain tied to their original source records. Java launcher-option environment variables are removed for the compact replay so launcher notices cannot masquerade as parser failures. Python handles the large numeric/instance cases.

For native Deephaven rebuilding, see [the source replay guide](DEEPHAVEN_REPRODUCTION.md). It requires separately obtained JDK 21 and pinned upstream/build dependencies. The standard `deephaven` stage needs neither Gradle nor a downloaded runtime.

## Outcome and trust boundaries

Every success, timeout, memory failure, invalid result, unstarted unit and superseded source version remains in the evidence. The second compact scale campaign recorded all 180 units before its final summary expression failed through variable shadowing. `SUMMARY_RECOVERED_01.json` and its separate aggregation script recover the denominator from those records without rerunning a measurement. See [the claim map](CLAIM_EVIDENCE_MAP.md) for locators.

The certificate checkers establish equations of the declared games. They do not verify executable code, infer application prices/budgets, or establish all Java schedules. Native causal checks establish an existential ordering under a shared fixed source translation. The JMH experiment did not establish a positive protection premium or measured third-mode benefit. Deephaven supplies an upper-bound application under stated source and refresh contracts, with no observed prefix abort and no whole-system minimax claim. No human-subject or simulated-human evaluation is included.

Original research code/inputs/docs follow the repository MIT license, except clearly identified upstream material. Modified Deephaven files remain under the full [Deephaven Community License 1.0](licenses/deephaven/LICENSE.md), with its [notice](licenses/deephaven/NOTICE.md); JMH-generated benchmark files retain BSD notices. See [distribution details](DISTRIBUTION.md). Author-local path projections are recorded separately from original hashes and do not alter scientific outcomes.

The [resource-boundary guide](RESOURCE_BOUNDARIES.md) gives the exact protected-work/call-cap formulas, the independent-job sharp ratio, native counting conventions, complete new denominators, the old vector-checker defect and its strict recheck, and the relation to established optimistic fallback.

The [bounded-source guide](BOUNDED_SOURCE.md) gives the adaptive-family extension, protected-tail certificate and its non-global-optimality boundary, all blocking/Roslyn outcomes, exact coverage limitations and optional pinned Roslyn rebuilding. The standard driver now has 21 stages; `protected-tail-java` additionally executes the fixed Java tail paths.

## Certified suffix choices

The [suffix certificate](SUFFIX_CERTIFICATE.md) gives exact feasibility after the failed-call allowance is exhausted, with all 209,408 policy roots, 665,500 finite states and 20,594 native paths. Greedy fresh choice is sometimes worse than all-tail; all adverse examples remain. The new `protected-suffix` stage brings the standard replay to 22 stages. Optional `protected-suffix-java` re-executes its complete fixed native paths.

## Source semantics and partial-repair boundary

The [new guide](SOURCE_SEMANTICS_AND_PARTIAL_REPAIR.md) documents strengthened source obligations, the four retained error-hook TIMEOUTs and their separate repair, all independent-arrival/rebase outcomes, and exact partial-repair limits. That extension introduced stages23--26. New stages are `roslyn-semantics` (592 records), `roslyn-reentry` (55 processes), `roslyn-arrivals` (5,664 units), and `partial-repair` (3,495/160,080 and 1,046/20,920 distinct input/row studies). The optional `roslyn_extended_native.py` rebuilds pinned source and executes 236 semantic and 23 reentry controls.

A separate `roslyn-compilation` stage introduced stage27: all 96 authored compiler-dependency/cache cases, 2,556 project projections and eight raw corruptions. The extended native helper accepts `--compiler-projections` to build and execute these cases after its existing source/semantic/reentry stages. Actual and direct oracle paths share the Roslyn compiler engine.

The [compact partial-repair supplement](PARTIAL_COMPACT.md) adds standard stage28 (`partial-compact`). It preserves both compiler versions, exact regression/certificate checks, the original216 outcomes with6 timeouts and the changed algorithm's168 successes. Read its separate objective and cost assumptions before using the returned competitive policy.

The [objective and batch extension](OBJECTIVES_AND_BATCH.md) adds stages29–30: exact additive/toll recomputation and all saved batch-rebase native/arrival outcomes. Timing improvements are not established.

[Document-state guard supplement](DOCUMENT_GUARD.md) adds stage31: all fixed native projections and the four changed resource rows. No new timing samples.

[Workflow and arrival-count supplement](WORKFLOW_REPAIR.md) adds stages32--33: fixed DAG equations, checkable policy thresholds, and reconstruction of foreground-period publications from existing native timelines.

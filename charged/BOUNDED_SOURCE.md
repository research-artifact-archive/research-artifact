# Bounded calls, protected-tail refinement, and native source studies

The budget-unaware frontier needs no writer budget or calibrated protection premium. Cached completion is an inherited mechanism; the exact call/protection frontier, its normal-form justification and the refinements below are the stated contributions. These are authored fixed-resource results. They do not establish broad application prevalence, editor throughput, WCET or general elapsed-time improvement.

## Policy refinements and their limits

[Adaptive-family proof](evidence/RESUMED_20260909_1413/universal_adaptive_work_01/THEORY_AUTHOR.md): minimum-work ready selection minimizes worst work within the global-r cheap-then-cached threshold family, even compared with a selector that knows B and changes its next job adaptively. All 176,608 roots from 5,519 already observed inputs agree. This does not make the family globally optimal.

[Protected-tail proof and counterexample](evidence/RESUMED_20260909_1413/protected_tail_01/THEORY_AUTHOR.md): after r cheap failures and h cached mismatches, at a boundary with no retained preparation, finish the suffix freshly if protected work so far plus remaining mandatory work is at most the sum of the largest h input weights. This keeps Q<=n+r and the exact universal worst-L frontier for every B; it weakly lowers worst W against the same-order threshold policy. The chain(2,4,1,1),r=1,B=4 improves max(W,L,Q) from(18,7,5) to(17,7,5); both have W=18 again at B>=5. General W-optimality remains unproved.

All 176,640 roots from 5,520 observed/constructed inputs retain the frontier; 285 strictly reduce worst W and 176,355 tie. All 2,552 native Java paths over four authored shapes match 144 group maxima. Eight corruptions are rejected. `TailProbe.Selector` receives cloned works/predecessors, r and a mode, and observes its own callback outcomes; neither B nor the environment's path is an input. Fixed whole-kernel work is essential; this work theorem is not transferred to variable/lazy Roslyn transformations.

## Controlled Java blocking

The probe experiment has 4,320 measurements and 1,440 warmups: four scales, r=0/1/2, same/disjoint bins, two policies, three JVMs, 30 measured repetitions per setting. At B=r both policies have Q=4+r and W=(11+r)s, while protected selected iterations are11s versus0. Issue-to-entry times include synchronization/scheduling. At the largest scale, sums of four same-bin waits have medians about 26.8 ms versus 31.2 us; disjoint signed differences are submicrosecond and sometimes reverse. These forced arrivals demonstrate a conditional collateral-blocking effect.

The original checker missed cross-job/timing constraints; version2 rechecks the same raw records and rejects12 corruptions. [Complete results](evidence/RESUMED_20260909_1413/probe_blocking_01/recheck02/RESULTS.md), all 24 cells, three-fork medians and descriptive NumPy bootstrap intervals remain available. The standard-library replay reconstructs raw validity, independent integer outputs, medians and per-fork/secondary summaries; it does not recompute NumPy bootstrap intervals. The earlier JMH calibration remains adverse: only 2/8 settings admitted, all fitted protection premiums0, and no measured third-mode gain in admitted roots.

## Roslyn source boundary and all outcomes

Pinned [Roslyn source](https://github.com/dotnet/roslyn/tree/6c4a46a31302167b425d5e0a31ea83c9a9aa1d09) is MIT-licensed; [license/notices](licenses/roslyn) accompany the modified `Workspace.cs` files. The patch changes only the foreground SourceText document-update path; background writes retain the original algorithm. The original loop transforms an immutable solution outside a semaphore and retries on identity mismatch. Two/three-mode variants spend a global r failures and then use fresh protected computation or cached completion. SourceText no-ops preserve the pre-lock return in patch03.

The initial patch02 deadlocked on a same-text update reentered from its notification callback: one original 3-second TIMEOUT is retained in `reentry_outcomes01/two`. Patch03 repairs that no-op and all four repaired/original/unmodified controls complete. This does not establish arbitrary reentrant-host safety.

- Authored linked-project grid: 204 cases and 16 zero-writer unmodified controls succeed. Original-patch timing campaign: 3,960 measurements plus 792 warmups. Three-mode paired foreground medians are lower/higher/tied versus original in17/26/1 settings, and lower/higher versus two in14/30 settings. These are patch02 timings, not silently attributed to patch03.
- Repository projection: four MSBuild-evaluated projects,3,837 pristine files/4,019 document occurrences/40.8MB; two package-external items excluded before outcomes. Maximum-sharing then maximum-size target:63,593 bytes in two projects; largest unique background:977,535 bytes. Includes internal project references, but does not reproduce editor/compiler configuration or request compilation.
- Patch03 repository execution:69development and 4 quiet unmodified controls, then990 measurements plus 198 warmups, all complete. Per330 measured batches/mode, foreground admissions are original/two/three=2,040/1,590/1,590; protected transformations0/1,080/450; total transformations2,040/1,590/2,040. For each comparator, three-mode paired foreground medians improve in4 settings and worsen in7. All 33 cells and 22comparisons remain available.

Q excludes background-writer admissions. Each mode gets B writes at its first B foreground prelock opportunities; equal totals do not imply identical intermediate observations. The harness checks all 4,016 untouched SourceText object references, captured linked text, notification content and event count/order; event OldSolution/NewSolution payloads, untouched metadata/project state and arbitrary host equivalence are not checked. Baselines are zero-writer controls and have no trace/mutation reconstruction. Source hashes and target-comment strings are prepared before whole-unit timing. The [post-outcome coverage correction](evidence/RESUMED_20260909_1413/roslyn_source_01/REPOSITORY_COVERAGE_CORRECTION.md) preserves and narrows the original plan/receipt wording.

## Reproduction

Python 3.10+ and its standard library suffice for all 21standard stages:

```sh
python3 charged/reproduce.py all --out work/all --timeout 300
```

New individual stages are `adaptive-work`, `probe-blocking`, `roslyn-source` and `protected-tail`. The Roslyn stage checks all 6,453saved native records plus 8 reentry outcomes, retaining the one TIMEOUT. Original/public manifest hashes are explicitly bridged only for author-path projections. The guarded-tail stage reconstructs all equations and saved Java paths. Optional fresh fixed Java execution:

```sh
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py protected-tail-java --out work/tail-native --timeout 300
```

Optional Roslyn rebuilding uses separately acquired source/SDK; no runtime, package cache or source archive is redistributed. The original native setup used SDK10.0.100-rc.1.25451.107 with net8 Roslyn assemblies under the net10 driver. Source archive SHA256:`7b0bfa1c049eeddf3257ad61b28eca11c259296d478edd4cf58767b2ed9184c4`. [SDK URL and official SHA512](evidence/RESUMED_20260909_1413/roslyn_source_01/SDK_SELECTION.json); [source URL/hash receipt](evidence/RESUMED_20260909_1413/roslyn_source_01/TOOLCHAIN_MATERIALIZATION_RESULT.json).

```sh
python3 charged/roslyn_native.py \
  --sdk /absolute/path/to/pinned-dotnet \
  --source-archive /absolute/path/to/roslyn.tar.gz \
  --packages /absolute/path/to/optional-reused-nuget-cache \
  --out /absolute/path/to/new-native-replay
```

Omit `--packages` to use a fresh package cache. Network restore is then required. Output paths must contain no glob metacharacters because MSBuild treats them specially. The script authenticates the source archive, checks every projected source file, preserves pristine input texts, builds unmodified and patch03 assemblies, replays4 quiet controls/69 repository cases and 4same-text reentry controls. It does not rerun timing campaigns. Fixed semantic replay is not a new population, third-party certification or proof of submission readiness.

The [full sharp-ratio proof](supplements/ratio_proof_supplement.tex) and [detailed Deephaven source bound](supplements/deephaven_source_supplement.tex) supplement the paper. All earlier zero-fee, charged, native, calibration and Deephaven adverse results remain unchanged.

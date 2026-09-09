# Source semantics, independent arrivals, and partial-repair boundaries

This extension preserves every earlier source experiment and adds four portable stages, bringing the standard replay to 26. These are author-side checks and authored workloads. They establish neither application prevalence nor a numerical Roslyn service-level requirement.

## Source implementation and exact coverage

The pinned Roslyn revision remains `6c4a46a31302167b425d5e0a31ea83c9a9aa1d09`. The new source work addresses event and host behavior that the preceding study did not check. Every native semantic unit retains publication chains, old/new Solution payloads, immediate and queued events, linked document order/content, callback snapshot bindings, and projections of all 4,016 untouched documents in the 4,019-document/four-project source projection. Native assertions check text identity, versions and metadata. This is a finite projection check, not equivalence of every compiler cache or arbitrary host behavior.

| Version | Fixed semantic units | Outcome |
|---|---:|---|
| Patch03 with the strengthened event/state harness | 174 patched + 4 quiet unmodified | 178 SUCCESS/PASS |
| Patch04 with the same semantic harness | 174 patched + 4 quiet unmodified | 178 SUCCESS/PASS |
| Guarded rebase with additional source alternatives | 232 patched + 4 quiet unmodified | 236 SUCCESS/PASS |

The patch03 missing-document error path introduced a concrete deadlock: `GetDocumentName` could call host code while the nonreentrant serialization semaphore was held. Four of 14 constructed error-hook processes timed out at their original three-second caps. Patch04 retains the captured Solution and defers that exceptional transformation outside protection; all 14 identical inputs complete. Four same-text controls also complete. The rebase successor completes 18 error-hook and five same-text controls. The new reentry stage checks all 55 processes, with 51 original successes and four retained TIMEOUTs. It never reruns those failures or marks them repaired retrospectively. The earlier, separate patch02 same-text TIMEOUT remains in the old `roslyn-source` stage.

Guarded rebase is a legal source alternative outside the paper's opaque whole-kernel call interface. It checks the Solution ID, related-document sequence and affected project-state identities, then merges prepared document contents into the latest Solution. An ineligible change uses the repaired three-mode path. Merging performs protected work even when the full-transform counter is zero. No theorem identifies merge cost with a constant μ or a full transformation.

Source and complete outcomes: [patch03 event checks](evidence/RESUMED_20260910_0343/roslyn_semantics_01/REPORT_JA.md), [error counterexample](evidence/RESUMED_20260910_0343/roslyn_error_reentry_01/REPORT_JA.md), [patch04](evidence/RESUMED_20260910_0343/roslyn_patch04_01/REPORT_JA.md), [rebase](evidence/RESUMED_20260910_0343/roslyn_rebase_01/REPORT_JA.md). The modified sources retain the [Roslyn MIT license and notices](licenses/roslyn).

## Complete independent-arrival studies

Each unit uses 32 serial foreground text updates and 64 background requests. A producer schedules requests independently at fixed intervals 0,10,100,1000 microseconds; a FIFO background worker executes them. There is no forced foreground prelock callback. Source materialization, setup, request times, publication times, queue/service delay, garbage collection and whole-unit costs are retained. Requested arrivals are distinguished from actual writes overlapping the foreground interval.

| Study | Arms/process forks | Measurement | Warmup | Total |
|---|---|---:|---:|---:|
| Initial | 6 arms × 3 forks | 720 | 144 | 864 |
| Balanced | 6 arms × 6 cyclic blocks | 1,440 | 288 | 1,728 |
| Rebase comparison | 8 arms × 8 cyclic blocks | 2,560 | 512 | 3,072 |

All 5,664 units complete and pass the applicable raw checker. The initial shuffled order accidentally placed all instrumented-original processes first; that limitation is preserved. Subsequent cyclic blocks balance process positions, and each study has a separate plan and denominator. The first rebase summary script had a denominator typo detected before its execution; the original script and the correction are retained, and analysis02 does not rerun any observation.

In the rebase study, 320 measured batches per arm have full-transform counters as follows. Q counts foreground serialization admissions only.

| Arm | Q | Protected full transforms | Total full transforms | Protected merges |
|---|---:|---:|---:|---:|
| Instrumented original | 18,964 | 0 | 18,964 | 0 |
| Two, r=0 | 10,240 | 10,240 | 10,240 | 0 |
| Three, r=0 | 10,240 | 4,274 | 14,514 | 0 |
| Two, r=2 | 10,802 | 7,131 | 10,802 | 0 |
| Three, r=2 | 10,786 | 3,641 | 14,427 | 0 |
| Rebase, r=0 | 10,240 | 0 | 10,240 | 4,219 |
| Rebase, r=2 | 10,240 | 0 | 10,240 | 4,528 |

At the 100-microsecond interval and r=2, three-mode/background p95 has median 60.00 microseconds versus 306.1 for two-mode, with improvement in 7/8 block medians. Foreground medians are 693.98 versus666.38 microseconds; across blocks the ordering is mixed. Bursty cases also retain foreground regressions. Rebase performs fewer full transformations, but its foreground/background timing does not consistently beat three-mode. The r=0/r=2 rebase arms have the same eligible-update behavior yet different timing, so these data do not calibrate a merge premium or establish a general speedup. The replay reconstructs all cells and per-fork summaries, including unmodified baseline and the adverse comparisons.

## What partial repair changes mathematically

These two specified interfaces are distinct from the source experiment. Neither is inferred from the timing data.

First, one job contains positively weighted independently prepared components. A fixed footprint family Γ defines which components each write invalidates; only the dirty union is observed. Each protected call may repair that union and publish the whole job, or reject and prepare again outside. There are at most q=r+1 calls. Let G(b) be the largest weight covered by at most b footprints. With component repair as the protected cost, the known-budget minimax optimum is G(floor(B/q)). Among B-unaware policies required to have zero protected repair for every B≤r, retry-first attains the pointwise best envelope G(max(B−r,0)). A common policy optimal for every B exists exactly when r=0 or one footprint already covers every reachable component. Finite multiplicative ratio imposes that low-budget zero condition; its optimum is at most q and the bound is sharp. This compares controllers in the same partial-repair interface. It is not an upper bound on Roslyn rebase's gain over whole-kernel fallback.

The [proof](evidence/RESUMED_20260910_0343/partial_repair_01/PROOF.md) and all 3,495 inputs/160,080 exact finite rows are included. The historical JSON key `all_undominated_policies` is a misnomer: it contains all nine canonical candidate policies, including dominated ones; the raw bytes remain unchanged.

Second, charge a common mandatory μ≥0 once on publication under every mode. The known-budget value becomes μ+G(floor(B/q)), while the all-B exactness criterion is unchanged. Competitive synthesis can now choose early partial repair. A finite compiler uses remaining calls and e, the sum of minimum footprint counts consistent with the observed dirty sets. It never receives actual B. In a three-singleton/unit-weight example with q=3 and μ=2, optimal ratio 3/2 improves on retry-first 5/3. There are only six strict improvements in the full 20,920-row grid; all 20,914 ties are preserved. Six hundred inputs also match a direct history-tree implementation, and two inputs each match an exhaustive 4,096-policy enumeration. [Full proof and counterexample](evidence/RESUMED_20260910_0343/partial_repair_baseline_01/PROOF.md). This declared μ is not Roslyn's measured merge cost. General footprint preprocessing can be exponential; no compact-input polynomial claim is made.

The [closest-work analysis](evidence/RESUMED_20260910_0343/closest_guarantees_01/REPORT_JA.md) explicitly credits established optimistic fallback, quantitative games and synchronization optimization. The new boundary calculations do not by themselves establish strong novelty or practical importance.

## Reproduce

The four portable stages require only Python 3.10+:

```sh
python3 -B charged/reproduce.py roslyn-semantics --out work/source-semantics
python3 -B charged/reproduce.py roslyn-reentry --out work/source-reentry
python3 -B charged/reproduce.py roslyn-arrivals --out work/source-arrivals
python3 -B charged/reproduce.py partial-repair --out work/partial-repair
```

`all` includes these and the preceding 22 stages. Every invocation requires a fresh output directory. Original/public hashes bridge only documented author-path projections; no semantic predicate is relaxed. These portable stages recompute saved-output checks and exact equations, not additional timing measurements.

Optional fresh source execution uses the same separately obtained [SDK and authenticated source archive](BOUNDED_SOURCE.md#reproduction):

```sh
python3 charged/roslyn_extended_native.py \
  --sdk /absolute/path/to/pinned-dotnet \
  --source-archive /absolute/path/to/roslyn.tar.gz \
  --packages /absolute/path/to/optional-reused-nuget-cache \
  --out /absolute/path/to/new-extended-native-replay
```

The helper verifies all 3,837 pristine source files, builds unmodified and rebase assemblies, and executes the fixed 236 semantic cases plus 18 error-hook and 5 same-text controls. Omitting `--packages` uses a fresh package cache and network restore. Output paths must not contain glob metacharacters. Each child command has a recorded timeout and preserves failure logs. Source/SDK archives and binary package caches are not redistributed.

# Extended-budget single-trial protocol

This is an overlay for a **separate copy** of `campaign/`. The original baseline
runners, configurations and results remain in their existing locations. This
directory contains five exact configurations, their staged runner, analyzer,
orchestration checks and the shared runtime override. It contains no models,
JARs, private runbook or archive. Relative model and runtime paths resolve from
the root of the overlaid campaign copy, not from this extension directory.

As of 27 September 2026, none of these 27 extended trials has returned. Their
saved display is **NOT_RUN**; a preflight plan is not a measurement. These
single trials are separate from the fixed-budget five-repetition campaign.

| Configuration | Planned trials | Heap | Whole-JVM cap per trial |
|---|---:|---:|---:|
| `ext1_travel_frontier` | 4 | 64 GiB | 7,200 s |
| `ext2_rq3_df_cpu` | 2 | 64 GiB | 7,200 s |
| `ext3_travel_next` | 5 | 64 GiB | 7,200 s |
| `ext4_rq3_df_heap200` | 12 | 200 GiB | 7,200 s |
| `ext5_travel_heap200` | 4 | 200 GiB | 7,200 s |

The cap sum is 12 hours for ext1+ext2 and 54 hours for all 27 trials, excluding
preflight and collection. Scheduling skips may shorten execution. Everything
runs serially, once per cell; terminal outcomes are preserved on resume.

## Apply to a fresh copy (PowerShell, package root)

```powershell
$work = Join-Path $PWD 'replication\ext-campaign'
if (Test-Path $work) { throw 'Choose a new extension workspace' }
Copy-Item .\campaign $work -Recurse
$delta = Join-Path $PWD 'campaign\extensions\ext'
foreach ($dir in @('configs','scripts','runtime')) {
    New-Item -ItemType Directory -Force (Join-Path $work $dir) | Out-Null
    Copy-Item (Join-Path $delta "$dir\*") (Join-Path $work $dir) -Recurse -Force
}
foreach ($file in @('run-ext.ps1','run-all.ps1')) {
    Copy-Item (Join-Path $delta $file) (Join-Path $work $file) -Force
}
Set-Location $work
```

## Plan only (no Java required)

```powershell
foreach ($name in @('ext1_travel_frontier','ext2_rq3_df_cpu','ext3_travel_next','ext4_rq3_df_heap200','ext5_travel_heap200')) {
    python scripts\campaign.py --config $name --stage plan
    if ($LASTEXITCODE -ne 0) { throw "Planning failed: $name" }
}
```

This writes configuration and plan files under `raw/<configuration>/`, but
starts no JVM and supplies no outcome. Repeating plan generation checks the
existing plan identity rather than replacing it with another configuration.

## Execute on the campaign host

Use the declared Windows Xeon W-2265 host, JDK 17, Python 3.10+ and at least
240 GiB physical memory and 50 GiB free disk. Exact execution also requires the
original measured JAR at
`Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar` within
the working copy; preflight requires SHA-256
`fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07`.
That binary is not distributed. A source-built JAR has different bytes and
cannot pass this exact-campaign check. Planning and saved-result analysis do
not require any JAR.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-ext.ps1 -Python python -Java java
```

The wrapper selects ext1 through ext5, each with stage1 then collect. The
underlying `run-all.ps1` retains the older campaign names, but its default list
is the baseline campaign: use `run-ext.ps1` for this extension. Resume with the
same command and the same working copy. Retain complete per-campaign raw
folders, including configs, plans, metadata, outputs and skip reasons.

For ext5, each method is independent. The default order is K1 Lazy, K1
Direct-Full, K4 Lazy, K4 Direct-Full. K1 at 200 GiB is unnecessary if that same
method's ext3 K1 at 64 GiB has a verified SUCCESS. Otherwise it is eligible;
missing/incomplete prior evidence counts as no observed SUCCESS and is recorded
as such. K4 at 200 GiB is eligible only after verified SUCCESS for that method's
K1 at 64 or 200 GiB. SUCCESS requires completed provenance and certificate/Link
checks. If K1 at 200 GiB times out or runs out of memory, K4 is skipped. K6 is
not included.

Explicit monotone skipping propagates only actual TIMEOUT/OOM evidence under
matching method, target, properties, heap and cap; earlier 64 GiB resource
failures do not automatically propagate to 200 GiB. A skip is a scheduling
cutoff, not an inferred TIMEOUT, OOM or LOSS for the larger case. Invalid and
missing prerequisites remain visible with reasons. RSS is process working set,
not heap occupancy; the 200 GiB series changes the resource condition.

## Recreate the supplementary table (no Java)

Run this from the overlaid campaign copy after restoring the package's raw
assets. `--input-root` is the archived raw tree or another returned raw tree;
`--output` must be outside it. Use a fresh output directory to preserve earlier
analyses. For the layout created above:

```powershell
python scripts\analyze_ext.py --input-root ..\..\FSE2027_SUBMISSION_20260914\experiments\rq3_xeon\raw --output analysis\ext
```

The outputs are `ext-budget.csv`, `ext-budget.tex` and
`ext-budget-macros.tex`. With the currently returned evidence, all 27 rows are
NOT_RUN, received/checked counts are zero, and timing/RSS cells are unmeasured.
`rq3/summary.csv` and `rq4_travel/summary.csv` supply the fixed-budget Lazy
comparators. After a completed extension is returned, place its untouched
per-campaign raw folder under the chosen input root and run the same analyzer
into a new output directory. It rereads original metadata/output, preserves
invalid/incomplete/skip/resource outcomes, and reports a ratio only for checked
matching decisions against a five-valid-repetition baseline. Whole-JVM and
solver ratios remain separate; one extended trial is not a median.

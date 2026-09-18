# Windows measurement campaigns

Use the portable layout in `campaign/`. The nested
`FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/` contains the paper's source layout,
renderers and archived measurements. The input/configuration bytes and runtime scripts are the same;
new executions and archived results have separate destinations.

## Prepare the host

Use Windows on a Xeon W-2265 with 256 GB RAM, a 64-bit JDK 17, and Python 3.10+.
The runner checks at least 240 GiB physical memory and 50 GiB free disk.
Put the package on a short local path, outside synchronized folders and network drives.
Use the same JDK vendor/patch version for all repetitions and avoid other heavy workloads.

Build the tool as described in the main README. The public package contains no executable JAR.
Copy your locally built JAR into the portable layout before starting a new replication:

```powershell
# Run from the package root after the Maven build.
$target = 'campaign\Implementation\Source Code\maven-root\mtsa\target'
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item 'Implementation\Source Code\maven-root\mtsa\target\mtsa-1.0-SNAPSHOT.jar' $target
Set-Location campaign
java -version
python --version
```

Use this placement only in a fresh campaign. Never replace the JAR of a campaign that already has runs.
The built binary has a new identity; new measurements are a separate replication, not replacement evidence.
Maven and network access are needed to build and fetch dependencies, but not during the campaign.
The portable directory includes the small supporting runtime and model copies; their bytes match the source layout.

## Plan and run

Inspect a plan without launching a JVM:

```powershell
python scripts\campaign.py --config rq3 --stage plan
```

Run the complete five-campaign sequence:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-all.ps1
```

The driver runs stage1, stage2 where applicable, and collect in order, with one JVM at a time.
It suppresses sleep during execution and records a transcript under `campaign/raw/`.
Alternatively, run stages individually:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq3 -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq3 -Stage stage2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq3 -Stage collect
```

Pass `-Python C:\path\python.exe -Java C:\path\java.exe` if PATH resolves another runtime.
The wrapper changes to its own directory. Native stderr is captured as text and the native exit code is checked.
The startup probe must verify child-JVM RSS sampling and process-tree termination before trials begin.
PowerShell parser validation on macOS checks syntax, not Windows system calls;
the saved Windows transcripts and startup-probe records document the original execution environment.

## Cases, limits and repetition rules

| Campaign | First-stage cells | Maximum repetition slots | Per-job cap |
|---|---:|---:|---|
| rq3 | 27 instances x 5 methods = 135 | 675 | 64 GiB heap / 1,200 s |
| rq4_independent | 19 K values x 4 methods = 76 | 380 | 64 GiB / 1,200 s |
| rq4_controlled | 33 games x 4 methods = 132 | 132 | 64 GiB / 1,200 s |
| rq4_travel | 48 settings x 4 methods = 192 | 960 | 64 GiB / 1,200 s |
| rq4_hub | 90 games x 4 methods = 360 | 1,800 | 64 GiB / 1,200 s |

The full grid has 895 first-stage cells and at most 3,947 trial slots, over 1,315 hours of cap time.
Actual elapsed time is much smaller when small jobs finish quickly and resource failures eliminate repetitions.
Allow days for a full replication, not one night. Frontend, JVM startup and collection add overhead.

Retain every stage1 cell. A first-stage WIN or LOSS with valid checks is eligible for four further trials.
TO, OOM, invalid or inconsistent results are not retried; remaining slots receive explicit skipped statuses.
Only five valid, decision-consistent completions receive median and min–max time summaries.
The controlled family is single-run structural evidence, not a timing-median comparison.

Re-running the same driver resumes only unstarted cells. An interrupted running cell becomes
`INTERRUPTED_NOT_RETRIED`; never delete its directory to obtain a different outcome.
An OS lock prevents simultaneous JVMs across campaigns. After power loss or forced termination,
check for a surviving experiment JVM before resuming; that situation bypasses normal cleanup.

Independent K values are every integer 2 through 20. Travel uses
N={1,2,4,6,8,12} and K={1,2,4,6,8,12,16,20}. Hub uses the saved 30 seeds and three UC profiles.
No seed, cap or model is selected retrospectively. RSS is the maximum sampled child-JVM working set,
with about 100 ms between samples; a short peak can be missed.

## Collect and render

Preserve the entire new `campaign/raw/` tree, including plans, environments, skipped rows, logs and all run directories.
Do not merge it into the archived raw. Keep its new binary/host identity and use a separate output directory.
The supplementary trials use `run-supplement.ps1`; see [their protocol](RQ3_SUPPLEMENT.md).
Legacy fidelity has separate inputs and tooling under `experiments/legacy_fidelity/` and is not part of Table 3.

Restore the published assets for reproducing the paper's original displays, then run from the package root:

```sh
python -m pip install -r FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/plot-requirements.txt
python FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/scripts/render_results.py --mode xeon --input-root FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw --output replication/rendered
python FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/scripts/analyze_results.py --input-root FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw --output replication/rendered
```

Use a fresh `replication/rendered/` directory. `quickstart.py` provides the checked, no-overwrite route.
Original raw is read only; summaries and plots are derived outputs.
See [provenance](PROVENANCE.md) for timer scopes and the distinction between paper data and small Mac pilots.

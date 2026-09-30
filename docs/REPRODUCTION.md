# Reproduction guide

Start with `python3 reproduce/check.py --output work/check` from the public root, using Python 3.10+ and the packages in `reproduce/requirements.txt`. This is a saved-evidence check, not a benchmark rerun. The public source contains no JARs. The expected full result is PASS with no skipped checks. Logs are separated into core, supplement and extensions; the restored compatibility workspace is under the chosen output directory.

## Why a compatibility workspace exists

Original scripts and configurations refer to `Implementation/` and `FSE2027_SUBMISSION_20260914/experiments/`. Moving those references inside every saved script would unnecessarily alter research programs and manifests. `reproduce/materialize.py` therefore verifies the purpose-based public files and copies them back to their original relative locations in a fresh directory. It also verifies and unpacks all large raw archive parts and writes the compatibility manifest expected by the archived checkers. The public `reproduce/layout.json` gives the exact mapping. No symlink support is required.

## Build and inherited headless example

From the public root:

```sh
python3 tool/build.py --variant baseline --output work/baseline
cd work/baseline
python3 campaign/scripts/run_cell.py --model gsm --output replication/gsm-base
```

The example uses 4 GiB, a 60-second whole-JVM cap, one repetition and the recorded Lazy properties. `--plan-only` previews the command; `--model metasocket` selects the other small example. Its observation is separate from the fixed Xeon table. Use `tool/run.py` from the public root with variant `e1` for the explicit finite JSON examples and their standalone HTML reports.

## Full workspace, correctness and performance reruns

From the public root:

```sh
python3 reproduce/materialize.py --output work/full
cd work/full
python3 fetch_assets.py --asset dependencies
mvn -B -f "Implementation/Source Code/maven-root/mtsa/pom.xml" package -DskipTests -Djacoco.skip=true
python3 reproduce_validation.py rq1 --plan-only --output replication/rq1-plan
python3 reproduce_validation.py rq2 --plan-only --output replication/rq2-plan
```

Remove `--plan-only` and choose different fresh output directories to execute. `--derive-only` runs the Python oracle derivations without Java. A run directory must be below the materialized workspace because the archived harness uses workspace-relative paths. Inspect generated plans before reserving machine time. The JAR is locally rebuilt; retain its observed hash.

The original large campaign's entry point is `campaign/run-windows.ps1`; its detailed protocol is `campaign/README.md`. The `campaign/` material is the fixed campaign and original ext1–5 planning package. **Its pre-run extension statuses are historical**, not current observations. Final ext1–7 results are under `FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/ext*_*/`. Newer scripts are in that experiment's `scripts/`, configurations in `configs/`, and the original PowerShell commands include `run-ext.ps1`, `run-ext2.ps1`, `run-ext7.ps1` and `run-all.ps1`. Preserve the separate stages and failures.

For a new performance run, copy the selected saved configuration to a fresh local configuration, set the classpath to the relevant rebuilt JAR and `results_root` to a new replication directory, and use the archived `Implementation/Experiment/FSE2027/scripts/run_experiment.py --config NEW.json --dry-run`. Review the resulting plan before dropping `--dry-run`. Hardware checks in the Xeon protocol are intentional. A smaller machine can run examples but cannot reproduce a 200 GiB heap experiment. Never point a new configuration at distributed raw directories.

## Experimental variants and finite families

`reproduce/solver-variants/variants.json` records measured commits, JAR hashes and complete baseline-relative patches. The baseline is used for the main fixed comparison and ext1–7; E2 adds full construction with UC pruning; E1 includes E2 and contract merging; E5 includes E1/E2 and physical-initial transfer preprocessing. Apply exactly one patch in a fresh source tree. A rebuilt binary need not have the measured JAR's bytes.

Materialized E1/E2 scripts live in `FSE2027_SUBMISSION_20260914/experiments/ablation_20260928/scripts/`; E4/E5/E6 live in `.../experiments/witness_20260929/`. The original run scripts record fixed experiment inputs, host-specific paths and measured-JAR expectations; those are provenance, not universally portable commands. Use the public `tool/run.py` for a single finite-model replication. It copies the adapter, substitutes only the actual local JAR digest in that copy, compiles it, and preserves all input/source hashes. It does not rewrite the archived driver or results.

The main E6 canonical inputs are Rolling v1, Canary v1, Policy v2, DB-Rolling v2 and Rolling-Audit v1. Threads and PC2 are included in the same main index; scale, assumption controls and Cell reference trials have separate denominators. The family directories provide generators, schemas, interpretation and saved decisions. `independent/check_games_v3.py --help` describes the independent finite-game checker. `reproduce/check_extensions.py` invokes 22 small canonical checks (18 distinct games) and validates the saved larger denominators without rerunning long Java trials.

## Metrics and certificate boundaries

- Solver time and whole-JVM elapsed time are different columns. The cap is on the JVM process. Fixed complete cells have five-run medians; extended campaigns are single trials.
- `states_discovered` counts states reached by the selected algorithm, not a common full-game denominator. Enabled buckets count state/action queries with nonempty Post; transition outcomes count the alternatives in those buckets.
- Process RSS includes more than the Java heap. Missing final counters for TO/OOM must stay missing. No censored state/time ratios are imputed.
- `internal_certificate_check=passed` in an inherited FSP log records an executed check. It is not itself an exported certificate. Some inherited runs provide output and transitions rather than the explicit E6 JSON certificate format. E6 completed decisions provide `result.json` plus serialized `certificate.json`; invalid and timed-out trials need not.
- Link checks apply to WINs. LOSS provides a checked discovered losing region, not necessarily the maximum losing region. Viewer output is an inspection aid, not a new independent semantic proof.

## Observed package validation

The October 2026 reorganization was checked after restoring the public layout: all 11 core checks passed with no SKIP, all supplement tasks passed, and E-series/ext1–7 checks passed. The core check regenerated the complete 135-cell table and scaling figures and preserved 16,027 inspected files. The extension check preserved 3,996 inspected files and independently reconstructed 22 small finite jobs. A comparison with the prior anonymous E6 export found 3,070 raw/input/result/certificate files unchanged and none missing. These are artifact-validation observations; they are not additions to research sample sizes.

Baseline and E1 source builds succeeded with JDK 17 and the existing Maven cache. The newly built E1 JAR produced the expected small Rolling WIN and merged LOSS with certificate/endpoint checks, and WIN Link checking. No claim of a new empty-cache build or a full performance rerun is made.

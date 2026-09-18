# Fine-Grained Dynamic Update Controller Synthesis

FG-DUCS synthesizes how to update a running controlled system one component and requirement at a time.
This package contains the complete MTSA-derived sources, benchmark models, checkers, saved evidence and the paper's proofs.
Start with the Python-only checks below; build the Java tool to synthesize a controller yourself.
The larger measurement logs are separate downloadable assets, while the saved tables and correctness evidence are in this repository.

**Preview: branch main. Submission revision: tag fse27-submission (created at the final push).**

Read [the paper](paper/main.pdf) and [the supplement](paper/supplement.pdf).
The source preview is public; the two raw-data assets await the `v2-preview` pre-release.

## What the tool does

Describe pairs of old and new components and the allowed state transfers between them.
Give the old and new safety requirements, their individual stop/start boundaries and monitor initializers,
requirements that apply during the update, ordering constraints, and compatible handover targets.
The synthesizer chooses an update policy that works from every admitted old state and for every transfer outcome.
Update commands and final handover wait for uncontrollable quiescence.

A successful result contains a policy, a strictly decreasing rank and a compatible handover table.
A losing result contains a losing region explaining why the supplied finite game cannot guarantee completion.
Certificate checking validates these results against the game; it does not validate the application's modeling choices.
Execution additionally requires sound residual initialization and the runtime assumptions stated in the paper.
The separate checker shares the frontend and transition semantics with the synthesizer; all checkers belong to the same author team.

## Quick start

Use **Python 3.10+**. Allow about **10 minutes**; no Java, Maven or downloaded dependency is needed for the core checks.
From the repository root, run:

```sh
python quickstart.py
```

The script prints a claim / expected / observed / PASS-or-FAIL table and saves it as
`replication/quickstart-report.md`, with detailed logs in a fresh run directory.
It checks saved RQ1/RQ2 evidence, independently derives expectations from the LTS inputs,
checks the finite paper witnesses and their drawings, recomputes residual coverage,
and reconstructs the monolithic Industry comparison.
Saved-graph and measurement checks that need the raw assets are explicitly marked **SKIP** until those assets are restored.
With the assets and Matplotlib installed, it also regenerates Table 3 and Figure 3 and compares their principal values.

| Check | Expected evidence |
|---|---|
| RQ1 saved decisions | 92 jobs: 36 WIN, 48 LOSS, 8 invalid inputs |
| RQ2 saved decisions | 14 jobs: 10 WIN, 4 LOSS |
| Independent expectation derivation | 46 RQ1 input rows; 14 RQ2 tool/input rows |
| Paper witnesses and drawings | Fine/bulk, observation and requirement-boundary cases agree |
| Residual initialization | H: 0/273 certified; A: 138/138 sound; E': 89/135 exact, 46 unverified |
| Monolithic comparison | Both saved meta-product censuses and the entry-label obstruction agree |
| Contract variant, after restoring raw | All 131 roots WIN; rank and validation-response checks pass |
| RQ3, after restoring raw | FG: 25 WIN / 1 LOSS / 1 TO; Direct-Full: 14 WIN / 13 TO |
| Legacy RQ3, after restoring raw | 9 WIN / 13 OOM / 5 N/M (capture cap) |

On the checked macOS host, the core run took **2.7 seconds**; restored raw plus Matplotlib took **23.0 seconds**, with all 10 checks passing.
See [reproduction details](docs/REPRODUCTION.md) for scope and the saved reports.
Results depend on storage and processor speed; the 10-minute allowance is not a timeout used in the experiments.
An existing report or output directory is never overwritten.
To repeat the checks, use a fresh destination, for example `python quickstart.py --output replication/second-check`.

## Reproduction tiers

| Tier | Requirements and time | What you obtain |
|---|---|---|
| A: inspect and recompute | Python 3.10+, minutes; Matplotlib optional | Saved-record checks, raw-LTS expectations, witness and residual checks; asset-backed figure regeneration when available |
| B: run the tool | 64-bit JDK 17, Maven, network for dependencies; observed clean builds about 3–11 minutes | GUI and headless synthesis, fresh RQ1/RQ2 runs, small RQ3 examples |
| C: repeat measurements | Windows Xeon W-2265, 256 GB RAM, JDK 17, Python; days | Serial, resource-capped campaigns using `campaign/run-all.ps1` |

Tier A does not repeat the Java experiments. RQ1/RQ2 synthesis in Tier B uses the saved case settings;
RQ1 needs room for its 12 GiB heap, and its full sweep takes longer than building.
GSM/base and MetaSocket/base are small seconds-scale RQ3 examples on the measured host,
not a guarantee for another machine or for the other 25 application instances.
Tier C uses a 64 GiB heap and 1,200-second cap per job, with separate settings for the supplementary trials.
The cap sum for the full planned grid exceeds 1,300 hours; failure-based skipping reduces actual execution substantially.

`campaign/` is the portable Windows execution layout; the nested
`FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/` retains the paper's source layout and archived results.
The duplicated model and runtime support files have identical bytes.
Keep new runs under `campaign/raw/` or a fresh `replication/` directory, separate from the archived evidence.

## Using the tool

### Recommended usage

1. Install a 64-bit JDK 17 and Maven, and put `java`, `javac` and `mvn` on `PATH`.
2. Fetch the exact third-party dependencies from their upstream locations:

```sh
python fetch_assets.py --asset dependencies
python fetch_assets.py --asset dependencies --verify-only
```

3. Build the tool from the repository root:

```sh
mvn -B -f "Implementation/Source Code/maven-root/mtsa/pom.xml" package -DskipTests -Djacoco.skip=true
```

This compiles tests but does not run them. [Reproduction details](docs/REPRODUCTION.md) include focused test commands,
an empty-cache build recipe and the recorded build environments.
The generated JAR is for local use and is not byte-identical to the measured binary.

4. Start the GUI:

```sh
java -jar "Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar"
```

5. Open `Implementation/Experiment/Models/GSM_FG.lts`.
   Follow the file's opening comments: select `UPDATE_CONTROLLER_OTF_FG`, then **Compose** (`||`).
   The suffixed targets select the different update-time requirements.
6. Inspect the result using **Transitions**, **Draw**, or **Animation** (the blue **A**).
   Inspect the output pane for the decision, certificate verification and Link check.

A saved `internal_certificate_check=passed` field records an executed check; it is not itself a serialized certificate.
Inspect a run's `output.txt`, `meta.json` and any emitted `transitions.txt` together.
Invalid inputs have no game certificate, and Link checking applies to winning results.
The Java classes under `ltsa.updatingControllers.otf` define policy/rank/handover and losing-region evidence.

### A headless example

After building, run one GSM/base lazy cell through the campaign runner:

```sh
python campaign/scripts/run_cell.py --model gsm --output replication/gsm-base
```

This separate local example uses a 4 GiB heap, a 60-second cap and one repetition.
It preserves the selected method properties and model bytes, and records its own configuration and outcome.
Its timing is not part of the published Xeon comparison.
Use `--plan-only` to inspect the command without starting Java, or `--model metasocket` for the other small example.
For full correctness runs, use fresh directories:

```sh
python reproduce_validation.py rq1 --java java --output replication/rq1
python reproduce_validation.py rq2 --java java --output replication/rq2
```

### Writing your own update contract

Start from `GSM_FG.lts` and keep your edited copy separate from the benchmark inputs.
The following excerpts use that model's actual names; the full file supplies the environment transitions and endpoint specifications.

```text
// Pair OLD_ENV with NEW_ENV and name one transfer event.
// The complete relation in GSM_FG.lts lists all allowed state pairs.
relation R_ENV_FG = {SENDER@OLD_ENV = reconfigure_ENV -> SENDER@NEW_ENV,
                    X@OLD_ENV = reconfigure_ENV -> X@NEW_ENV,
                    Y@OLD_ENV = reconfigure_ENV -> Y@NEW_ENV,
                    Z@OLD_ENV = reconfigure_ENV -> Z@NEW_ENV,
                    ENCODED@OLD_ENV = reconfigure_ENV -> ENCODED@NEW_ENV,
                    SENT@OLD_ENV = reconfigure_ENV -> SENT@NEW_ENV,
                    RECEIVED@OLD_ENV = reconfigure_ENV -> RECEIVED@NEW_ENV,
                    DECODED@OLD_ENV = reconfigure_ENV -> DECODED@NEW_ENV}

// Requirement boundaries are individual controllable update events.
set StopOldSpecActions = {stopOldSpec_P_DECODE}
set StartNewSpecActions = {startNewSpec_P_NEW_DECODE}
set ReconfigureActions = {reconfigure_ENV}

// Track pending operations, then express an update-time ordering requirement.
fluent Pending_StopOldSpec_P_DECODE = <hotSwapIn, stopOldSpec_P_DECODE>
fluent Pending_StartNewSpec_P_NEW_DECODE = <hotSwapIn, startNewSpec_P_NEW_DECODE>
fluent Pending_Reconfigure_ENV = <hotSwapIn, reconfigure_ENV>
ltl_property R2_StopOldSpec_P_DECODE = [](Pending_StopOldSpec_P_DECODE -> Pending_Reconfigure_ENV)
ltl_property R2_StartNewSpec_P_NEW_DECODE = [](Pending_StartNewSpec_P_NEW_DECODE -> Pending_Reconfigure_ENV)
```

The first ordering formula keeps component replacement pending until the old requirement is stopped;
the second does so until the new requirement has started.
The frontend generates the individual stop/start events from `OldSpec` and `NewSpec`.
Bind the components, relation and requirements with this block from the R2 target:

```text
updatingController UpdCont_OTF_FG_R2 = {
    oldController = OldController,
    newController = NewController,
    oldEnvironment = {OLD_ENV},
    newEnvironment = {NEW_ENV},
    mapRelation = {R_ENV_FG},
    oldGoal = OldSpec,
    newGoal = NewSpec,
    transition = R2_StopOldSpec_P_DECODE,
    transition = R2_StartNewSpec_P_NEW_DECODE,
    nonblocking,
    revised_on_the_fly,
    fine_grained
}
||UPDATE_CONTROLLER_OTF_FG_R2 = UpdCont_OTF_FG_R2.
```

A component transfer may have several outcomes; the policy must handle every outcome.
New-requirement initializers are obtained by fluent lookup, while update-time monitors use the compiled post-entry state.
Their residual guarantees have the precise A/E scopes in [residual coverage](docs/RS_COVERAGE.md).
The default handover candidates are all reachable states of the verified new closed loop, filtered by goal compatibility and quiescence.
The mathematical contract also permits explicit precedence edges; these benchmark files declare none and encode their selected ordering in monitors.
Do not assume that a controller for the old and new endpoints alone proves that their update can complete.

## Claims-to-evidence map

Paths in this table are relative to `FSE2027_SUBMISSION_20260914/`.
Generated tables, figures and numerical macros are in `paper/build/generated/`.
Each script is executable evidence for its stated scope; the mathematical proofs remain in the paper and supplement.

| Claim or display | Where to inspect and reproduce |
|---|---|
| Figure 1; Theorem 3.4, fine/bulk separation | `experiments/paper_witnesses/check_witnesses.py`, `check_diagrams.py`; `paper/figures/witness_cell.tex`; Supplement S1.1 |
| Figure 2; Proposition 3.5, fixed heads and requirement boundaries | Same checkers; `paper/figures/witness_other.tex`; executable RQ2 fixtures; S1.2–S1.4 |
| Algorithm 1; termination, soundness and completeness | Java `ltsa.updatingControllers.otf`; RQ1/RQ2 certificates and oracle; S2.2–S2.4 |
| Lemma 4.5 and Theorem 4.6, containment and K+1 versus 2^K | `experiments/rq3_xeon/configs/rq4_independent.json`, inputs and returned raw; generated `rq4-points.csv`; S2.7 |
| Theorem 5.1, conditional trace lifting | S3 proof and A1–A4 correspondence; RQ1/RQ2 abstract Link records; runtime-platform validation remains outside this evidence |
| H/A/E residual lemmas | `experiments/rs_coverage/`, compiled-monitor exports and all preserved diagnostic columns; S3.1 and S4 |
| Table 1, RQ1 | `experiments/semantic_revision_20260914/rq1/`, `oracle/`, `rederive_oracle.py`; 92 saved jobs |
| Table 2, RQ2 | `experiments/semantic_revision_20260914/rq2/`, `derive_rq2_expectations.py`; 14 saved jobs |
| Table 3, all 135 RQ3 cells | `experiments/rq3_xeon/raw/`; generated `rq3-cells.csv`, `rq3-table.tex`, complete-range and provenance tables; S4 |
| Figure 3, RQ4 scaling | Independent, controlled, Travel and hub raw; `rq4-scaling-combined.pdf`, full panels and Travel status grid; S4 |
| Contract feature coverage | `experiments/rs_coverage/contract-coverage.csv`, LTS declarations and archived frontend census; S4 |
| Industry contract variant and monolithic cross-check | `experiments/industry_r1_contract_variant/` and `experiments/industry_r1_legacy_monolithic_check/`; S4 |
| Separate legacy reference comparison | `experiments/legacy_fidelity/inputs/`, diffs, `raw/xeon/`, collector and renderer; S4 |
| Table 4, related work | Primary DOI/URL references in `paper/references.bib`; contract locations in S5 |

## Data, statuses and provenance

The main RQ3 table retains every model/method cell, including unresolved results.

| Display | Meaning |
|---|---|
| WIN / LOSS | Realizable / unrealizable in the supplied game, with the applicable checks |
| TO | Wall-clock resource cap reached; no realizability conclusion |
| OOM | Memory failure; no realizability conclusion |
| N/M (capture cap) | Author-side capture stopped at 250,000 states before legacy synthesis |
| N/M (fork parser) | A separate reference input was rejected by the fork's stricter duplicate-name parser |
| N/M (instrumentation) | A separate reference input stopped in author-side capture instrumentation before a legacy GR decision |
| INTERRUPTED | Operational interruption, not a solver outcome |

Workflow/R2 Direct-Full is shown as **TO‡**: the original run was operationally interrupted;
a separate, same-setting supplementary attempt timed out at 1,200 seconds. Both records remain in S4.
PC Arms=2/R2 retains its 1,200-second TO; a single 3,600-second supplementary attempt also timed out.
Its sampled process RSS does not establish Java heap saturation.
Only five valid, decision-consistent completions receive a median and min–max range.
The separate monolithic legacy-fidelity comparison is not a Table 3 cell and is not a speed comparison.

Download both parts from the `v2-preview` pre-release when it is available, preserving their names.
From the package root, verify and restore them:

```sh
python restore_results.py --assets /path/to/downloaded-assets --verify-only
python restore_results.py --assets /path/to/downloaded-assets
```

[Distribution identities](docs/DISTRIBUTION.md) lists the part sizes and SHA-256 values;
`result-assets.json` lists every archived file. The restorer refuses conflicting existing bytes.
Oversized CSVs are losslessly compressed; summaries and rendering do not require their expansion.
Distribution copies anonymize personal path prefixes while retaining decisions, measurements, inputs and timestamps.
Logged original-file digests refer to the pre-redaction originals; environment files explicitly record that relationship.
See [provenance](docs/PROVENANCE.md) for timer scopes, incomplete repetitions, reference-tool differences and every supplementary trial.

## Requirements and licensing

Core checks use the Python standard library. Plot generation additionally uses Matplotlib;
Java synthesis uses JDK 17 and Maven, and paper builds use XeLaTeX, acmart and fontspec.
The main and supplementary PDFs contain no CJK fonts.
Use [LICENSE](LICENSE) and [NOTICE](NOTICE) for the exact scope of the original contributions and upstream terms.
The authors have confirmed redistribution permission for the MTSA-derived sources; existing legal headers are preserved.
Third-party dependencies are fetched from official upstream distributions by `fetch_assets.py`.
The measured shaded JAR contains FFmpeg natives marked nonfree and unredistributable and is not distributed.
A slim binary is also withheld because the terms of all libraries nested in the Synoptic bundle have not been established.
The measured binary's SHA-256 and source-rebuild procedure remain in [reproduction details](docs/REPRODUCTION.md).

## Documentation index

| Guide | Contents |
|---|---|
| [Reproduction](docs/REPRODUCTION.md) | Complete commands, clean-clone build records, verification logs and quick-start timing |
| [Provenance](docs/PROVENANCE.md) | Timers, reference tools, contract variant, supplementary runs and anonymized metadata |
| [Campaign](docs/CAMPAIGN.md) | Windows setup, serial execution, repetition rules and result collection |
| [Residual coverage](docs/RS_COVERAGE.md) | H/A/E meanings, sufficient conditions, retained diagnostics and unverified cases |
| [RQ3 supplementary trials](docs/RQ3_SUPPLEMENT.md) | Separate configurations, execution steps and links to their original records |
| [Distribution identities](docs/DISTRIBUTION.md) | Generated file and result-asset digests |

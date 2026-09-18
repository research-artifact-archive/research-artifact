# FG-DUCS replication package

This anonymous package accompanies **Fine-Grained Dynamic Update Controller Synthesis** at [research-artifact-archive/research-artifact](https://github.com/research-artifact-archive/research-artifact). The repository provides the complete MTSA-derived tool sources including the FG-DUCS extensions, models, saved validation evidence, supplementary proofs and reproduction scripts. Larger raw outputs are prepared as split assets awaiting the `v2-preview` Release, as recorded below. The authors have confirmed redistribution permission for the MTSA-derived sources; existing file headers are preserved. Included scripts fetch third-party JARs from official upstream distributions. The package includes the completed Xeon RQ3 and all controlled, independent, Travel and hub RQ4 returns. Both authorized RQ3 supplements and all legacy-fidelity campaigns have returned; existing adverse outcomes are retained.

## Contents and claim mapping

- `paper/main.pdf` and `paper/supplement.pdf`: main paper and full proofs/supplementary tables. Rebuildable sources are under `FSE2027_SUBMISSION_20260914/paper/`.
- `Implementation/Source Code/maven-root/mtsa/`: Java source and tests, with file-repository metadata stored under `dependency-metadata/`; dependency JARs are obtained separately. The principal package is `ltsa.updatingControllers.otf`.
- `Implementation/Experiment/Models/`: nine benchmark LTS files with three targets each (27 RQ3 instances).
- `FSE2027_SUBMISSION_20260914/experiments/semantic_revision_20260914/`: RQ1's 92 jobs, RQ2's 14 jobs, independent expectation derivations, and separate boundary probes. Each run retains stdout, stderr, solver output, metadata, and any transition output.
- `Implementation/Experiment/FSE2027/results/macos24-paper-final-20260805g-correctness/inputs/`: the unchanged 41 semantic LTS fixtures and five endpoint-contract fixtures. The historical path identifies source inputs; results reported here are the revised-semantic runs above.
- `Implementation/Experiment/FSE2027/rq2-formal-witness/models/`: eight capability LTS fixtures, including neutral controls. The executable cell fixtures are smaller than the paper's fully specified Production Cell construction.
- `FSE2027_SUBMISSION_20260914/experiments/paper_witnesses/`: a standalone Python reconstruction of the paper's complete branching, requirement-boundary, and Production Cell witnesses, with saved closure and policy checks.
- `FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/`: fixed configs, inputs, generators, Windows drivers, collection/rendering scripts, and completed `raw/rq3`, `raw/rq4_controlled`, `raw/rq4_independent`, `raw/rq4_travel`, and `raw/rq4_hub`, plus all three returned launcher logs. Raw has one canonical source-layout copy, restored from the result assets; root `raw/` is reserved for replications. The separate `raw/industry-r1-independent` Mac run checks correctness and supplies no Xeon timing evidence.

The checked counts are RQ1 **92/92** expected decisions (36 WIN, 48 LOSS, 8 invalid), 84/84 internal and separate exhaustive checks, and 36/36 atomic Link checks. RQ2 is **14/14** (10 WIN, 4 LOSS), 14/14 internal and exhaustive checks, and 10/10 Link checks. Invalid inputs have no game certificate; Link applies only to WIN. These are jobs, not independent applications. Saved pass records are distinguished from serialized certificate bodies: internal checks ran during synthesis, and each `transitions.txt` or other body is retained only where the original run emitted it. Re-running produces fresh check records; a pass field alone is not a serialized certificate.

## Inspect the saved results

Python 3.10+ is sufficient for the offline check:

```sh
python check_package.py
python reproduce_validation.py rq1 --derive-only --output replication/rq1-oracle
python reproduce_validation.py rq2 --derive-only --output replication/rq2-oracle
python FSE2027_SUBMISSION_20260914/experiments/paper_witnesses/check_witnesses.py --output replication/paper-witnesses
```

The two derivations parse the original LTS inputs and apply the fixed Post/goal rules without using Java decisions as expected answers. They write fresh files under the requested output directory. The raw parser intentionally supports a restricted FSP subset; unsupported models are outside this oracle's scope. The separate paper-witness command uses only the Python standard library and transcribes the finite definitions in the paper; it checks nine cases, the fixed-head obstruction, and the Production Cell census and 13-state/11-edge policy. Choose fresh output directories to preserve prior results.

## Source distribution and dependency acquisition

The complete tool source tree is distributed directly; no source overlay is needed. All JARs are omitted from the prepared source tree and ignored by its `.gitignore`. The frozen shaded solver contains FFmpeg natives marked `nonfree and unredistributable` and is not publicly distributed, including as a Release asset. Its SHA-256 below identifies the measured binary. Reproduction uses the included sources and the clean-cache build procedure below. Publication and verification status are recorded below. The campaign binary is unchanged.

| Frozen file | Bytes | SHA-256 |
|---|---:|---|
| `mtsa-1.0-SNAPSHOT.jar` | 698961879 | `fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07` |
| `synoptic-1.0.jar` | 109442641 | `21d8611a1f07ae744b436f7e7228d2233896f79b3568a42c96f2886f2eb59f69` |

For existing authorized local use, import an exact solver copy without modifying the source copy:

```sh
python fetch_assets.py --asset mtsa --source-file /path/to/mtsa-1.0-SNAPSHOT.jar
python fetch_assets.py --asset mtsa --verify-only
```

For a source build, obtain the exact local dependencies directly from the official MTSA tree. Synoptic is available at the [official MTSA upstream file](https://git.exactas.uba.ar/lafhis/mtsa/-/raw/master/maven-root/mtsa/lib/synoptic/synoptic/1.0/synoptic-1.0.jar), under its upstream terms:

```sh
python fetch_assets.py --asset dependencies
python fetch_assets.py --asset dependencies --verify-only
```

This first restores the hashed file-repository metadata from `dependency-metadata/`, then verifies local dependency objects against fixed sizes/SHA-256 values and installs them at their original paths. The published repository contains no `lib/` directory; the acquisition step creates the needed local build layout. URLs are pinned to official upstream commit `d10ba71f092dc9645a80d2752bd089691f158156`. The 109 MB WESSBAS/Synoptic-derived object goes to the POM file-repository path and `locallib/synoptic.jar`; the two different SceneBeans objects remain separate. A local `--source-file` is also accepted. The script rejects a different existing binary and incomplete or mismatching downloads. Obtaining a file from upstream does not establish a right to redistribute it; the package omits all third-party JARs. `fetch_assets.py` has no Release retrieval route. A slim CLI binary is optional work after the v2 freeze, outside the v1 artifact requirements.

## Re-run correctness/capability checks

Use a 64-bit JDK 17 and Python 3.10+. After acquiring dependencies, build the included sources in a separate package copy. The source build and focused tests are:

```sh
mvn -B -f "Implementation/Source Code/maven-root/mtsa/pom.xml" package -DskipTests -Djacoco.skip=true
mvn -B -f "Implementation/Source Code/maven-root/mtsa/pom.xml" test -Dtest=ltsa.updatingControllers.otf.ActivationSpecTest,ltsa.updatingControllers.otf.FineGrainedOtfDucsTest,ltsa.updatingControllers.otf.OtfDucsSynthesizerTest,ltsa.updatingControllers.otf.QuiescentUpdateBoundaryTest -Dfork.number=0 -Dthread.count=1 -Dparallel=none -DfailIfNoTests=true -Djacoco.skip=true
```

The build requires JDK 17, Maven, Python 3.10+ for the acquisition script, and network access to Central and FreeHEP. Run the acquisition step before building to reconstruct the complete `mtsa/lib` file repository next to `pom.xml`. Generated `lib/` directories and JARs are ignored by Git. The distribution POM adds Central immediately before FreeHEP, without changing dependency coordinates or Java sources. Build in a separate package copy so its new `target/` does not replace the frozen campaign binary.

A real clean-cache check ran on macOS arm64 with **OpenJDK 17.0.19 and Maven 3.9.16**. Starting from a new empty local Maven repository, `package` succeeded with exit 0 in **198.503 seconds** (about 3 min 19 s); 272 resolved dependency JARs were valid ZIP files. Tests were compiled but their execution was skipped. The initial original-POM attempt was stopped after **162.624 seconds** because FreeHEP was repeatedly queried before Central; this was an unfinished dependency-resolution attempt, not a compilation failure. Both attempts and their POMs are preserved in `validation/build/`; distribution copies redact personal filesystem prefixes only. The successful attempt used another new empty repository and only the repository-order change above. Elapsed times are observations of this host/network, not an expected upper bound. Source reconstruction succeeding does not resolve redistribution restrictions on the generated shaded JAR.

From a separate package copy, after acquiring the local dependencies, the checked command is:

```sh
# Use an unused absolute directory; it must initially be empty.
mvn -B -f "Implementation/Source Code/maven-root/mtsa/pom.xml" \
  -Dmaven.repo.local=/absolute/path/to/new-empty-maven-repository \
  package -DskipTests -Djacoco.skip=true
```

The `validation/build/` logs record the actual execution timestamps (2026-09-15 JST); the requested work-day label is 2026-09-16. No new timing measurement was substituted for the initial attempt. The distributed Java sources are byte-identical to the measured tool's sources; the distribution-only POM repository ordering does not change dependency coordinates. The exact runtime binary remains identified by the SHA-256 above. The checked rebuild was not byte-identical to that JAR, but was built from the same Java sources. The package also includes all 841 original `src/test/resources` files, restored after this timed check; the recorded package check compiled tests but did not execute them.

After building, run validation with a fresh output location and explicitly select the JDK if the default `java` differs:

```sh
python reproduce_validation.py rq1 --java java --output replication/rq1
python reproduce_validation.py rq2 --java java --output replication/rq2
```

These commands use the original cases, method properties, heap limits and per-job timeouts. RQ1 originally used a 12 GiB heap; ensure sufficient RAM. The original runs remain untouched. A resource failure remains a resource failure. Alternatively, existing local users can import the exact frozen JAR using the earlier `--source-file` command. The optional binary check in `check_package.py` verifies that frozen hash; run its saved-evidence check before building when using the source-rebuild route.

## Xeon campaign and figure/table generation

The campaign README and archived configurations describe the dedicated Windows Xeon W-2265 / 256 GB protocol: one JVM at a time, 64 GiB heap, 1,200 s timeout. Stage 1 covers 135 RQ3 cells. First-stage TO/OOM cells are not repeated; completed cells receive four additional runs. Only five valid, decision-consistent completions receive median/min-max summaries. Legacy denotes this fork's GR synthesis path on the same fine-grained inputs. It has no preverified new-controller handover requirement. The monolithic aligned-entry checks below compare it with a lab-maintained build of the original DUCS source. Direct-Full is the same-game comparator.

RQ3 records FG lazy 25 WIN, one LOSS and one TO; Direct-Full 14 WIN and 13 TO, including the marked pre-authorized Workflow/R2 replacement; Legacy nine WIN, 13 OOM and five N/M (capture cap). The latter are unmeasured: author-side M9MtsSnapshot capture instrumentation stops before synthesis at its fixed 250,000-state limit. These cells give no evidence of Legacy capability or solver failure. The raw process status remains CRASH; only the renderer's display annotation changes after checking the saved exception. The 14 FG/Direct-Full and nine FG/Legacy completed decisions agree. Independent RQ4 completes all 76 cells with five repetitions. Controlled RQ4 retains all 132 single-run jobs, with 31 WIN and two LOSS per method; no timing medians are reported for this panel.

The single Mac Industry/R1 diagnostic passes the separate exhaustive checker (110,992 states). The goal-terminal export has 110,825 states; `FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/industry-r1-independent/analyze_graph.py` reconstructs the fixed point, checks losing closure, and records 42 losing entries among 131 roots. Its four-state DSD1 rejection cycle occurs after all update commands; command preemption alone leaves that cycle intact. These are correctness observations only. The original CSV postprocessing error and subsequent collection-only repair are preserved; the JVM was not rerun.

`FSE2027_SUBMISSION_20260914/experiments/industry_r1_contract_variant/` contains one separately tested contract variant: the same existing `validateGF1` event is exempted from all three R1 bans, with every other input line unchanged. One frozen-JAR Mac run wins at all 131 original roots, with certificate, Link and separate exhaustive checks; the included Python analysis checks a rank certificate and all three UC validation responses. This assumes validation is acceptable during the update interval. The exact input diff and both the original LOSS and variant WIN are retained. It supplies no timing comparison and is excluded from the 27-case campaign. To repeat only its saved-graph checks, use `python FSE2027_SUBMISSION_20260914/experiments/industry_r1_contract_variant/check_variant.py`. The separate `run_variant.py` records the Mac launch procedure and requires the exact locally held frozen JAR; it refuses to overwrite existing raw evidence and rejects a different binary hash. A source rebuild has a different hash and requires a separately identified replication, not substitution for this recorded run.

`FSE2027_SUBMISSION_20260914/experiments/industry_r1_legacy_monolithic_check/` contains two supplied monolithic cross-check logs, the original model and its two-line `T` to `T_Empty` selection change, and `check_legacy_product.py`. The original-source lab-build log returns a 2,312-state controller; the initial fork log returns no controller. A static reconstruction matches both meta products (14,763/99,676 versus 33,093/257,314 states/transitions) and the final safety-state counts (3,134 versus 15,177). The fork's `hotSwapIn` entry label leaves the model's `beginUpdate` fluent reset unsynchronized, introducing an uncontrollable self-loop that defeats GR progress. Run the Python script to check this specific model reconstruction and the spoiling loop without a JVM or experiment rerun. The source comparison uses official upstream commit `d10ba71f092dc9645a80d2752bd089691f158156`; the supplied reference JAR is now identified as the lab-maintained build of source commit `e1bf040b83e36b36308bce22e280133682986250`, SHA-256 `4ab198ba14c9f0f829c36808025aefc063e2a3a0836679490179cc407e6133e5`. Official publication-release identity, GUI host/date and final published benchmark identity remain unconfirmed. Neither cross-check is a performance measurement or a new cell in the 27-instance campaign. FG Industry/R1's 42 losing entries reject its all-entry, verified-endpoint, quiescent-handover contract; the monolithic result is evidence against generalizing this to R1 itself.

Travel retains 48 instances under each of four methods: lazy/eager/update-first each have 20 complete cells, 26 TO and two OOM; Direct-Full has 18, 28 and two. Of 960 planned repetition slots, 504 are actual trials and 456 explicit failure skips. All 18 completed lazy/Direct-Full pairs give 3.4–46.2% state ratios and 1.49–34.21 median-time ratios (median 3.93). All methods are unresolved at N=4/K≥8 and every tested N≥6. Hub completes 90 instances × four methods × five repetitions, with agreeing decisions; paired Direct-Full/lazy median-time ratios are 5.35–118.38 (median 78.11). The generated tables and figures retain every cell and explicit TO/OOM markers.

`FSE2027_SUBMISSION_20260914/experiments/legacy_fidelity/` retains generated monolithic inputs/diffs, a separate headless Java adapter, orchestration source under `bundle_delta/`, and Mac validation evidence. Aligning the three Industry fluent declarations yields the same T_Empty controller (2,312 states, 6,615 transitions) in the fork and reference build; supplied T also agrees (3,050/9,496). Two initial adapter failures are retained alongside the corrected runs. These are decision checks, never Xeon performance measurements or RQ3 cells. The returned 21-condition-per-tool Xeon comparison records 21 lab-build controllers and 16 fork controllers, with five fork inputs unmeasured before a legacy GR decision (three parser-name conflicts, two author-side instrumentation exceptions). First-trial sizes match in 15 conditions; Railcab supplied differs by five states, but four tool/condition cells vary in size across repetitions. S4 and the module README retain every variable size and the confirmed source causes; the cause of size variation and controller equivalence remain unresolved. The separate comparison is not mixed into the main RQ3 table. The public package excludes the private delta ZIP, its lib/ directory and every adapter/solver JAR. Preparation scripts require privately available tool JARs and the original-source resource tree; they do not fetch or redistribute the reference shaded JAR.

`run-supplement.ps1` and `RQ3_SUPPLEMENT_README_JA.md` document the separately authorized follow-up campaigns, now returned. Workflow/R2 Direct-Full timed out at the same 1,200 s cap; the main cell is TO‡ and S4 retains the original operational interruption. The PC Arms=2/R2 single 3,600 s trial also timed out (67.1 GiB sampled peak process RSS under a 64 GiB heap cap), leaving its original 1,200 s TO unchanged. RSS includes non-heap memory and does not measure heap saturation. The generated provenance table records both originals and follow-ups, with explicit skipped repetitions and no follow-up median.

The Windows drivers are also present at this package root. `powershell -NoProfile -ExecutionPolicy Bypass -File .\run-all.ps1` uses that self-contained layout and writes `raw/`. The nested campaign directory retains the paper's source layout for rendering and returned-data integration. Restore the result assets first (command and hashes at the end of this README), then regenerate from this package root:

```sh
python -m pip install -r FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/plot-requirements.txt
python FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/scripts/check_render_results.py
python FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/scripts/render_results.py --mode xeon --input-root FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw --output FSE2027_SUBMISSION_20260914/paper/build/generated
python FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/scripts/analyze_results.py --input-root FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw --output FSE2027_SUBMISSION_20260914/paper/build/generated
cd FSE2027_SUBMISSION_20260914/paper
latexmk -pdf -outdir=build main.tex
latexmk -pdf -outdir=build supplement.tex
```

The main RQ3 table retains all 135 cells in one-line form. A dagger marks a range wider than 10% of the median; the complete min–max values stay in Supplement S4. `rq4-scaling-combined.pdf` combines states, time and a 48-setting × four-method Travel status grid. The full panels remain in `rq4-states-vs-k-full.pdf` and `rq4-time-vs-k-full.pdf`. The supplementary provenance table validates the separately included `experiments/rq3_supplement/configs/` definitions against the returned trials; it retains the original TO/INTERRUPTED records while applying the authorized Workflow display replacement. Legacy-fidelity results have separate S4 outcome, per-repetition size and reference-resource tables and never become RQ3 cells. Run `python3 FSE2027_SUBMISSION_20260914/experiments/legacy_fidelity/render_fidelity.py` and `check_returned_fidelity.py` to regenerate/check them. The separately retained locally generated and Xeon-produced comparison CSVs agree byte for byte. The successful final run-all transcript and both full per-campaign returns are present.

The complete Production Cell witness is Figure 1, the two smaller witnesses are Figure 2, and the scaling figure is Figure 3; the RQ3 and related-work tables are Tables 3 and 4. TikZ sources are included under `paper/figures/`. To check the actual drawn transitions, transfers, endpoint edges and policy against the finite witness implementation and the explicitly scoped RQ2 fixture correspondence, run `python FSE2027_SUBMISSION_20260914/experiments/paper_witnesses/check_diagrams.py`. The paper cell adds inspection and lifecycle monitors to the RQ2 plant projection; equality is not asserted for the full games. Complete smaller-witness parameters are in S1.4, eligibility checks in S2.1, and residual-history definitions in S3.1. The main paper uses neutral boundary names `entry` and `load`, corresponding to Java `hotSwapIn` and `hotSwapOut`.

Rendering uses Matplotlib; PDF builds use XeLaTeX, acmart and xeCJK. Travel/hub and both RQ3 supplementary measurements are included; every Xeon campaign has returned. The analyzer emits paired per-instance comparisons, controlled-family structural CSV/LaTeX and aggregate statistics. Raw summaries are never rewritten; Mac pilot/diagnostic timings never substitute for Xeon measurements.

Oversized `metrics_long.csv` distribution copies are losslessly stored as `metrics_long.csv.gz` inside the result assets. Summaries, per-run evidence and the paper renderer need no decompression. Run this Python snippet from the package root to restore these CSVs without overwriting existing files:

```python
import gzip
import shutil
from pathlib import Path
for path in Path('.').rglob('*.csv.gz'):
    with gzip.open(path, 'rb') as source, path.with_suffix('').open('xb') as target:
        shutil.copyfileobj(source, target)
```

The assembler verifies decompressed bytes before replacing a distribution copy, and the anonymity scan reads compressed CSV contents too. Original returned raw and the local experiment bundle retain their uncompressed bytes.

## Scope, privacy, and AI use

Certificates validate search results relative to shared parsing, monitor, transfer, Post and goal code. The separate explicit checker shares the frontend and goal logic; the raw-LTS oracle parses independently but covers only its supported subset. All were maintained by the same author team. Residual soundness outside the documented A/E certifications and A1-A4 runtime conformance remain external premises; the output is a finite policy/rank/handover table for a conforming execution platform.

Generative AI assisted research design, implementation/tests, experiment scripting/execution, analysis and writing. Saved executable outputs supply numerical evidence. Model extraction and source/publication claims require explicit checks described in the paper.

Distribution copies replace personal filesystem prefixes with package-relative paths or `<USER_HOME>`. Decisions, measurements, seeds, timestamps, model bytes and JAR bytes are preserved. Original local logs remain retained. Saved log-file digests describe the pre-redaction source files; they are not checksum claims about redacted distribution copies. Bibliographic author names in third-person citations and upstream attribution are not submission-author metadata. This package contains neither private author facts nor downloaded third-party papers.

The source package is published at the anonymous repository cited by the paper. LICENSE covers only the stated original contributions; NOTICE records confirmed MTSA-derived source redistribution permission, the upstream license investigation, and separate third-party terms. The shaded solver and third-party JARs remain excluded from public distribution.


For AD provenance, original environment bytes are checked before distribution. Anonymous copies redact the Python user-home path and annotate `environment*.json` with `distribution_redaction` (original SHA-256, changed field names, and personal-path-only scope). Run metadata retain the original fingerprint. The public renderer checks that explicit relationship and stable host/runtime facts; it does not claim byte equality between redacted and original environments. Trial statuses, measurements, inputs, JAR identities and configs are unchanged. Full Maven-source dependency metadata remain part of the source tree; the private legacy-fidelity `lib/` tree is excluded entirely.

## v2 evidence map

All paths below are relative to `FSE2027_SUBMISSION_20260914/` unless a full prefix is shown. Generated numerical text is under `paper/build/generated/`. Restore release data before commands that inspect per-run records. These mappings identify evidence, not a substitute for the mathematical proofs.

| Paper claim / display | Supplement | Inputs, configuration, and reproducible output |
|---|---|---|
| Figure 1; Theorem 3.4 (fine/bulk) | S1.1 | `experiments/paper_witnesses/check_witnesses.py`, `check_diagrams.py`; `paper/figures/witness_cell.tex`; finite-closure and policy JSON output |
| Figure 2; Proposition 3.5 (fixed heads / boundary block) | S1.2–S1.4 | Same witness checkers; `Implementation/Experiment/FSE2027/rq2-formal-witness/models/`; `paper/figures/witness_other.tex` |
| Algorithm 1; Lemmas 4.1/4.2, Theorem 4.3, Corollary 4.4 | S2.2–S2.4, S3 | `ltsa.updatingControllers.otf` source and tests; RQ1/RQ2 oracle and certificate/Link records; source paths above |
| Lemma 4.5 (containment), Theorem 4.6 (K+1 versus 2^K) | S2.7 | `experiments/rq3_xeon/configs/rq4_independent.json`, `inputs/`, `raw/rq4_independent/`; `rq4-points.csv` |
| Theorem 5.1 (conditional trace lifting) | S3 | Proof and A1–A4 correspondence; abstract Link checks in RQ1/RQ2. No runtime-platform validation is claimed |
| H/A/E initialization lemmas and checks | S3.1; S4 coverage table | `experiments/rs_coverage/` saved monitor exports, strict H and one-shot A/E checks, appended CSV columns and witnesses; `rs-*.tex` generated coverage |
| Table 1 (RQ1) | S4 validation | `experiments/semantic_revision_20260914/rq1/`, `oracle/`, `rederive_oracle.py`; 92 saved jobs |
| Table 2 (RQ2) | S1, S4 validation | `experiments/semantic_revision_20260914/rq2/`, `derive_rq2_expectations.py`; 14 saved jobs |
| Table 3 (135 RQ3 cells) | S4 full ranges, elapsed/censoring, provenance | `experiments/rq3_xeon/configs/rq3.json` and both `rq3_supplement_*` returned directories; `rq3-table.tex`, `rq3-supplement.tex`, `rq3-cells.csv`, `rq3-censored-comparisons.csv`, `rq3-supplementary-provenance.csv` |
| Figure 3 (RQ4) | S4 complete panels | Same campaign tree: `rq4_independent`, `rq4_controlled`, `rq4_travel`, `rq4_hub`; `rq4-scaling-combined.pdf`, complete-panel PDFs, `rq4-travel-status-grid.csv` |
| Contract feature coverage | S4 | `experiments/rs_coverage/contract-coverage.csv`, original LTS declarations and archived frontend census; generated table |
| Legacy reference experiment (separate from Table 3) | S4 | `experiments/legacy_fidelity/inputs/`, input diffs, `raw/xeon/`, `render_fidelity.py`; `legacy-fidelity-reference.csv`, generated resources and size-variation tables |
| Table 4 (related-work contracts) | S5 | Cited primary DOI/URLs in `paper/references.bib`; source-level contract locations in S5 |

The RQ3/Travel time ratio is for the solver plus internal certificate-check interval, excluding frontend/endpoint preparation and later Link construction/checking. Hub uses solve-only time and Legacy its native timer. S4 reports total JVM elapsed medians and ranges separately. A 1,200-second JVM timeout supplies a lower bound only for the censored *total attempt* relative to FG's elapsed median; the cap divided by solver time is recorded as a descriptive quotient, not a solver-speedup bound. One censored attempt is never promoted to a five-trial Direct-Full median. Sampled working-set RSS may miss peaks.

## Publication and independent clone status

The publication location is https://github.com/research-artifact-archive/research-artifact. The repository is reinitialized for this FG-DUCS package, replacing its previous content; the `main` branch history contains only this package's publication commits. The final submission tag `fse27-submission` will be created at the final push after v2 is frozen. Until then, `main` is the working preview and the two split result assets are designated for the `v2-preview` pre-release. Release creation and asset upload are pending; the manifest and asset digests are already included. No final-submission tag exists yet.

The public preview was independently cloned over HTTPS and verified on macOS arm64 with OpenJDK 17.0.19 and Maven 3.9.16. From a new empty Maven cache, the source build succeeded in **643.205 seconds**; this includes a slow FreeHEP dependency transfer. Upstream dependency acquisition and digest verification took **89.486 seconds** separately. Tests were compiled but execution was skipped. Saved-package checks passed for all **92 RQ1 and 14 RQ2 jobs**. The `--derive-only` smoke runs succeeded and matched all derived fields of the **46 RQ1 oracle rows and 14 RQ2 expectation rows**, after normalizing clone paths. These derive runs do not rerun synthesis or regenerate the saved RQ2 prose annotations. Logs and timings are in `validation/clean-clone/`; the earlier 198.503-second local build remains separate evidence. Clone the current preview as follows; use `git checkout fse27-submission` only after the final tag has been published:

```sh
git clone https://github.com/research-artifact-archive/research-artifact.git fg-ducs-clean
cd fg-ducs-clean
python check_package.py
python fetch_assets.py --asset dependencies
mvn -B -f "Implementation/Source Code/maven-root/mtsa/pom.xml" -Dmaven.repo.local=/absolute/path/to/new-empty-cache package -DskipTests -Djacoco.skip=true
python reproduce_validation.py rq1 --derive-only --output replication/clean-rq1
python reproduce_validation.py rq2 --derive-only --output replication/clean-rq2
```

After the preview Release is available, download both `fgducs-results.tar.gz.part001` and `fgducs-results.tar.gz.part002` from https://github.com/research-artifact-archive/research-artifact/releases/tag/v2-preview into the same directory, then run:

```sh
python restore_results.py --assets /path/to/downloaded-assets --verify-only
python restore_results.py --assets /path/to/downloaded-assets
```

The restore script verifies both asset and per-file digests. Public Release download and restoration have not been checked because the `v2-preview` Release is not yet published; local asset restoration checks below remain separate evidence. Source models, the measured JAR and original raw remain unchanged.


## Source extent and local package checks

The Maven Java sources and test resources are retained byte for byte. The optional
`src/main/SPECTRATranslator` Eclipse sources and `src/test/benchmarks` are included
as inherited supplementary material; they are outside the recorded Maven build.
Their existing LICENSE files and legal headers remain intact (see NOTICE for
the separate JavaBDD notices). Native/binary generated outputs and one
contact-only benchmark note are omitted. File-repository metadata are stored
under `dependency-metadata/`; `fetch_assets.py` restores their exact original
paths before obtaining dependency binaries. The public tree itself has no `lib/`. Two optional SPECTRA Java files whose package directory is named `lib` are likewise retained in this mapped store and restored byte for byte; the mapping lists their original paths.

Local v2 packaging checks restored all split assets into a separate directory,
verified every archived file digest, checked saved RQ1/RQ2 certificates, and
regenerated the paper tables from the restored raw. The dependency-metadata
restoration was checked for exact bytes, repeatability, and refusal to replace
a differing existing file. These checks run on saved data and package copies;
they are not new synthesis trials. The later public clean-clone check is recorded separately above.
The anonymity scan distinguishes required third-party legal attribution from
submission-author identity; both original JavaBDD copyright/contact lines are
retained. No submission-author identifying matches remain.


## Residual interpretations (AG diagnostics and AH certification)

The strict history-inclusive check H remains 0/273, with all historical columns and witnesses preserved. Under activation-safe A, the language and frontend-rule checks establish RS inclusion for **all 138 NEW initializations**. Equality additionally requires a nonempty actual safe-history set; its plant-level nonemptiness is not established. An empty safe-history intersection is universal, so inclusion still holds. This interpretation does not claim safety of past violating histories.

Under entry-scoped E, **89/135 UPD initializations are exact by Lemma E-prime**. The checker reads the expanded definitions of all referenced fluents: each must be a declared fluent whose initiating/terminating labels are recognized update commands, which cannot occur before entry. Their entry values therefore equal their declared initial values. The constant initializer must match the non-error boundary obtained from monitor state zero after one `hotSwapIn`.

The remaining **46/135** reference implicit action fluents (`event_predicate`) and remain unverified; their values can depend on pre-entry plant history, and the corresponding reference languages are not established by the saved DFA. No additional cases were excluded by declared plant-fluent labels. Compiled-reset self-consistency and observer synchronization remain diagnostics, not certificates or language counterexamples.

The added `rs_E_ah_exact` and evidence columns hold the current E-prime classification; the old `rs_E_exact` and `e_*` columns retain the historical AG result. S3/S4 and the module README explain the checks, one-shot constraints, witnesses and generated counts. All prior columns, input exports and campaign evidence are preserved; no synthesis campaign was rerun. Claude's confirmed model and research roles are recorded in Methods; the remaining author fact checks stay explicitly marked in the manuscript.

## Key distribution identities

| File | SHA-256 |
|---|---|
| `paper/main.pdf` | `96cf3a1f12d45b6e631f6172d8bc7ab94256effbc16621aa60f9dfbfaa9ba6b0` |
| `paper/supplement.pdf` | `190720cb90532ba2e92f9d13408909cd69afde2e0e8629be95b12bcfbe2e0974` |
| `fetch_assets.py` | `5dff4b083c15ee7de348625d1da8cf0ae325453c1dfa39b7956f7e07fb3225d5` |
| `restore_results.py` | `283066e8512101a6f41cf2e1bad5311f3e1cf90cb0eb77c607113f6964cdbfcd` |
| `result-assets.json` | `97bc32f4f2f611e44927d72b55550046603184e5ea15775d1d4abc450de86fa7` |
| `FSE2027_SUBMISSION_20260914/experiments/rs_coverage/summary.csv` | `a3de15da4fc92884d1f3a0095b7781390449c78cfe54ab93f360a605751d0f4d` |
| `FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/scripts/render_results.py` | `20627c81821d59523152e8de84f7a2b7122ac691daded3bfe0fb461da9dcc6ad` |
| `Implementation/Source Code/maven-root/mtsa/pom.xml` | `3fdc4272800b699fc4fa3e6916321d5d4a17302f22a5941f2c23fabf97a68e54` |

## Result release assets

The repository keeps RQ1/RQ2 saved evidence, source, models, configs and generated paper outputs. Complete RQ3/RQ4, legacy-reference and Industry-variant raw are in the parts below. Download **every part**, preserve its name, and run the restoration command; the parts form one gzip/tar stream. The script checks every part and file and refuses to replace different existing data.

```sh
python restore_results.py --assets /path/to/downloaded-assets --verify-only
python restore_results.py --assets /path/to/downloaded-assets
```

| Asset | Bytes | SHA-256 |
|---|---:|---|
| `fgducs-results.tar.gz.part001` | 90000000 | `7b471f6ae6e13c9a25c44f32e0f132493e4398434624be85c9a3009e63a3c691` |
| `fgducs-results.tar.gz.part002` | 2850581 | `bc5565f3a84129beb685654380fbf3c526bdce52ef3389f74748400e9e0f58fd` |

`result-assets.json` lists every archived path, size and digest. No solver/dependency JAR, lib/ tree, private decisions or private runbook is included.

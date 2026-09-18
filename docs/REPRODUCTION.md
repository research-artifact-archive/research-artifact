# Reproduction commands and verification

Run commands from the package root unless stated otherwise. Use fresh output directories.

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

For existing pre-specified local use, import an exact solver copy without modifying the source copy:

```sh
python fetch_assets.py --asset mtsa --source-file /path/to/mtsa-1.0-SNAPSHOT.jar
python fetch_assets.py --asset mtsa --verify-only
```

For a source build, obtain the exact local dependencies directly from the official MTSA tree. Synoptic is available at the [official MTSA upstream file](https://git.exactas.uba.ar/lafhis/mtsa/-/raw/master/maven-root/mtsa/lib/synoptic/synoptic/1.0/synoptic-1.0.jar), under its upstream terms:

```sh
python fetch_assets.py --asset dependencies
python fetch_assets.py --asset dependencies --verify-only
```

This first restores the hashed file-repository metadata from `dependency-metadata/`, then verifies local dependency objects against fixed sizes/SHA-256 values and installs them at their original paths. The published repository contains no `lib/` directory; the acquisition step creates the needed local build layout. URLs are pinned to official upstream commit `d10ba71f092dc9645a80d2752bd089691f158156`. The 109 MB WESSBAS/Synoptic-derived object goes to the POM file-repository path and `locallib/synoptic.jar`; the two different SceneBeans objects remain separate. A local `--source-file` is also accepted. The script rejects a different existing binary and incomplete or mismatching downloads. Obtaining a file from upstream does not establish a right to redistribute it; the package omits all third-party JARs. `fetch_assets.py` has no Release retrieval route. A slim CLI binary is not distributed: redistribution conditions for all nested dependencies have not been established.

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

The `validation/build/` logs retain their actual execution timestamps. No new timing measurement was substituted for the initial attempt. The distributed Java sources are byte-identical to the measured tool's sources; the distribution-only POM repository ordering does not change dependency coordinates. The exact runtime binary remains identified by the SHA-256 above. The checked rebuild was not byte-identical to that JAR, but was built from the same Java sources. The package also includes all 841 original `src/test/resources` files, restored after this timed check; the recorded package check compiled tests but did not execute them.

After building, run validation with a fresh output location and explicitly select the JDK if the default `java` differs:

```sh
python reproduce_validation.py rq1 --java java --output replication/rq1
python reproduce_validation.py rq2 --java java --output replication/rq2
```

These commands use the original cases, method properties, heap limits and per-job timeouts. RQ1 originally used a 12 GiB heap; ensure sufficient RAM. The original runs remain untouched. A resource failure remains a resource failure. Alternatively, existing local users can import the exact frozen JAR using the earlier `--source-file` command. The optional binary check in `check_package.py` verifies that frozen hash; run its saved-evidence check before building when using the source-rebuild route.

## Publication and independent clone status

The publication location is https://github.com/research-artifact-archive/research-artifact. The repository is reinitialized for this FG-DUCS package, replacing its previous content; the `main` branch history contains only this package's publication commits. The final submission tag `fse27-submission` will be created at the final push after the submission freeze. Until then, `main` is the working preview and the two split result assets are designated for the `v2-preview` pre-release. Release creation and asset upload are pending; the manifest and asset digests are already included. No final-submission tag exists yet.

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

Local packaging checks restored all split assets into a separate directory,
verified every archived file digest, checked saved RQ1/RQ2 certificates, and
regenerated the paper tables from the restored raw. The dependency-metadata
restoration was checked for exact bytes, repeatability, and refusal to replace
a differing existing file. These checks run on saved data and package copies;
they are not new synthesis trials. The later public clean-clone check is recorded separately above.
The anonymity scan distinguishes required third-party legal attribution from
submission-author identity; both original JavaBDD copyright/contact lines are
retained. No submission-author identifying matches remain.


## Quick-start and layout verification

The Python-only run took **2.711 seconds** on the checked macOS host: eight PASS,
with contract-variant and measurement regeneration explicitly SKIP because the raw assets were not restored.
A separate copy with every result asset restored and Matplotlib available took **22.978 seconds**, with **10/10 PASS**.
It reproduced all 135 RQ3 cells, the saved decision/status counts, paired ratios and all family statistics.
All 22,834 files in that restored input copy retained their original bytes, with no added or removed input files.
These elapsed values measure the reproduction checks, not synthesis performance.
The reports are `validation/quickstart/core.md` and `validation/quickstart/restored.md`.

The safety tests check output refusal, independent copies, corrupted evidence, absent assets and failure reporting:

```sh
python test_quickstart.py
```

All seven tests passed. Reusing an existing output directory returned exit code 2 and preserved its contents.
The portable PowerShell drivers passed parser checks under PowerShell 7.6.6 on macOS;
this validates syntax, not Windows execution. Every campaign config passed Python plan generation,
including the 135-cell RQ3 stage and the supplementary 5-slot/1-slot plans, without launching Java.
All config/model/runtime copies used by the portable layout match their source bytes.
The original Windows runtime/probe transcripts remain the execution evidence for the measured campaigns.

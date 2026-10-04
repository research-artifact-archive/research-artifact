# Packaging, provenance and scope

## Documents and supporting material

The [main paper](../paper/main.pdf) has 18 body pages and 21 total pages. The [integrated supplement](../paper/supplementary_material.pdf) has 87 pages, covering Technical Appendix A–R and Supplement S1–S5. The [document index](../paper/README.md) gives direct section links.

[The reading bundle](../paper/reading_bundle.zip) contains the main and integrated PDFs with relative cross-document links. [The manuscript source ZIP](../paper/manuscript_source.zip) contains the same files as the browsable [source directory](../paper/source/), including copied analysis inputs and build instructions.

The three saved-evidence analyses are available under `paper/source/evidence/` with copied inputs, scripts, outputs and negative controls. A public-root checker binds the copied inputs back to the full archive and recomputes the analyses. They add no synthesis or performance measurements. The [analysis index](../results/additional-analyses/README.md) describes their scope.

## Retained scientific records

The public tree is grouped by purpose. `reproduce/layout.json` is a technical restoration manifest: it maps public paths to the historical relative paths used by research programs, and records byte sizes and SHA-256 digests. The materializer verifies those files in a fresh directory. It is not a claim of external certification.

All main fixed-budget raw observations, available policies, extended-budget ext1–7 results, E1/E2/E4/E5/E6 scientific models, scripts, raw trials and serialized finite certificates are included. Large baseline logs, legacy-fidelity raw data and the separate contract-repair raw data are losslessly archived under `results/archives/`; ext1–7 and finite families remain directly browsable. The archives are regular Git files below 100 MB each, not external release downloads. Two very large CSVs were already losslessly gzip-compressed in the distribution; the materializer also restores their CSV form.

Original line endings are retained; `.gitattributes` disables automatic text conversion so Windows checkout does not change scientific hashes. Whitespace in archived observations and model comments is not normalized.

No timeout, OOM, LOSS, invalid input, unfavourable ordering, unfinished trial, discarded checker attempt or corrected-model predecessor is changed into a favourable observation. The E4 original input errors and corrected series are both retained. E6 version/control denominators remain separate. Supplementary reruns do not replace the fixed table or its medians.

Only distribution copies of identifying absolute paths and workstation metadata are anonymized. Scientific input/result/certificate bytes in the prior anonymous E6 export remain unchanged. Some original metadata hashes point to pre-anonymization invocation or environment files; 439 such references are explicitly classified by the extension checker as historical references, not asserted to identify the anonymized current bytes. Public-file integrity and the scientific input/certificate relationships are checked separately. Bibliographic citations and upstream legal notices remain in third person, including the third-party Kitsune manuscript at the University of Maryland; those URLs do not identify the submission authors.

Excluded material consists of private author/project instructions and editorial coordination notes, full private Git histories, compiled build caches, and redistributable-rights-unresolved solver/dependency binaries. Complete baseline source plus three experimental patches reconstruct the measured source variants. Dependencies are fetched directly from recorded upstream sources with hash checks. A local source build receives its own identity and is not claimed byte-identical to a measured JAR.

Older scientific design/protocol notes are retained as historical context where they explain counterexamples or frozen experiment plans. Pre-run statements such as NOT_RUN in an original protocol are not the final campaign status; the current README and saved raw indexes provide the final observations. The private submission workflow and candidate-review material are not required to use or check this package.

Screenshots in `docs/images/` are browser captures of the local result viewer, fed by actual fresh Rolling runs of the public E1 source build. They show the resulting policy or losing evidence, not simulated measurements. The screenshot runs are functional checks and are not included in any paper aggregate.

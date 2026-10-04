# Synthesizing Staged Updates between Verified Controllers

This anonymous replication package was prepared by the paper's authors for **FG-DUCS**. The selected manuscript is **C145 (4 October 2026)**: 18 pages of main text, 21 pages including references, and an 87-page integrated supplement.

FG-DUCS generates an update game from local component transfers and individual requirement lifetimes between fixed, verified endpoint controllers. Its second contribution identifies when a winning batch policy can be expanded into individual commands while preserving completion and the selected endpoint.

## Read or download

| Document | Read | Download |
|---|---|---|
| **Main paper** | [Main PDF](paper/main.pdf) | [Download PDF](https://raw.githubusercontent.com/research-artifact-archive/research-artifact/fgducs-c145-20261004/paper/main.pdf) |
| **Proofs and experimental detail** | [Integrated supplement: Technical Appendix A–R and S1–S5](paper/supplementary_material.pdf) | [Download PDF](https://raw.githubusercontent.com/research-artifact-archive/research-artifact/fgducs-c145-20261004/paper/supplementary_material.pdf) |
| **Both PDFs together** | Includes matching files with working relative document links | [Download reading bundle](https://raw.githubusercontent.com/research-artifact-archive/research-artifact/fgducs-c145-20261004/paper/reading_bundle.zip) |
| **Manuscript and added analyses** | [Browse source](paper/source/) | [Download manuscript source ZIP](https://raw.githubusercontent.com/research-artifact-archive/research-artifact/fgducs-c145-20261004/paper/manuscript_source.zip) |

**Start with the paper and integrated supplement.** No installation is needed to read the proofs, inspect the tables or browse the saved results. The supplement opens with linked reading routes and a complete contents list. Its PDF bookmarks and continuous page numbers cover both parts.

## Find the evidence for a claim

The page numbers below refer to the **C145 PDFs**. For every appendix section, use the [complete document index](paper/README.md#appendix-section-index). For exact files, commands and limitations, use the [claim-to-evidence map](docs/CLAIMS.md).

| Question | Main paper | Supplement and evidence |
|---|---|---|
| What is supplied, generated and guaranteed? | [§§2–4; Table 1 and Table 2](paper/main.pdf#page=3) | [TA A–C, pp.3–11](paper/supplementary_material.pdf#page=3): correspondence, synthesis and complete Cell/Policy inputs |
| When does changing granularity preserve a winner? | [§5, pp.10–12](paper/main.pdf#page=10) | [TA D, pp.12–17](paper/supplementary_material.pdf#page=12): proofs and counterexamples; [TA R, p.45](paper/supplementary_material.pdf#page=45): saved Threads expansion |
| What does requirement initialization establish? | [§4.2 and Table 2](paper/main.pdf#page=8) | [TA E–F, pp.17–25](paper/supplementary_material.pdf#page=17); [saved command and Railcab analyses](docs/CLAIMS.md#rq2-initialization-and-saved-policies) |
| Does granularity change feasibility? | [RQ1, Table 3, pp.13–15](paper/main.pdf#page=13) | [S4.1, pp.52–53](paper/supplementary_material.pdf#page=52); [all family inputs and outcomes](results/granularity/e6/); [54 inherited null comparisons](results/ablation/) |
| What do the implementation checks cover? | [RQ2 and Figure 2, pp.15–16](paper/main.pdf#page=15) | [TA P, pp.40–43](paper/supplementary_material.pdf#page=40); [S4.2, pp.54–55](paper/supplementary_material.pdf#page=54); [check and data map](docs/CLAIMS.md#rq2-initialization-and-saved-policies) |
| What are the costs and unresolved cases? | [RQ3, Table 4 and Figure 3, pp.16–17](paper/main.pdf#page=16) | [S4.3–S4.4, pp.56–69](paper/supplementary_material.pdf#page=56); [all 135 saved cells](paper/source/build/generated/rq3-cells.csv); [results and metric definitions](docs/RESULTS.md) |
| How does this relate to DUCS, GR(1) and supervisory control? | [Table 1](paper/main.pdf#page=4) and [§7](paper/main.pdf#page=18) | [TA I–J, pp.30–33](paper/supplementary_material.pdf#page=30); [S5, pp.86–87](paper/supplementary_material.pdf#page=86) |

If GitHub's preview ignores a page link, download the PDF and use the printed continuous page number or bookmarks. Keep `main.pdf` and `supplementary_material.pdf` in the same folder for links between the two documents.

## Results and interpretation

| Evidence | Reported result | Scope |
|---|---|---|
| Constructed granularity comparisons | **55 pairs: 33 separations, 11 both LOSS, 10 both WIN, 1 incomplete** | Thirty separations are Rolling/Canary parameter points; these are mechanism examples, not a prevalence estimate |
| Inherited Base/R1 granularity comparisons | **54 comparisons, no decision changes** | A retained null result |
| Fixed-budget synthesis, 27 contracts | Lazy **25 WIN / 1 LOSS / 1 TO**; Eager **17 WIN / 10 TO** | Same-game variants with identical UC pruning; Figure 3 includes all 27 contracts |
| Other fixed-budget variants | Update-first **23 WIN / 1 LOSS / 3 TO**; Direct-Full **14 WIN / 13 TO** | Update-first is faster in 8/24 completed comparisons; Direct-Full also changes construction and pruning |
| Saved-policy serialization | **10 Threads policies checked**, with the same endpoints and the exact event-count increase | Identity transfers, no monitors or precedence; not a general transformation implementation |
| Separate Legacy reference | **9 WIN / 13 OOM / 5 N/M** | A different subsequent-control objective; not a same-objective speed comparison |

[Detailed results](docs/RESULTS.md) preserve all fixed-budget cells, extended trials, null results and scope distinctions. [Results by question](results/README.md) leads to the models, tables, certificates and raw records.

The guarantees concern the supplied finite game: every admitted old entry, every modeled outcome, active-monitor safety and finite completion without fairness. Commands and handover require global modeled uncontrollable quiescence. Correct source interpretation and runtime conformance remain separate obligations. Static lookup cells are not activation executions; a timeout or OOM is not a proof of LOSS. The package does not establish deployment or human benefits.

## Reproduce the study

For a **small Python-only check of the three saved-evidence analyses retained from C143**, run from the repository root:

```sh
python3 -B reproduce/check_added_analyses.py --output work/added-c145
```

For the **complete saved-evidence check**, install the listed Python dependencies and choose a fresh output directory:

```sh
python3 -m pip install -r reproduce/requirements.txt
python3 -B reproduce/check.py --output work/check-c145
```

These commands inspect and recompute saved evidence; they do not rerun Java performance experiments. The complete check restores the archived workspace, checks tables and figures, and preserves negative and unresolved results. See [reproduction instructions](docs/REPRODUCTION.md) for dependencies, output reports, individual commands, and the more expensive synthesis and measurement reruns.

Large raw logs are included as ordinary Git files under [results/archives](results/archives/). There are no missing release assets or Git LFS downloads.

## Use the tool

Follow the [build-and-run walkthrough](tool/README.md) to build the source and run the small Rolling example, which returns WIN for individual transfers and LOSS when both transfers are merged. The resulting offline viewer exposes actions, states, ranks and certificates.

The [input guide](docs/INPUTS.md) explains the fixed endpoints, transfer outcomes, requirement lifetimes and initialization duties. Source builds require JDK 17 and Maven; dependencies come from recorded upstream sources. Rebuilt binaries and fresh examples are kept separate from the reported measurements.

## Repository layout

| Folder | Contents |
|---|---|
| [paper/](paper/README.md) | Matching PDFs, downloadable bundles, full appendix index and manuscript source |
| [results/](results/README.md) | Evidence by research question, including failures and raw archives |
| [reproduce/](reproduce/README.md) | Saved-evidence checks, paper build, campaigns, variants and restoration map |
| [tool/](tool/README.md) | Implementation, inherited models, source build and finite-example runner |
| [docs/](docs/README.md) | Claim map, input guide, detailed results, reproduction and packaging scope |

## Version correspondence

This release is [`fgducs-c145-20261004`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c145-20261004). Its main PDF and 361-file source ZIP preserve the selected C145 files exactly; the accompanying supplement and component PDFs are the matching C145 files. Relative to C143, C145 adds only a 94-word opening Introduction paragraph explaining the software-evolution context. The remaining research text, mathematical results and experimental evidence are unchanged.

**Links already printed in the manuscript are preserved.** C145's Data Availability, Table 5 and reference [4] cite [`fgducs-c143-20261004`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c143-20261004), the preceding supporting-material release. That immutable tag remains available. Its supplementary text, proofs, tables, implementation and saved evidence are the same as those supporting C145; its main PDF is C143 and lacks the new opening paragraph. Use the C145 PDF links above for the selected manuscript.

The implementation and original experimental observations are retained from the earlier archive. The three saved-evidence analyses accompanying C145 are directly available in [paper/source/evidence](paper/source/evidence/). Earlier tags, including [`fgducs-c143-20261004`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c143-20261004), [`fgducs-c115-20261003`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c115-20261003) and [`fgducs-invariants-20261002`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-invariants-20261002), retain their own PDFs and page numbers; their URLs identify historical evidence, not the current manuscript.

[Packaging and provenance](docs/PACKAGING.md) describe retained historical records, anonymous distribution copies and omitted binaries. Generative-AI assistance is disclosed in main §6.1 and TA Q. Private author notes, review conversations and submission records are not part of this package. This is a manuscript release; it does not claim that conference submission has been completed.

# FG-DUCS manuscript and supplementary material

[Main paper](main.pdf) · [Integrated supplementary material](supplementary_material.pdf) · [TeX and generated evidence](source/).

This is the manuscript and supplementary material prepared by the authors for the paper cited as **FG-DUCS Evaluation Artifact [4]**. These PDFs match snapshot [`fgducs-c82-20261003`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c82-20261003). The paper is titled *Synthesizing Staged Updates between Verified Controllers*. It has 18 body pages, followed by Data Availability and references (21 pages total). It develops a local-contract compiler for component transfers and individual requirement lifetimes. Table 2 distinguishes modeler-supplied inputs, generated game structure and synthesis outputs; it does not claim measured effort reduction. The complete Cell input and Policy lifetime example connect the contract to completing policies; full correspondence and synthesis proofs establish the generated game and procedure. The main paper preserves continuations from the selected new-controller state, separates game correctness, requirement interpretation and execution, and retains source-derived activation arguments, merging obstructions and all principal favourable and adverse results. Technical Appendix G gives the endpoint-interface and fixed-policy certificate-reuse results. The main text includes the activation-invariant criterion and its proof, then analyzes granularity before introducing synthesis. The guarantee table explains properties and premises; RQ2 explains the evidence in order: finite fixtures, source-monitor correspondence, the meanings and limits of initialization, GSM, and application WIN/LOSS interpretation. The design section illustrates R1 and R2 as alternative requirements using GSM. The audit and role example displays its opposing lifetime orders. Related Work separates supplied post-update control, independent requirement boundaries and local input generation. The concrete Cell input comparison and full analytical constructions are together in Technical Appendices H–I. Primary-source comparisons acknowledge earlier generation of update environments and safe adaptation paths, supervisor switching with state reinitialization, workcell reconfiguration through supervisor transformation, and switched-system invariant control. The activation-invariant criterion is supported by a separate finite analysis of 138 saved monitor occurrences and 900 non-error lookup cells; actual activation keys, observations and fallback behavior remain assumptions.

The 78-page supplementary material combines two pages of linked reading routes and complete contents, Part I (29-page technical appendix) and Part II (47-page supplementary proofs and experimental details). It retains the complete proofs and all reported outcomes while consolidating repeated definitions, proof recaps and verbatim logs; full logs remain in the artifact. Each smaller witness now presents its complete input before its proof. S4 follows the main RQ order: granularity mechanisms, independent checks, then fixed-budget costs. Its Railcab figure retains both outcomes of one saved transfer and every descendant branch. The history section introduces the current safe-prior and entry-based interpretations before the stronger whole-history diagnostic. S2 gives search invariants and complete proof references before the implementation ordering; S3 points to the authoritative execution proof without repeating its conclusion in a separate subsection. Its six reading routes connect examples, guarantees, requirement meaning, RQ1, RQ2–RQ3 and related work directly to the relevant pages. S5 separates update/adaptation interfaces from synthesis and switching, using plain-language columns for inputs, guarantees and scope. Both the routes and the complete section contents are clickable. It provides continuous page numbers and bookmarks, and redirects the main paper's references to the combined document. Keep these two PDFs together for relative cross-document links. Labels Technical Appendix A–P refer to Part I; S1–S5 refer to Part II. The separate [technical appendix](technical_appendix.pdf) and [experimental supplement](supplement.pdf) remain available as build components and for compatibility; citation links in the separate appendix point to the main bibliography.

S4.3 now separates definition preparation from adapter preparation, including endpoint products, activation closure and initializer tables. Its two tables retain all 27 contracts and four methods: five-run medians and ranges for 81 completed cells (405 runs), with 27 unresolved cells left unfilled. The closure count includes component versions and fluent observers; it is neither game size nor initializer-entry count. Lazy defers the remaining update-game exploration, while total JVM cost includes this preparation. [The complete preparation CSV](source/build/generated/rq3-preparation.csv) and [saved-data generator](source/scripts/generate_rq3_preparation.py) support reproduction.

The snapshot contains the manuscript, not a completed conference submission. `source/build/generated/` preserves saved display inputs, including all 135 fixed experiment cells and ext1–7 summaries. Private author notes, review conversations and submission instructions are excluded. The mathematical arguments and presentation changes add no benchmark measurements. [The evidence map](../docs/CLAIMS.md) distinguishes saved observations, proofs and unvalidated assumptions.

## Appendix section index

Page numbers below are **continuous PDF pages in [supplementary_material.pdf](supplementary_material.pdf)**, including its two-page reading guide and contents. The main paper's Technical Appendix A–P references identify Part I; S1–S5 identify Part II. The PDF bookmarks use the same section titles.

| Label | Section | PDF page |
|---|---|---:|
| A | Source Histories and Synthesis Correctness | [3](supplementary_material.pdf#page=3) |
| B | Complete Cell Contract and Its Two Completing Paths | [6](supplementary_material.pdf#page=6) |
| C | Policy Requirement-Boundary Argument | [7](supplementary_material.pdf#page=7) |
| D | NEW and UPD History-Scope Derivations | [9](supplementary_material.pdf#page=9) |
| E | Activation-Scoped Initialization | [9](supplementary_material.pdf#page=9) |
| F | Proof of Conditional Trace Lifting | [12](supplementary_material.pdf#page=12) |
| G | Endpoint Interfaces and Certificate Reuse | [14](supplementary_material.pdf#page=14) |
| H | Complete Native DUCS Construction for Cell | [16](supplementary_material.pdf#page=16) |
| I | Cell through a GR(1) Bridge Interface | [18](supplementary_material.pdf#page=18) |
| J | Saved PC2 Activation Histories and Their Boundary | [19](supplementary_material.pdf#page=19) |
| K | Default Exploration Order | [22](supplementary_material.pdf#page=22) |
| L | Complete Benchmark Input Counts | [23](supplementary_material.pdf#page=23) |
| M | All Completed Direct-Full Exploration Pairs | [24](supplementary_material.pdf#page=24) |
| N | Separate Extended-Budget Trials | [24](supplementary_material.pdf#page=24) |
| O | Separate Evaluation Populations and All-Contract Grid | [24](supplementary_material.pdf#page=24) |
| P | Implementation and AI-Assisted Research Details | [31](supplementary_material.pdf#page=31) |
| S1 | Granularity and observation witnesses | [32](supplementary_material.pdf#page=32) |
| S2 | Finite games, search invariants, and certificates | [34](supplementary_material.pdf#page=34) |
| S3 | Monitor intervals and conditional trace lifting | [38](supplementary_material.pdf#page=38) |
| S4 | Supplementary validation and cost tables | [43](supplementary_material.pdf#page=43) |
| S5 | Expanded related-work comparison | [77](supplementary_material.pdf#page=77) |

For Figure 2, inspect [the complete fixed-budget CSV](source/build/generated/rq3-cells.csv), including all five-trial time and peak-RSS ranges. Its third panel uses raw process bytes divided by 1,048,576 to obtain MiB. The generator retains every completed Lazy/Direct-Full pair; Table 5 and Appendix O retain the unresolved cases. See the [claim map](../docs/CLAIMS.md) for validation commands and scope limits.

The [original evidence snapshot](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-invariants-20261002) is preserved with its earlier manuscript PDFs. This section index applies to the current paper-matched release, not to that earlier pagination.

## Rebuild

Install XeLaTeX and latexmk, then run from the repository root:

```sh
python3 -m pip install -r reproduce/requirements.txt
python3 -B reproduce/build_paper.py --output work/paper
```

The build uses a new source copy and stabilizes main/technical cross-references. It writes the primary pair and both component PDFs under `work/paper/`, preserving distributed sources. PDF assembly checks text preservation, anonymous metadata, named destinations and cross-document links. The source PDFs remain in `work/paper/source/build/`. See `source/latexmkrc` for engine configuration.

# FG-DUCS manuscript and supplementary material

[Main paper](main.pdf) · [Integrated supplementary material](supplementary_material.pdf) · [TeX and generated evidence](source/).

This is the manuscript and supplementary material prepared by the authors for the paper cited as **FG-DUCS Evaluation Artifact [4]**. These PDFs match snapshot [`fgducs-c74-20261003`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c74-20261003). The paper is titled *Compiling Local Update Contracts into Controller-Preserving Policies*. It has 18 body pages, followed by Data Availability and references (21 pages total). It develops a local-contract compiler for component transfers and individual requirement lifetimes. Complete Cell and Policy inputs connect the contract to whole completing policies; full correspondence and synthesis proofs establish the generated game and procedure. The main paper preserves continuations from the selected new-controller state, separates game correctness, requirement interpretation and execution, and retains source-derived activation arguments, merging obstructions and all principal favourable and adverse results. Technical Appendix O gives the endpoint-interface and fixed-policy certificate-reuse results. The source-invariant initialization result is supported by a separate finite analysis of 138 saved monitor occurrences and 900 non-error lookup cells; actual activation keys, observations and fallback behavior remain assumptions.

The 76-page supplementary material combines a one-page reading guide, Part I (29-page technical appendix) and Part II (46-page supplementary proofs and experimental details). It retains the complete proofs and all reported outcomes while consolidating repeated definitions, proof recaps and verbatim logs; full logs remain in the artifact. It adds continuous page numbers and bookmarks, and redirects the main paper's references to the combined document. Keep these two PDFs together for relative cross-document links. Labels Technical Appendix A–P refer to Part I; S1–S5 refer to Part II. The separate [technical appendix](technical_appendix.pdf) and [experimental supplement](supplement.pdf) remain available as build components and for compatibility; citation links in the separate appendix point to the main bibliography.

The snapshot contains the manuscript, not a completed conference submission. `source/build/generated/` preserves saved display inputs, including all 135 fixed experiment cells and ext1–7 summaries. Private author notes, review conversations and submission instructions are excluded. The mathematical arguments and presentation changes add no benchmark measurements. [The evidence map](../docs/CLAIMS.md) distinguishes saved observations, proofs and unvalidated assumptions.

## Appendix section index

Page numbers below are **continuous PDF pages in [supplementary_material.pdf](supplementary_material.pdf)**, including its one-page reading guide. The main paper's Technical Appendix A–P references identify Part I; S1–S5 identify Part II. The PDF bookmarks use the same section titles.

| Label | Section | PDF page |
|---|---|---:|
| A | Source Histories and Synthesis Correctness | [2](supplementary_material.pdf#page=2) |
| B | Complete Cell Contract and Its Two Completing Paths | [5](supplementary_material.pdf#page=5) |
| C | Complete Benchmark Input Counts | [6](supplementary_material.pdf#page=6) |
| D | All Completed Direct-Full Exploration Pairs | [7](supplementary_material.pdf#page=7) |
| E | Default Exploration Order | [7](supplementary_material.pdf#page=7) |
| F | Separate Extended-Budget Trials | [8](supplementary_material.pdf#page=8) |
| G | NEW and UPD History-Scope Derivations | [9](supplementary_material.pdf#page=9) |
| H | Proof of Conditional Trace Lifting | [9](supplementary_material.pdf#page=9) |
| I | Policy Requirement-Boundary Argument | [10](supplementary_material.pdf#page=10) |
| J | Separate Evaluation Populations and All-Contract Grid | [12](supplementary_material.pdf#page=12) |
| K | Complete Native DUCS Construction for Cell | [18](supplementary_material.pdf#page=18) |
| L | Saved PC2 Activation Histories and Their Boundary | [19](supplementary_material.pdf#page=19) |
| M | Activation-Scoped Initialization | [23](supplementary_material.pdf#page=23) |
| N | Implementation and AI-Assisted Research Details | [26](supplementary_material.pdf#page=26) |
| O | Endpoint Interfaces and Certificate Reuse | [27](supplementary_material.pdf#page=27) |
| P | Cell through a GR(1) Bridge Interface | [29](supplementary_material.pdf#page=29) |
| S1 | Granularity and observation witnesses | [31](supplementary_material.pdf#page=31) |
| S2 | Finite games, search invariants, and certificates | [33](supplementary_material.pdf#page=33) |
| S3 | Monitor intervals and conditional trace lifting | [37](supplementary_material.pdf#page=37) |
| S4 | Supplementary validation and cost tables | [42](supplementary_material.pdf#page=42) |
| S5 | Expanded related-work comparison | [76](supplementary_material.pdf#page=76) |

For Figure 2, inspect [the complete fixed-budget CSV](source/build/generated/rq3-cells.csv), including all five-trial time and peak-RSS ranges. Its third panel uses raw process bytes divided by 1,048,576 to obtain MiB. The generator retains every completed Lazy/Direct-Full pair; Table 5 and Appendix J retain the unresolved cases. See the [claim map](../docs/CLAIMS.md) for validation commands and scope limits.

The [original evidence snapshot](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-invariants-20261002) is preserved with its earlier manuscript PDFs. This section index applies to the current paper-matched release, not to that earlier pagination.

## Rebuild

Install XeLaTeX and latexmk, then run from the repository root:

```sh
python3 -m pip install -r reproduce/requirements.txt
python3 -B reproduce/build_paper.py --output work/paper
```

The build uses a new source copy and stabilizes main/technical cross-references. It writes the primary pair and both component PDFs under `work/paper/`, preserving distributed sources. PDF assembly checks text preservation, anonymous metadata, named destinations and cross-document links. The source PDFs remain in `work/paper/source/build/`. See `source/latexmkrc` for engine configuration.

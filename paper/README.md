# FG-DUCS manuscript and supplementary material

[Main paper](main.pdf) · [Integrated supplementary material](supplementary_material.pdf) · [TeX and generated evidence](source/).

These materials were prepared by the authors for *Synthesizing Staged Updates between Verified Controllers*, whose reference **[4], FG-DUCS Evaluation Artifact**, identifies this package. The PDFs match [`fgducs-c114-20261003`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c114-20261003): 18 body pages and 21 pages total, plus 81 pages of integrated supplementary material. This records a manuscript release, not a completed conference submission.

The main paper proceeds from motivating Cell and Policy examples to the local contract, its generated game and guarantees, granularity, synthesis and evaluation. Table 1 compares the supplied inputs, generated results, progress and continuation of DUCS, GR(1) updating and FG-DUCS. Proposition 5.3 states the serial-transfer sufficient condition in the main paper; Technical Appendix O.13 contains its proof, counterexamples, finite checks and source-inspection table for all nine inherited inputs. Section 2.3 also distinguishes earlier O-DUCS analysis from the archived fork examined in S4.8. Broader primary-source comparisons appear in Related Work and S5.

Table 2 states the properties and premises; Table 4 identifies the corresponding validation populations and boundaries: 46 source positions reused in 138 contract occurrences, 900 non-error lookup cells, and 25 winning application contracts across 125 repeated runs. The paper distinguishes correctness of the supplied contract game, the meaning of requirements at activation, and faithful execution. Saved lookup exactness does not establish actual activation conformance: decoding, post-start keys, observer behavior and absence of fallback remain unchecked. Technical Appendix E, S3 and S4.2 give the detailed evidence; S4.5.1 connects the archived entry-initialization diagnostic to the current results without replacing the historical values.

The integrated supplement contains two linked guide pages, **Part I: Technical Appendix A–P (33 pages)** and **Part II: Supplement S1–S5 (46 pages)**. Six reading routes, a complete contents list, continuous page numbers and bookmarks lead to the proofs, full examples, checks, results and comparisons. S4 follows the main RQ order before presenting diagnostic, historical and extended-budget records separately. All positive, negative, invalid, timeout, OOM and unmeasured outcomes remain available.

Keep **main.pdf** and **supplementary_material.pdf** together for relative document links. The separate [technical appendix](technical_appendix.pdf) and [experimental supplement](supplement.pdf) are also retained as build components; the appendix's citation links point to the main bibliography.

The [claim-to-evidence map](../docs/CLAIMS.md) gives reproduction commands and scope limits. Saved preparation measurements for all contracts and methods are available in [the preparation CSV](source/build/generated/rq3-preparation.csv), with [its generator](source/scripts/generate_rq3_preparation.py). Full settings and unresolved costs remain in S4.3. The manuscript revisions add no benchmark measurements. Private author notes, review conversations and submission instructions are excluded.

## Appendix section index

Page numbers below are **continuous PDF pages in [supplementary_material.pdf](supplementary_material.pdf)**, including its two-page reading guide and contents. The main paper's Technical Appendix A–P references identify Part I; S1–S5 identify Part II. The PDF bookmarks use the same section titles.

| Label | Section | PDF page |
|---|---|---:|
| A | Source Histories and Synthesis Correctness | [3](supplementary_material.pdf#page=3) |
| B | Complete Cell Contract and Its Two Completing Paths | [7](supplementary_material.pdf#page=7) |
| C | Policy Requirement-Boundary Argument | [8](supplementary_material.pdf#page=8) |
| D | NEW and UPD History-Scope Derivations | [10](supplementary_material.pdf#page=10) |
| E | Activation-Scoped Initialization | [10](supplementary_material.pdf#page=10) |
| F | Proof of Conditional Trace Lifting | [13](supplementary_material.pdf#page=13) |
| G | Endpoint Interfaces and Certificate Reuse | [14](supplementary_material.pdf#page=14) |
| H | Complete Native DUCS Construction for Cell | [17](supplementary_material.pdf#page=17) |
| I | Cell through a GR(1) Bridge Interface | [19](supplementary_material.pdf#page=19) |
| J | Saved PC2 Activation Histories and Their Boundary | [20](supplementary_material.pdf#page=20) |
| K | Exploration Order and Work Bound | [23](supplementary_material.pdf#page=23) |
| L | Complete Benchmark Input Counts | [25](supplementary_material.pdf#page=25) |
| M | All Completed Direct-Full Exploration Pairs | [26](supplementary_material.pdf#page=26) |
| N | Separate Extended-Budget Trials | [26](supplementary_material.pdf#page=26) |
| O | Separate Evaluation Populations and All-Contract Grid | [26](supplementary_material.pdf#page=26) |
| O.13 | A local condition for serializing transfer batches | [32](supplementary_material.pdf#page=32) |
| P | Implementation and AI-Assisted Research Details | [35](supplementary_material.pdf#page=35) |
| S1 | Granularity and observation witnesses | [36](supplementary_material.pdf#page=36) |
| S2 | Finite games, search invariants, and certificates | [39](supplementary_material.pdf#page=39) |
| S3 | Monitor intervals and conditional trace lifting | [42](supplementary_material.pdf#page=42) |
| S4 | Supplementary validation and cost tables | [47](supplementary_material.pdf#page=47) |
| S5 | Expanded related-work comparison | [81](supplementary_material.pdf#page=81) |

For Figure 2, inspect [the complete fixed-budget CSV](source/build/generated/rq3-cells.csv), including all five-trial time and peak-RSS ranges. Its third panel uses raw process bytes divided by 1,048,576 to obtain MiB. The generator retains every completed Lazy/Direct-Full pair; Table 5 and Appendix O retain the unresolved cases. See the [claim map](../docs/CLAIMS.md) for validation commands and scope limits.

The [original evidence snapshot](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-invariants-20261002) is preserved with its earlier manuscript PDFs. This section index applies to the current paper-matched release, not to that earlier pagination.

## Rebuild

Install XeLaTeX and latexmk, then run from the repository root:

```sh
python3 -m pip install -r reproduce/requirements.txt
python3 -B reproduce/build_paper.py --output work/paper
```

The build uses a new source copy and stabilizes main/technical cross-references. It writes the primary pair and both component PDFs under `work/paper/`, preserving distributed sources. PDF assembly checks text preservation, anonymous metadata, named destinations and cross-document links. The source PDFs remain in `work/paper/source/build/`. See `source/latexmkrc` for engine configuration.

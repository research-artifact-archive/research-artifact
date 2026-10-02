# FG-DUCS manuscript and supplementary material

[Main paper](main.pdf) · [Integrated supplementary material](supplementary_material.pdf) · [TeX and generated evidence](source/).

These PDFs match snapshot [`fgducs-c73-20261002`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c73-20261002). The paper is titled *Compiling Local Update Contracts into Controller-Preserving Policies*. It has 18 body pages, followed by Data Availability and references (21 pages total). It develops a local-contract compiler for component transfers and individual requirement lifetimes. Complete Cell and Policy inputs connect the contract to whole completing policies; full correspondence and synthesis proofs establish the generated game and procedure. The main paper preserves continuations from the selected new-controller state, separates game correctness, requirement interpretation and execution, and retains source-derived activation arguments, merging obstructions and all principal favourable and adverse results. Technical Appendix O gives the endpoint-interface and fixed-policy certificate-reuse results. The source-invariant initialization result is supported by a separate finite analysis of 138 saved monitor occurrences and 900 non-error lookup cells; actual activation keys, observations and fallback behavior remain assumptions.

The 76-page supplementary material combines a one-page reading guide, Part I (29-page technical appendix) and Part II (46-page supplementary proofs and experimental details). It retains the complete proofs and all reported outcomes while consolidating repeated definitions, proof recaps and verbatim logs; full logs remain in the artifact. It adds continuous page numbers and bookmarks, and redirects the main paper's references to the combined document. Keep these two PDFs together for relative cross-document links. Labels Technical Appendix A–P refer to Part I; S1–S5 refer to Part II. The separate [technical appendix](technical_appendix.pdf) and [experimental supplement](supplement.pdf) remain available as build components and for compatibility; citation links in the separate appendix point to the main bibliography.

The snapshot contains the manuscript, not a completed conference submission. `source/build/generated/` preserves saved display inputs, including all 135 fixed experiment cells and ext1–7 summaries. Private author notes, review conversations and submission instructions are excluded. The mathematical arguments and presentation changes add no benchmark measurements. [The evidence map](../docs/CLAIMS.md) distinguishes saved observations, proofs and unvalidated assumptions.

## Rebuild

Install XeLaTeX and latexmk, then run from the repository root:

```sh
python3 -m pip install -r reproduce/requirements.txt
python3 -B reproduce/build_paper.py --output work/paper
```

The build uses a new source copy and stabilizes main/technical cross-references. It writes the primary pair and both component PDFs under `work/paper/`, preserving distributed sources. PDF assembly checks text preservation, anonymous metadata, named destinations and cross-document links. The source PDFs remain in `work/paper/source/build/`. See `source/latexmkrc` for engine configuration.

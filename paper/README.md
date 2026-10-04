# C143 paper and supplementary material

**Selected manuscript: C143, 4 October 2026.** [Read the main paper](main.pdf) · [Read the integrated supplement](supplementary_material.pdf) · [Download both PDFs](reading_bundle.zip) · [Download manuscript source](manuscript_source.zip).

The main paper has **18 pages of body text, 21 pages in total**. The integrated supplement has **87 pages**: a two-page guide and contents, **Technical Appendix A–R (43 pages)**, and **Supplement S1–S5 (42 pages)**. The PDFs and source ZIP contain the selected manuscript with only artifact-location and reference updates for this publication. The scientific body is unchanged.

## Start from the paper

| Main-paper item | Question answered | Read next |
|---|---|---|
| [§2, Figure 1, pp.2–4](main.pdf#page=2) | Why separate component transfers and requirement boundaries? | [Complete Cell and Policy contracts, TA B–C, pp.9–11](supplementary_material.pdf#page=9) |
| [§3, pp.4–8](main.pdf#page=4) | Which inputs determine the game, entries, outcomes and handover? | [Correspondence proof, TA A, p.3](supplementary_material.pdf#page=3); [endpoint reuse, TA H, p.28](supplementary_material.pdf#page=28) |
| [§4, Table 2, pp.8–10](main.pdf#page=8) | What is proved for the game, and what needs interpretation or execution premises? | [Initialization, TA E–F, pp.17–25](supplementary_material.pdf#page=17); [execution theorem, TA G, p.26](supplementary_material.pdf#page=26) |
| [§5, pp.10–12](main.pdf#page=10) | Which granularity changes preserve a winning policy? | [Full proofs and counterexamples, TA D, pp.12–17](supplementary_material.pdf#page=12) |
| [RQ1, Table 3, pp.13–15](main.pdf#page=13) | Where does granularity change feasibility, and where does it not? | [S4.1, pp.52–53](supplementary_material.pdf#page=52); [saved Threads expansion, TA R, p.45](supplementary_material.pdf#page=45) |
| [RQ2, Figure 2, pp.15–16](main.pdf#page=15) | What is checked in the generated game and saved application policies? | [Railcab activation, TA F.3, p.24](supplementary_material.pdf#page=24); [population map, TA P.1, p.40](supplementary_material.pdf#page=40); [S4.2, p.54](supplementary_material.pdf#page=54) |
| [RQ3, Table 4, Figure 3, pp.16–17](main.pdf#page=16) | How do same-game search variants compare under the recorded budgets? | [S4.3, p.56](supplementary_material.pdf#page=56); [complete metrics, S4.4, p.60](supplementary_material.pdf#page=60) |
| [Table 1, p.4](main.pdf#page=4), [§7, p.18](main.pdf#page=18) | What differs from existing update interfaces? | [DUCS and GR(1) Cell constructions, TA I–J, pp.30–33](supplementary_material.pdf#page=30); [expanded comparison, S5, pp.86–87](supplementary_material.pdf#page=86) |
| [§6.1, pp.12–13](main.pdf#page=12) | What was implemented, and how was AI used? | [Implementation and AI assistance, TA Q, p.44](supplementary_material.pdf#page=44) |
| [Data Availability, Table 5, p.19](main.pdf#page=19) | Which publication contains which materials? | [Version correspondence](#version-correspondence) |

**Figure 2 is the Railcab saved-policy illustration. Figure 3 is the 27-contract Lazy/Eager cost comparison.** The earlier 14-pair Lazy/Direct-Full cost and memory records remain in the supplement and saved data. Use this index for C143; earlier tags use different section labels and page numbers.

## Appendix section index

Every number below is a **continuous page of [supplementary_material.pdf](supplementary_material.pdf)**, including the two opening guide pages. The PDF bookmarks use the section titles below.

| Label | Section | Open page |
|---|---|---:|
| A | Source Histories and Synthesis Correctness | [3](supplementary_material.pdf#page=3) |
| B | Complete Cell Contract and Its Two Completing Paths | [9](supplementary_material.pdf#page=9) |
| C | Policy Requirement-Boundary Argument | [10](supplementary_material.pdf#page=10) |
| D | Granularity and Safe Serialization | [12](supplementary_material.pdf#page=12) |
| D.2 | Granularity need not preserve feasibility | [13](supplementary_material.pdf#page=13) |
| D.3 | A local condition for serializing transfer batches | [14](supplementary_material.pdf#page=14) |
| D.4 | Serializing requirement-boundary batches | [16](supplementary_material.pdf#page=16) |
| E | NEW and UPD History-Scope Derivations | [17](supplementary_material.pdf#page=17) |
| F | Activation-Scoped Initialization | [21](supplementary_material.pdf#page=21) |
| F.2 | Preserved Observers Across Update Commands | [23](supplementary_material.pdf#page=23) |
| F.3 | Source-Observer Analysis of the Saved Railcab Policies | [24](supplementary_material.pdf#page=24) |
| G | Proof of Conditional Trace Lifting | [26](supplementary_material.pdf#page=26) |
| H | Endpoint Interfaces and Certificate Reuse | [28](supplementary_material.pdf#page=28) |
| I | Complete Native DUCS Construction for Cell | [30](supplementary_material.pdf#page=30) |
| J | Cell through a GR(1) Bridge Interface | [32](supplementary_material.pdf#page=32) |
| K | Saved PC2 Activation Histories and Their Boundary | [33](supplementary_material.pdf#page=33) |
| K.1 | All New Requirements of the Saved PC2 Policy | [36](supplementary_material.pdf#page=36) |
| L | Exploration Order and Work Bound | [36](supplementary_material.pdf#page=36) |
| M | Complete Benchmark Input Counts | [38](supplementary_material.pdf#page=38) |
| N | All Completed Direct-Full Exploration Pairs | [39](supplementary_material.pdf#page=39) |
| O | Separate Extended-Budget Trials | [39](supplementary_material.pdf#page=39) |
| P | Separate Evaluation Populations and All-Contract Grid | [40](supplementary_material.pdf#page=40) |
| P.5 | Lifetime gaps in two saved policies | [42](supplementary_material.pdf#page=42) |
| Q | Implementation and AI-Assisted Research Details | [44](supplementary_material.pdf#page=44) |
| R | Static Expansion of Saved Threads Policies | [45](supplementary_material.pdf#page=45) |
| S1 | Granularity and observation witnesses | [46](supplementary_material.pdf#page=46) |
| S2 | Additional Game Encodings and Exploration Constructions | [49](supplementary_material.pdf#page=49) |
| S3 | Frontend Initialization and Lifecycle Checks | [50](supplementary_material.pdf#page=50) |
| S4 | Supplementary validation and cost tables | [52](supplementary_material.pdf#page=52) |
| S4.1 | Constructed operational mechanisms and controls | [52](supplementary_material.pdf#page=52) |
| S4.2 | Independent checks for the contract and returned policies | [54](supplementary_material.pdf#page=54) |
| S4.3 | Fixed-budget comparison on the 27 adapted contracts | [56](supplementary_material.pdf#page=56) |
| S4.4 | Detailed fixed-budget measurements and policy diagnoses | [60](supplementary_material.pdf#page=60) |
| S4.5 | Archived auxiliary campaigns and historical checks | [70](supplementary_material.pdf#page=70) |
| S4.6 | Extended-budget trials | [76](supplementary_material.pdf#page=76) |
| S4.7 | Separate Eager enlarged-heap trials | [78](supplementary_material.pdf#page=78) |
| S4.8 | Legacy reference, archived OTF path and fidelity checks | [79](supplementary_material.pdf#page=79) |
| S4.9 | Separate Legacy enlarged-heap reference | [84](supplementary_material.pdf#page=84) |
| S5 | Expanded related-work comparison | [86](supplementary_material.pdf#page=86) |

The [separate technical appendix](technical_appendix.pdf) and [separate S1–S5 supplement](supplement.pdf) are also available. Their local page numbers differ from the integrated PDF. Keep the two primary PDFs together when downloading; the reading bundle does this automatically.

## Find source, data and checks

| Folder or file | Purpose |
|---|---|
| [source/main.tex](source/main.tex), [technical_appendix.tex](source/technical_appendix.tex), [supplement.tex](source/supplement.tex) | The three document entry points |
| [source/technical_fragments/](source/technical_fragments/) | Definitions, statements, complete proofs and interpretation analyses; see the [claim map](../docs/CLAIMS.md) for exact files |
| [source/figures/](source/figures/) | Current and retained figure sources; the entry-point TeX files determine which are used |
| [source/build/generated/](source/build/generated/) | Saved tables, CSVs and macros, including [all fixed-budget cells](source/build/generated/rq3-cells.csv) and [preparation costs](source/build/generated/rq3-preparation.csv) |
| [source/evidence/](source/evidence/) | Self-contained copied inputs and C143's three saved-evidence analyses; [overview and direct commands](source/evidence/README.txt) |
| [source/scripts/](source/scripts/), [source/build_support/](source/build_support/) | Table/figure generators and standalone source-bundle build support |
| [../results/](../results/README.md) | Full scientific records outside the manuscript source bundle |
| [../reproduce/](../reproduce/README.md) | Public-root entry points for checking, rebuilding and restoring the original layout |

The source ZIP contains the exact manuscript source bundle, including copied inputs and analysis outputs; it is not a substitute for the complete tool and raw experiment archive. Use the full repository for full reproduction.

## Rebuild

With XeLaTeX, latexmk and the Python requirements installed, run from the repository root:

```sh
python3 -m pip install -r reproduce/requirements.txt
python3 -B reproduce/build_paper.py --output work/paper-c143
```

The builder uses a fresh source copy, stabilizes cross-document references and creates the four PDFs. It preserves distributed sources. The standalone ZIP also contains [its own build instructions](source/build_support/README.txt). PDF assembly preserves the text, named destinations and cross-document links.

## Version correspondence

The matching release is [`fgducs-c143-20261004`](https://github.com/research-artifact-archive/research-artifact/tree/fgducs-c143-20261004), cited by main-paper Data Availability, Table 5 and reference [4]. It contains all four matching PDFs, the source ZIP and all three added saved-evidence analyses. C143’s scientific body remains unchanged; only artifact locations and references were updated for publication. Historical input-provenance references to C115 remain valid and identify the earlier unchanged input bytes.

Earlier tags remain unchanged. Their paper PDFs are earlier manuscripts, so their appendix labels and pagination must not be used with this index. No new synthesis or performance measurement is introduced by this publication. [Packaging scope](../docs/PACKAGING.md) and the [claim map](../docs/CLAIMS.md) distinguish proofs, static checks, saved observations and unvalidated execution premises.

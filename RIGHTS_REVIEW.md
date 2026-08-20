# Pre-publication rights review

This local handoff is mechanically ready for an anonymous Git repository, but
the following human rights review is intentionally not automated. A public
push is authorized only after the authors replace every `PENDING` decision with
the applicable permission or license record. Citation and SHA-256 provenance
do not grant redistribution rights.

| File class | Public path | Current treatment | Decision |
|---|---|---|---|
| Original analysis, verification, protocol, tests, and generated evidence | `analysis/`, `tools/`, `tests/`, `protocols/`, most of `evidence/` | Intended author material under the repository MIT text; confirm all contributors agreed | PENDING |
| Current Java integration source absent from upstream | `source-rebuild/added/` | Intended author additions; confirm authorship and contributor consent | PENDING |
| Patch with one line of upstream context | `source-rebuild/patches/fg-ducs-v1.1.0.patch` | Upstream context is minimized but still requires a distribution basis | PENDING |
| Nine fixed FG-DUCS adaptations | `Implementation/Experiment/Models/*.lts` | Parent mapping and hashes are recorded; unmodified parents are omitted | PENDING |
| Twelve Travel Agency adaptations | `inputs/c2/travel_agency_family/Models/` | Clearly labelled derived adaptations; canonical source omitted and hash-bound | PENDING |
| Two ARDrone adaptations | `inputs/c3/Models/` | Clearly labelled author adaptation; source anchor omitted and hash-bound | PENDING |
| Forty-one generated semantic inputs and eight independent inputs | `inputs/c1/semantic_boundaries_v2/Models/`, `inputs/c2/inputs/Models/` | Treat as author-generated only after contributor confirmation | PENDING |
| MTSA source tree, binaries, dependencies, DUCS parent models, and canonical OTF-DCS resources | not included | Reviewers fetch the pinned upstream archive; URLs and hashes only | OMITTED |

After the review, retain the evidence for each resolved row outside the
anonymous repository if it would identify the authors. Record only a neutral
status and license/permission scope here. Then regenerate `SHA256SUMS`, rerun
`./reproduce.sh handoff`, and perform the logged-out clone check in `README.md`.

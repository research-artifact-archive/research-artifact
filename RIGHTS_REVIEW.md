# Distribution permission scope

This repository is public. The authors confirmed permission to modify and
publish the inherited MTSA/DUCS-based tool on 2026-08-31. This author attestation
covers the tool integration sources and patch below; its identifying basis is
retained outside this anonymous repository. It is not an independent legal
audit, a new license for MTSA or its dependencies, or a confirmation of every
derived benchmark and contributor class. Citation and SHA-256 provenance do
not grant redistribution rights.

| File class | Public path | Current treatment | Decision |
|---|---|---|---|
| Original analysis, verification, protocol, tests, and generated evidence | `analysis/`, `tools/`, `tests/`, `protocols/`, most of `evidence/` | Intended author material under the repository MIT text; confirm all contributors agreed | PENDING |
| Current Java integration source absent from upstream | `source-rebuild/added/` | Modification/publication permission confirmed by author attestation for the MTSA/DUCS-based tool; includes inherited code, not only novel contributions | PERMISSION_CONFIRMED |
| Patch with one line of upstream context | `source-rebuild/patches/fg-ducs-v1.1.0.patch` | Same author-attested tool modification/publication permission; no upstream relicensing | PERMISSION_CONFIRMED |
| Nine fixed FG-DUCS adaptations | `Implementation/Experiment/Models/*.lts` | Parent mapping and hashes are recorded; unmodified parents are omitted | PENDING |
| Twelve Travel Agency adaptations | `inputs/c2/travel_agency_family/Models/` | Clearly labelled derived adaptations; canonical source omitted and hash-bound | PENDING |
| Two ARDrone adaptations | `inputs/c3/Models/` | Clearly labelled author adaptation; source anchor omitted and hash-bound | PENDING |
| Forty-one generated semantic inputs and eight independent inputs | `inputs/c1/semantic_boundaries_v2/Models/`, `inputs/c2/inputs/Models/` | Treat as author-generated only after contributor confirmation | PENDING |
| MTSA source tree, binaries, dependencies, DUCS parent models, and canonical OTF-DCS resources | not included | Reviewers fetch the pinned upstream archive; URLs and hashes only | OMITTED |

Five file classes remain `PENDING`; the omitted class remains `OMITTED`.
The tool permission must not be substituted for the remaining class-specific
confirmation. Keep identifying permission records outside the anonymous
repository and preserve third-party attribution. Maintenance of this existing
public repository uses `./reproduce.sh portable`, checksums, neutral commits,
and logged-out clone checks. `handoff` is the historical pre-publication gate,
not the gate for this established repository. Neither a public URL nor a
portable-check PASS establishes release-wide rights clearance.

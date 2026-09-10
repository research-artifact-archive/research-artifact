# Paper-to-evidence map

The stored manuscript is *The Total-Work Cost of Bounded Retry Guarantees*, snapshot197; its exact identity is [paper/SNAPSHOT.json](paper/SNAPSHOT.json). It integrates the comparison-free/common-guard, changed-call-weight and unit-guard DAG results below. Current locators: model2, universal protection3, total-work and call-weight results4, complete programs/observation5, Java6, charged representation and complexity7, evaluation8, related work9, limitations10, conclusion11. Do not interpret older theorem numbers as current paper locators. References to different commits of this repository describe one research lineage, not independent novelty baselines.

| Obligation | Evidence entry | Standard replay stages |
|---|---|---|
| Complete body-work frontiers for independent jobs and arbitrary retry slack | [General retry](charged/GENERAL_RETRY.md) | `general-retry`, `one-retry-native` |
| Least total-work curve for a universally completing policy with optimal protection at every hidden budget | [Universal independent jobs](charged/UNIVERSAL_INDEPENDENT.md) | `universal-independent`, `universal-independent-native` |
| One-write full-program representation with entry/comparison work charged in both resources | [Charged-comparison guide](charged/CHARGED_COMPARISON.md) | `charged-comparison`, `fully-charged-one-write` |
| Independent free-comparison NP/DP boundary, common-guard greedy frontier and heterogeneous exponential output | [Resource accounting](charged/RESOURCE_ACCOUNTING.md) | `guard-only-joint`, `uniform-guard` |
| Unit guard costs on a two-level DAG: strongly NP-complete joint caps, polynomial frontier size, all-call-fee translation | [Unit-guard DAG](charged/UNIT_GUARD_DAG.md) | `unit-guard-dag` |
| Charging a cached mismatch two units while keeping the operation atomic | [Resource accounting](charged/RESOURCE_ACCOUNTING.md) | `double-counted-mismatch` |
| Linux pathname source correspondence, exact body events, alternate comparators and logical/native call-count distinction | [Linux and guard entry](charged/LINUX_GUARD.md), [counting analysis](charged/CHARGED_COMPARISON.md) | `linux-dentry`, `linux-counting`, `guard-entry` |
| Roslyn immutable outputs, reentry, source preservation, arrivals, partial repair and cost limits | [Source semantics](charged/SOURCE_SEMANTICS_AND_PARTIAL_REPAIR.md), [partial repair](charged/PARTIAL_COMPACT.md) | `roslyn-source`, `roslyn-semantics`, `roslyn-reentry`, `roslyn-arrivals`, `partial-repair`, `roslyn-compilation`, plus the linked later studies |
| Earlier mechanisms, stronger comparators, failures and unresolved transfer assumptions | [Research lineage](charged/RESEARCH_LINEAGE.md), [full charged history](charged/README.md) | Included in the complete52-stage replay |

The native/source entries state their premises and exclusions. They do not claim general fixed-work transfer, a caller-required numerical cap, native latency optimality or a measured human benefit. Every negative result remains at its original denominator; replay does not turn it into a favorable result. The mathematical proof supplies the asymptotic and all-program claims; bounded enumerations corroborate particular implementations and witnesses.

Run `python3 -B tools/verify_release.py` for the full distribution inventory, and `python3 -B charged/reproduce.py all --out work/all52 --timeout 300` for every standard stage. Each stage requires a fresh output directory and verifies its frozen dependencies. Optional native rebuilds are separate, documented operations and are not part of the52-stage fixed-evidence claim.

The [preceding historical map](docs/PAPER_ARTIFACT_MAP_BEFORE_UNIT_GUARD.md) retains all old package table mappings and commands byte-for-byte. Its relative paths refer to the repository root where that map originally lived. The [reproduction receipt](REPRODUCTION_20260910.json) records verification scope and completed executions.

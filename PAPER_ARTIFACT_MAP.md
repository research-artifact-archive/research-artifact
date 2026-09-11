# Manuscript240 evidence map

The stored paper is *Resource Contracts for Completing Optimistic Computations*, snapshot240, body18/total21 pages. Its central new result bounds the worst body work of every permitted immediate-preparation caller on every finite DAG against the full general-program optimum under the same simultaneous call/protection contract. Exact residual safety and its fee-dependent information boundary make the permitted choices explicit.

| Paper question or claim | Guide | Standard replay stages |
|---|---|---|
| Sections2–4, Theorems1–2: optimal universal protection and exact independent-job work curve | [General retry](charged/GENERAL_RETRY.md), [independent jobs](charged/UNIVERSAL_INDEPENDENT.md) | `general-retry`, `one-retry-native`, `universal-independent`, `universal-independent-native` |
| Section5, Theorem3: exact completed-state residual viability and all safe modes | [Residual safety](charged/RESIDUAL_SAFETY.md) | `residual-safety` |
| Section5, Theorem4: sharp uniform approximation for all permitted callers on arbitrary DAGs | [Proof, audits and finite population](charged/DAG_APPROXIMATION.md) | `dag-approximation` |
| Section6, Theorem5: exact arbitrary-premium residual region and safe-mode limits | [General fee proof and implementation](charged/CHARGED_GENERAL.md) | `charged-general` |
| Section6, Proposition6: equal visible/current information can require opposite permissions | [Residual fee boundary](charged/RESIDUAL_SAFETY.md), [general fees](charged/CHARGED_GENERAL.md) | `residual-safety`, `charged-general` |
| Section6, Theorem7: three actual operation prices, including signed transformed costs | [Three-price oracle](charged/THREE_COST_RESIDUAL.md) | `three-cost-residual` |
| Section7, preceding observation result: strict cached erasure changes the supplied-budget frontier | [Observation DAG](charged/OBSERVATION_DAG.md), [program proof](charged/FULL_PROGRAM_PROOF.md) | `general-retry`, `universal-observation-dag` |
| Section7, preceding call-accounting result: charging a mismatching cached completion twice | [Resource accounting](charged/RESOURCE_ACCOUNTING.md) | `double-counted-mismatch` |
| Section8, Theorem8: conditional Java correspondence for actual external writes | [Java interface proof](charged/JAVA_INTERFACE_PROOF.md), [interface guide](charged/INTERFACE_GUIDE.md) | earlier Java stages linked in those guides |
| Section9.1: executable body/common-premium filter, original traces and equal worst-work coordinates | [Java residual filter](charged/JAVA_RESIDUAL_FILTER.md) | `java-residual-filter` |
| Section9.2: cached Linux variant keeps two logical calls but permits three body attempts; two-cheap can also make three calls | [Linux and guard entry](charged/LINUX_GUARD.md), [counting](charged/CHARGED_COMPARISON.md) | `linux-dentry`, `linux-counting`, `guard-entry` |
| Section9.3: Roslyn preservation, fixed-cost transfer failure and native latency limits | [Source semantics](charged/SOURCE_SEMANTICS_AND_PARTIAL_REPAIR.md), [partial repair](charged/PARTIAL_COMPACT.md) | linked Roslyn and partial-repair stages |
| Earlier policy studies and all adverse/equal cases | [Short order](charged/SHORT_ORDER_POLICY.md), [safe suffix](charged/SAFE_FRESH_SUFFIX.md) | `short-order-policy`, `safe-fresh-suffix` |
| Earlier frontiers, charged representation, hardness and stronger comparators | [Resource accounting](charged/RESOURCE_ACCOUNTING.md), [unit-guard DAG](charged/UNIT_GUARD_DAG.md), [lineage](charged/RESEARCH_LINEAGE.md) | included in the complete60-stage driver |

Run `python3 -B tools/verify_release.py` for the full inventory and `python3 -B charged/reproduce.py all --out work/all60 --timeout 300` for the60 standard stages, in a fresh directory. [REPRODUCTION_20260911.json](REPRODUCTION_20260911.json) records successful fresh public verification of the immutable evidence commit cited by the paper. Native rebuilds are separate. Finite agreement does not replace a general proof, and overlapping study counts are not independent samples of software workloads. No new scientific sample is created by the paper publication.

Outside the PDF, [joint-resource analytical consequences](paper/supplement/JOINT_RESOURCES.md) give common monotone-objective optima, exact classes and the priced caller factor. [Its manifest](paper/supplement/SUPPLEMENT_MANIFEST.json) distinguishes existing foundations, draft corrections, author checks and nine arithmetic examples. Existing60-stage reproduction does not certify these additional analytical assertions; no additional native sample is claimed.

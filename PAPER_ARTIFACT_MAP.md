# Manuscript219 evidence map

The stored manuscript is *Resource Contracts for Completing Optimistic Computations*, snapshot219, body18/total21 pages. Its core is the total-work consequence of a completion contract, the exact residual safety interface and its fee-dependent information boundary. Earlier auxiliary results stay available with their own original scope.

| Paper question or claim | Guide | Standard replay stages |
|---|---|---|
| Sections2–4: call/protected-work guarantees and least total-work curve under simultaneous optimal protection | [General retry](charged/GENERAL_RETRY.md), [universal independent jobs](charged/UNIVERSAL_INDEPENDENT.md) | `general-retry`, `one-retry-native`, `universal-independent`, `universal-independent-native` |
| Section5, Theorem4: exact completed-state residual viability, permitted modes and two heaps | [Residual safety](charged/RESIDUAL_SAFETY.md) | `residual-safety` |
| Section6, Theorem5 and Proposition6: fee separation, common-fee cancellation and opposite permissions under the same q/DAG/prefix | [Residual safety](charged/RESIDUAL_SAFETY.md) | `residual-safety` |
| Section7.1, Proposition7: strict cached erasure changes supplied and unknown-budget work guarantees | [Observation DAG](charged/OBSERVATION_DAG.md), [program proof](charged/FULL_PROGRAM_PROOF.md) | `general-retry`, `universal-observation-dag` |
| Section7.2, Proposition8: charging cached mismatch twice changes the universal guarantee | [Resource accounting](charged/RESOURCE_ACCOUNTING.md) | `double-counted-mismatch` |
| Section8, Theorem9: conditional Java correspondence with saved outputs and actual external writes | [Java interface proof](charged/JAVA_INTERFACE_PROOF.md), [interface guide](charged/INTERFACE_GUIDE.md) | earlier Java stages linked in those guides |
| Section9.1: executable residual filter, fixed branch traces and all-equal worst-work comparison | [Java residual filter](charged/JAVA_RESIDUAL_FILTER.md) | `java-residual-filter` |
| Section9.2: Linux source-body, logical-call and native-primitive distinctions, with changed attempt cap | [Linux and guard entry](charged/LINUX_GUARD.md), [counting](charged/CHARGED_COMPARISON.md) | `linux-dentry`, `linux-counting`, `guard-entry` |
| Section9.3: Roslyn preservation, failure cases and limits of fixed-cost/latency transfer | [Source semantics](charged/SOURCE_SEMANTICS_AND_PARTIAL_REPAIR.md), [partial repair](charged/PARTIAL_COMPACT.md) | linked Roslyn and partial-repair stages |
| Preceding short-order and sufficient-suffix studies, with all adverse/equal cases | [Short order](charged/SHORT_ORDER_POLICY.md), [safe suffix](charged/SAFE_FRESH_SUFFIX.md) | `short-order-policy`, `safe-fresh-suffix` |
| Earlier charged representation, frontiers/hardness and stronger comparators | [Resource accounting](charged/RESOURCE_ACCOUNTING.md), [unit-guard DAG](charged/UNIT_GUARD_DAG.md), [research lineage](charged/RESEARCH_LINEAGE.md) | included in the complete57-stage driver |

Run `python3 -B tools/verify_release.py` for the full inventory, and `python3 -B charged/reproduce.py all --out work/all57 --timeout 300` for all standard stages in a fresh directory. Native rebuilds are separate documented operations. [REPRODUCTION_20260911.json](REPRODUCTION_20260911.json) states which checks have actually completed. Fixed populations overlap; finite agreement corroborates code and examples and does not replace a general proof or establish software importance. Publication preserves previous negative outcomes.

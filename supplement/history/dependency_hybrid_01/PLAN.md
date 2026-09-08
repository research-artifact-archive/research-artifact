# Cost-compatible DAG dispatch: exploratory implementation successor

Status: PLANNED, no hybrid execution or outcomes yet. Root single writer. Prior DAG compiler/curves/checker/native evidence and independent compiler remain byte-unchanged. This is implementation development and comparison, not a new final evaluation or application witness.

## Structural result and implementation scope

If each edge(u,v) satisfies c_u<=c_v, a nondecreasing-c topological order exists. Kahn selection by(c_i,stable ID) produces one: a not-yet-ready smaller-cost node would have a ready ancestor of no greater cost. Removing edges gives the independent relaxation as a lower bound. Its sorted-order optimum is legal in the original DAG at every history, hence also an upper bound. The values are equal for every B. Complexity O(|E|+n log n) arithmetic for condition/order plus O(n) packing, with O(n+|E|) input and O(n) policy/value encoding. No new theorem beyond this direct corollary is claimed.

The existing independent compiler sorts equal c by p and ID. That tie rule is NOT safe for arbitrary DAG labels: a parent and child can have equal c and reversed premiums/IDs. Create a local packing implementation accepting the proved topological order; preserve the original compiler. Retain the DAG as a contract and readiness assertion at dispatch/execution. Inputs failing the condition use the unchanged ideal compiler. Reject cyclic/malformed inputs before either route, rather than implying the price condition proves acyclicity.

## Before running

Write the exact hybrid/check/runner sources, input-generation rules, all units and manifests before scientific comparison. Structural preparation may count units and condition applicability without computing values. Planned correctness checks: all643 known small DAG inputs, with provenance explicitly reused, against the existing unrestricted scalar tables and encoded ideal values; fresh relabelled equal-cost adversarial tie fixtures and zero premiums; checks of emitted action readiness and every policy maximum for small fixed budgets. Retain all failures/timeouts/invalid, not just value mismatches. The new ordinary-DAG route must not be labeled an independent algorithm or a new population.

Select new scale inputs by the structural predicate before any value/timing outcome, not by successful compilation or gap. Include large chains/layered/sparse DAGs and independent graphs with c compatible by construction, arbitrary labels, small/wide binary prices and zero premiums. Freeze exact n/families/seeds/count and per-unit wall/RSS caps in a MATERIALIZED_PLAN before run. All work remains bounded below September8 09:50JST, hard stop10:00JST.

For the old87-case scale corpus, do not rerun unchanged adverse fallback paths merely to improve timeout statistics. First determine which inputs use genuinely changed packing code. Either evaluate that changed subset with all denominators retained and bind the remainder to its old exact fallback receipts, clearly labeling any aggregate as historical-plus-new, or conduct a substantively changed whole-method comparison under a separately justified protocol. Never silently replace old9 compiler timeouts or4 checker timeouts. Prototype-only value timings cannot be compared as if both methods returned identical all-budget certificates unless both outputs/checking costs are accounted for.

## Evidence and limits

The fast path removes avoidable ideal expansion; it does not establish source applicability, production speed, a general polynomial algorithm, or final research/paper readiness. All current source-fit failures stay OPEN. A full-budget checker for packed outputs must state its theorem/TCB use and independence precisely; reconstructing the same packing algorithm is not independent proof certification.

# Exact reasoning for the generated Rolling family

This note describes the fixed `v1` generator. It is a derivation, not a substitute for measurements; the tabulated observations remain in `v1/summary.csv`.

## Group-size threshold

The generator partitions the n replicas into consecutive nonempty groups, each of size k except possibly the last. The product relation for a group maps all its old ready states to new booting states. If k > n−m, a size-k group is present and must eventually be transferred; immediately afterward there are at most n−k < m ready replicas, irrespective of earlier transfers or their order. The interval error is immediate and absorbing, so neither later readiness nor service can repair that prefix. Hence strong completion is impossible.

If every group has size at most n−m, transfer one group and wait for all its UC readiness events before selecting another. Every transferred replica has exactly one enabled readiness transition to ready, and no waiting loop; all report orders terminate after exactly the group size many readiness events. The ready floor holds because at most one group's replicas are booting. Every group event is discharged, all replicas become new-ready, and the fixed new endpoint matches. Thus the generated contract is WIN exactly when k <= n−m. This proof relies on finite guaranteed startup in this model, not a fairness assumption about an implementation.

The completion length of this serial-group strategy is n + ceil(n/k): n readiness events plus one transfer per group. No successful path can use fewer because all these events are necessary. The user-level shorthand n/k groups requires k dividing n; the actual generator uses ceil(n/k) and records the smaller final group.

## Full-construction count for individual transfers (k=1)

For 1 <= m <= n−1, the only non-ready replica reachable under E1 Post is the replica just transferred: while it is booting, its UC readiness event blocks every further update event. Ordinary service actions are physical/tester self-loops. Stable states are indexed by the subset S of already updated, new-ready replicas, giving 2^n distinct states. A transient booting state is indexed by its unique booting replica i and an arbitrary subset S of the other n−1 updated replicas, giving n*2^(n−1) states. The pending set and ready-count tester are determined by these physical states, so they add no multiplicity. All these states are reachable by choosing the corresponding earlier update order, and the sole goal is included even though it is not expanded.

Therefore the exact number of Direct-Full discovered states is

`2^n + n*2^(n−1) = (n+2)*2^(n−1)`.

The returned path needs 2n transitions. In the measured n=2..6 runs, Lazy discovered exactly its 2n+1 path states, and Direct-Full measured 8,20,48,112,256 states respectively for every tested m. The exponential full-game formula holds for this generated family; the exact observed Lazy count also reflects the fixed E1 action ordering and should not be generalized to arbitrary contracts or solvers. No value beyond the measured parameter range is inserted into an experimental results column.

## Explicit input size

For individual transfers, the JSON contains n old local states and 2n new local states in total, 2n ordinary action labels, and n transfer labels. Its one ready-count interval tester has n−m+2 states (including the error state) and 2n(n−m+1) explicitly listed changes. Endpoint representations and initializers are linear in n. Thus the explicit input size is polynomial in n; the exponential full-game count is not obtained by supplying an already exponential monitor. The structural-size CSV accompanying the scale plot checks these counts directly against each selected input. This does not make the action-order-dependent Lazy count a general complexity bound.

## Candidate queries, nonempty buckets, and outcomes

A non-goal state has exactly 2n candidate labels: n service labels, one readiness label per already-new component, and one pending transfer per still-old component. Direct-Full queries every candidate, including empty Post sets. For D=(n+2)2^(n−1), its query count is therefore 2n(D−1). This counts state/action requests, not only enabled transitions.

A stable state with s updated replicas has n service and n−s transfer buckets. Summing over stable subsets and omitting the terminal goal gives 3n2^(n−1)−n. Each of the n2^(n−1) single-boot states has n−1 service buckets and one ready bucket. Thus enabled buckets total n(n+3)2^(n−1)−n. Every bucket is deterministic in Rolling, so materialized outcomes equal that number. This equality does not hold in set-valued Canary and is not a universal metric identity. As with state counts, formulas are predictions to compare with completed measurements, not replacements for missing columns.

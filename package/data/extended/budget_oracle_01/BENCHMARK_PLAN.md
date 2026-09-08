# Benchmark01: six declared budgets, cold construction and checking

After canonical conformance and contract hardening, fix48 newly authored cases:
chain, four disjoint chains, fence, and four-wide layered DAGs; sizes4/8/16/32;
SMALL, WIDE_PREMIUM and WIDE_PRICES. A deterministic seed202609080619 supplies
prices and label permutation. WIDE_PREMIUM changes premiums only by2^32 plus
small offsets; WIDE_PRICES changes both independently by2^32 plus offsets.
Keep zero premiums and duplicate/isomorphic shapes, including the independent
four-chain size4 case. These are generated method probes, not applications.

For each case compute sat=sum ceil(p_i/c_i). The declared ordered query list is
[1,2,8,max(1,sat//4),max(1,sat//2),max(1,sat)]. Keep duplicate budgets. Two methods
run once per case: hardened memoized concave oracle with one union certificate,
and unchanged all-budget hybrid plus strict full checking followed by these
queries. Six-budget workload membership is fixed before any new method results.

The oracle returns a certificate for these six values only. All-budget returns
values/policies for every budget, so the outputs have different scope. The
experiment measures the cost of obtaining certified requested values; it does
not assert strategy or runtime-online equivalence. When both succeed, every
requested value must agree. Preserve a full96-unit denominator and all failure,
timeout, invalid and unstarted outcomes. Never rerun an unchanged adverse unit.

Every method is a fresh serial process with5seconds and sampled1GiB RSS,
including imports, input loading, construction, serialization, reload and
checking. Alternate method order by case index. Campaign cap540seconds. Keep
commands, stdout/stderr, JSON artifacts, process/RSS observations and terminal
records. Report constructor/checker time separately where captured. The oracle
shares memo entries across the six queries; full-curve construction is performed
once per case. No external solver or published baseline is claimed for this
author-derived oracle. Neither elapsed-time benefit nor prevalence in software
applications follows from these synthetic workloads.

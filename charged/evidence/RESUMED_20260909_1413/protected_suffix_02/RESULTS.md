# Observed suffix-certificate results

The fixed policy comparison covers 6,544 authored inputs and all 209,408 (B,r) roots. The new input portion is all 1,024 five-job chains with works in {1,2,3,4}; 5,520 inputs were already observed. All roots preserve the universal worst protected-work curve and call cap, with worst total work no greater than the same-order threshold policy. Relative to the previous all-tail guard, there are 209,404 ties, one lower value, and three higher values. Thus neither rule is a universal improvement over the other.

The better case is chain (3,4,1,2,1), B=6,r=3: threshold/all-tail W=30, certificate W=29, both L=9,Q=8. The adverse example has works (1,6,4,2,6,9), edges 5->2,2->3,2->4,2->0,3->4, B=6,r=2: threshold/certificate W=67, all-tail W=65, L=25,Q=8. The full raw ledger retains all three adverse roots.

A separate finite-rank AND-OR solver checks the suffix-feasibility formula on 363 weight tuples of lengths 1..5 over {1,2,4}; all subsets, h=0..n and ell=0..sum(w) give 665,500 states and 1,331,000 comparisons. Both arbitrary next-job and fixed-index next-job versions agree with the formula: 271,630 states are feasible and 393,870 infeasible. This is finite equation evidence, not a mechanical proof.

The Java source executes all 20,594 fixed paths for four shapes, r=0..3, B=0..7 and three policies, giving 384 groups. All succeed. The separate Python checker verifies exact captured-parent values, integer outputs, current identities, call/selection grammar and actual W/L/Q counters; all 384 component maxima match the equations, and all eight corruptions are rejected. The selector is given only works, predecessors, r, policy and its own outcomes. Neither B nor the path is passed into it. javap records the selector fields and methods. The checker was fixed before these native outcomes but descends from an already observed checker. The native inputs and equation outcomes were already observed.

No timing campaign, new application population, human evaluation or general total-work optimum is claimed. The previous all-tail native study and every unfavorable result remain unchanged.

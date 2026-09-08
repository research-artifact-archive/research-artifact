# Certified specified-budget oracle: exploratory method

The B1/B2 comparisons motivate an exact alternative for general binary-encoded
budgets. This is an author-derived comparator using the already established DAG
concavity identity and inherited allocation/fixed-mode bounds. Do not present
binary search, reflection theory, or bound screening as new general techniques.
No claim of practical advantage is made before evaluation.

For (S,B), choose cheapest available i, g(k)=V(S-i,k), and protected minimum h(B).
The existing theorem gives V(S,B)=min(h(B),c_i B + max_{0<=k<=B}(g(k)-c_i k)).
Discrete concavity permits binary search for a peak using differences g(k)-g(k-1).
Every recursive oracle call removes a job; budget-1 self recursion is absent.
Memoize (S,b) values. Allocation L and fixed-protection U may close a query before
branching. A call performs O(log(B+1)) child probes plus at most n protected
children, but the number of distinct recursive queries can still be exponential.
For fixed n an uncached recurrence is bounded by (n+O(log(B+1)))^n calls; no
general polynomial solve-time or small-certificate guarantee follows.

Emit a root VALUE certificate as a dependency DAG of exact subquery values:
base zero nodes; equal L/U nodes; or a peak k with all protected children and
neighboring g values certifying the concave maximum. A separate checker imports
neither oracle nor bound implementation, checks exact input types/DAG and each
arithmetic obligation, reconstructs required nodes, rejects missing/extraneous
nodes, and relies explicitly on the mathematical DAG concavity theorem.

This artifact certifies a requested root value. It is not a full precompiled
strategy for every future residual budget. An online policy may query successive
states, incurring additional work. Comparisons must distinguish this output from
full CP/DP policy certificates and all-budget curves, and report initial
construction/serialization/checking plus later queries when evaluated.

Before new outcomes, fix implementation/checker bytes and complete development
inputs: existing complete-primitive grid and selected known large-budget curve
queries, plus deterministic relabel/zero-premium/malformed controls. All prior
records remain unchanged. First validate exact root values and certificate
rejection against independent scalar or existing all-budget evidence. Freeze a
fresh performance set/caps only after semantic conformance. Keep every trial,
revision reason, status, timeout and invalid; no performance reruns of unchanged
adverse units. No external publication or author/rights attestation occurs.

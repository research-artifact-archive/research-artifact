# Theorem attribution and certificate checking

This guide links the paper's mathematical results to their inherited foundations and implementation. The numbering refers to the paper snapshot in `package/paper/`; the revised paper retains these theorem numbers. It is a navigation aid, not an additional theorem, an independent review, or a claim of exhaustive literature priority. The full hypotheses and proofs are in the paper. Third-party articles are linked, not redistributed here.

## What each result adds

| Paper result | Inherited foundation | Result that needs the paper's additional argument |
|---|---|---|
| Theorem 5, primitive abstraction | Quantitative synchronization synthesis already includes optimistic retries, guards, and caches. Cerny et al. (2011), Section 4.2, Theorem 6, preserves limit-average values using matching transition distributions and weights. | Initial minimax **total counted-work** equality between this preparation/guard interface and serial retry macros. The potential omits and restores guarded prepared jobs, respects physical readiness, and handles atomic batch validation by an antichain inequality. It does not preserve every intermediate state's value. |
| Theorem 6, actual writes | Java's atomic `compute` contract and the retained OpenJDK implementation supply the callback behavior. | Two separate directions: a zero/one-write adversary maintains the lower-bound potential for admissible foregrounds; emitted serial controllers reread after rejection, allowing failures to be charged to distinct actual writes. The shared-bin argument needs the stated restrictions on callbacks and surviving guards. |
| Equation (2), Bellman recurrence | Mannor et al. (2012), Section 4 and Theorem 5, already provide budget-adaptive robust DP. Substitute the unfinished set, failure budget, negated residual costs, and horizon `n+B`. | The recurrence is a specialization, not a new Bellman principle. It alone establishes neither primitive equality nor a compressed representation for all budgets. |
| Lemma 7 and Theorem 8, reflected curves | Burdzy, Kang, and Ramanan (2009), Theorem 2.6 and the jump projection, supply the reflected recurrence. The slope-floor expression is a concavity specialization. | The retry game's child curves meet the hypotheses: subset monotonicity, cheapest-ready-fast dominance, the lower/upper child relation, and induction over unfinished sets. Extracted actions and eventual saturation also require the game-specific argument. |
| Theorem 10, supporting basis | Bertsimas and Sim (2003), Theorem 3 and Equations (15)-(19), already express a static binary robust objective as a lower envelope with input deviations as slopes. | This causal retry game is closed under protected shifts, integer slope flooring, and minima. Its coefficients use the **integer** maximum of `g(q)-c*q`. The paper also gives the sampled-run bound, tight chain family, coefficient bounds, and aggregate bit complexity. The number of completion ideals remains exponential in general. |
| Theorem 12, prescribed-order persistence | Persistent balanced trees are standard. Chrobak et al. (2009), Lemma 4 and Theorem 5, already avoid numerical fault-budget enumeration for prescribed-order latest completion under a different release/deadline model with mandatory retries. | Four slope ranges, earliest protection thresholds, and shared suffix roots implement this retry/protection objective. The stated arithmetic checking bound applies to **generated certificates** with the proved sharing. Prescribed-order optimality is restricted to that order; unrestricted optimality needs unique order or the separate cost-compatibility argument. |

The source documents and exact locations used for this comparison are:

- [Cerny et al., Quantitative Synthesis for Concurrent Programs](https://arjunradhakrishna.github.io/publications/quant_synth.pdf), Section 4.2, PDF pages 12-13, Theorem 6. The [publication page and erratum](https://www.microsoft.com/en-us/research/publication/quantitative-synthesis-for-concurrent-programs/) supersede the original complexity claim.
- [Cerny et al., Optimizing Solution Quality in Synchronization Synthesis](https://arxiv.org/pdf/1511.07163v1), Sections 6.1-6.2, PDF pages 8-10, already account for protected statements and profiled protection costs. The present artifact uses declared premiums without runtime calibration.
- [Mannor et al., Lightning Does Not Strike Twice](https://icml.cc/2012/papers/215.pdf), Section 4, Theorem 5 and Algorithm 1, PDF pages 4-6.
- [Burdzy, Kang, and Ramanan, The Skorokhod problem in a time-dependent interval](https://userpages.umbc.edu/~wkang/BKR.pdf), Theorem 2.6 and Equation (2.8), printed page 433; Equations (2.12)-(2.13), page 435.
- [Bertsimas and Sim, Robust discrete optimization and network flows](https://web.mit.edu/dbertsim/www/papers/melvyn/Robust-Discrete-Optimization-And-Network-Flows-MP98.pdf), Section 3.1, Theorem 3, Equations (15)-(19), printed pages 56-58.
- [Chrobak et al., Algorithms for Testing Fault-Tolerance of Sequenced Jobs](https://iuuk.mff.cuni.cz/~sgall/ps/faults.pdf), Section 4, Lemma 4, Algorithm 1 and Theorem 5, PDF pages 6-8.
- [Java 17 `ConcurrentHashMap.compute`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html#compute(K,java.util.function.BiFunction)); the paper identifies the retained OpenJDK source revision. Neither source provides the external-write bound or the work prices.

For example, the potential is not an exact intermediate-state quotient: the paper's cached-job example has potential 1 and actual remaining optimum 2. Initial equality instead follows from the lower-bound argument and an attaining serial implementation. Conversely, the bound on writes is not obtained by charging every possible stale rejection to a new write; it uses the emitted controller's fresh reads.

## Persistent checker pseudocode

The implementation is [the shared checker](package/src/fixed_order_profile_03/checker.py), with [structural validation](package/src/fixed_order_profile_02/checker.py). Its construction-independent check relies on the concave cap theorem. It verifies integer data; content hashes are used for provenance elsewhere, not as probabilistic equality tests here.

Let `child(b)` be the child curve's value at budget `b`. Slope positions are one-based: slope `b` is `child(b)-child(b-1)`. Slopes beyond finite support are zero. Empty ranges below require no comparison.

```text
CheckStructure(certificate)
  // Check order, prices, backward references, AVL balance,
  // canonical runs, aggregates, suffix premium totals, and zero terminal root.

for each adjacent suffix pair (own, child), with price (c,p), threshold t:
    if p = 0:
        require t = 0 and support(own) = support(child)
        require ExactEqual(own, child, [1, support(child)])
        continue

    a := number of child slopes at least c
    Delta(q) := c*(q-a) - (child(q)-child(a))
    require t > a and Delta(t-1) < p <= Delta(t)
    z := child(t)-child(t-1) + p-Delta(t-1)
    require 0 < z <= c
    require support(own) = max(support(child), t)

    require ExactEqual(own, child, [1,a])
    require Constant(own, [a+1,t-1], c)
    require Constant(own, [t,t], z)
    if t < support(child):
        require ExactEqual(own, child, [t+1,support(child)])
accept
```

`ExactEqual` decomposes both requested ranges into shared subtrees and integer run fragments. Identical subtree IDs are skipped after structural validation. Run fragments are compared by their slope values, consuming the shorter length. Otherwise the longer subtree front is expanded. Distinct IDs do not imply distinct values. `Constant` checks run values or a subtree's validated minimum and maximum slopes.

The checker accepts different valid sharing layouts. Its soundness for well-formed certificates is separate from the generated-family complexity bound. The [generated-class addendum](package/data/extended/fixed_order_profile_03/GENERATED_CLASS_ADDENDUM.md) supplies the sharing argument for certificates emitted by this constructor. No logarithmic-time guarantee is asserted for every arbitrary valid certificate, and the paper's arithmetic bound is not a unit-cost bit-complexity or elapsed-time guarantee.

Run `python3 -B package/reproduce_latest.py shared --out work/shared-check` to replay the 44,838 retained shared-checker units. This includes 20,758 adversarial certificate inputs with valid metadata: 74 are correctly accepted and 20,684 rejected. Acceptance of these 74 valid variations is intentional. Other stages preserve prior malformed controls and the original scale timeout partitions. Replays check known inputs and do not increase the scientific sample count.

## Which artifact a method returns

| Route or method | Returned object and scope |
|---|---|
| General ideal compiler | All-budget values and policy actions for reachable unfinished sets; exponential state dimension can remain. |
| Cost-compatible packing | A compact all-budget policy whose unrestricted optimality uses cost-compatible precedence. |
| Persistent unique order | Shared suffix curves and thresholds, with unrestricted optimality because there is only one order. |
| Persistent supplied order | The same representation, optimal within the supplied order only. |
| Exact specified-budget CP/DP | A policy for the requested budget; it inherits the primitive/native semantic guarantees when optimal for that game. It need not construct all-budget curves. |
| Direct value oracle | Requested values and local value evidence; it does not emit a complete online policy. |

The [paper-to-artifact map](PAPER_ARTIFACT_MAP.md) identifies construction and checking versions separately, including failed or timed-out earlier versions. A successful later replay does not change those historical outcomes.

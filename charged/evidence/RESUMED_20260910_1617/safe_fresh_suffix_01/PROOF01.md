# A protection-preserving replacement of an all-cached suffix

Author theorem candidate following an ordinary-model proposal of a particular fresh-selection rule on the already observed six-job example. The general invariant and the worst-work domination proof below are separate author contributions; neither follows from the model's reported private calculation or from the bounded checker. This result concerns body work in the visible three-mode interface, without guard-entry/comparison fees.

## Theorem

Fix any finite DAG of n>=1 persistent whole-kernel jobs, positive works w_i, and retry slack r>=0. Let G_k be the sum of the min(max(k,0),n) largest job weights, and Omega(S) the work of unfinished jobs S. Every invocation executes and charges the whole kernel; outputs of completed parents remain immutable, and a cached comparison exposes its match/mismatch Boolean. Before each cheap or cached comparison call, capture the current own-key identity and prepare from that current snapshot; this preparation is immediate, paid, and used for that call. Re-preparing a retained old snapshot is excluded. No program observes the actual write budget.

Fix any deterministic causal cheap controller that selects a ready unfinished job in finite time, prepares it immediately, and calls it cheaply, until either all jobs complete or r failures have occurred. Let C be this cheap controller followed by immediate cached completion of every remaining job in any deterministic ready order. Consider any policy P with exactly the same cheap controller, followed instead by the rule:

* Maintain k, the number of observed cached mismatches since the switch, and ell, the sum of weights of protected completed jobs. The program computes these from its modes, comparison results and known weights; it does not read hidden write/work counters.
* A ready job i may be completed fresh, without preparation, only when

      ell + w_i <= G_k,       ell + Omega(S) <= G_(k+1).       (SF)

* Otherwise use an immediately prepared cached completion. Cached completion may also be chosen when (SF) holds. Choose some ready unfinished job in finite time at every step.

Then P completes under every finite-write environment and, for every B>=0, satisfies

    Q <= n+r,
    sup_(E in E_B) L(P,E) <= G_((B-r)+),
    sup_(E in E_B) W(P,E) <= sup_(E in E_B) W(C,E).

Here E_B consists of environments with an unconditional B-write bound on every play. The last inequality concerns separate worst total work, not a pathwise protected-work ordering between the policies. Existing general lower bounds make P's protected-work curve optimal. The transformation need not attain the least total-work curve on arbitrary DAGs, and (SF) is sufficient, not necessary.

## Proof of call and protected-work guarantees

Each cheap call completes a job or consumes one of r failure slots; each later fresh/cached call completes a ready job. Thus there are at most n+r calls, finite choices and terminating selected operations. The policy completes. Fewer than r failures means completion in the cheap phase with L=0. Reaching the suffix requires at least r actual writes: immediate preparations give disjoint read-to-comparison intervals, and each cheap failure needs a write in its own interval.

In the suffix, each cached mismatch likewise needs a new write in its distinct preparation-to-comparison interval. Therefore at any suffix prefix the actual write count is at least r+k, although k counts only observed cached mismatches. Additional writes do not invalidate this inequality.

Before the first fresh completion, ell is the sum of k distinct cached-mismatch job weights. Consequently ell<=G_k and any new target i satisfies ell+w_i<=G_(k+1). A cached match leaves ell,k unchanged; a mismatch increments k and adds its target's weight. Both preserve the bound.

The first fresh call is permitted only when both inequalities (SF) hold. It gives ell'<=G_k and establishes

    ell' + Omega(S\{i}) = ell + Omega(S) <= G_(k+1).         (I)

After the first fresh call, maintain (I) at every operation boundary. A fresh call increases ell and removes exactly the same weight from Omega(S), so the left side is unchanged; its first guard separately ensures ell'<=G_k. A cached match removes its weight from Omega(S) without increasing ell, so (I) weakens. A cached mismatch increases ell by its weight and removes that weight from Omega(S), while k increases by one; the left side is unchanged and the right side is nondecreasing. Moreover, on that mismatch,

    ell' = ell+w_i <= ell+Omega(S) <= G_(k+1),

which is precisely the new protection bound. Thus no cached branch after a fresh call can violate protection. This also shows that an immediately cached operation is always safe; the rule cannot create a state in which all completing calls violate the cap.

For an execution with at most B writes, either it stays in the cheap phase or r+k<=B and ell<=G_k<=G_((B-r)+). At completion ell=L. This proves all-budget protection without equating the observed count with actual hidden writes.

## Proof of worst total-work domination

Fix any concrete P execution under an environment E in E_B. If it completes before the suffix, C has the identical cheap execution under that same environment and identical work. Otherwise let pi be its complete prefix through the r-th cheap failure. Denote by b0 its actual write count, S its unfinished set, and W0 all work already paid. Importantly, b0 can exceed r because of harmless writes. Do not erase those writes or assume they were unobservable.

Replay this identical prefix against C. The two controllers and their selected operations are identical up to the switch, so the same finite writer actions reproduce the complete prefix, saved outputs, live identities and all paid charges. In the P suffix, let H be the set of cached-mismatch jobs and m=|H|. Every suffix job completes exactly once, with one mandatory kernel and at most one duplicate if its cached call mismatches. No job is prepared before a fresh completion. Thus

    W(P,E) = W0 + Omega(S) + sum_(i in H) w_i,
    m <= B-b0.

Now give C a suffix writer that places one fresh own-key write at the cached comparison of each of the m largest-weight jobs in S, and no other writes. Every target eventually becomes ready and completes: the fixed DAG and persistent completion guarantee this under any ready order. Its immediate preparation is distinct from all earlier preparations and is invalidated by that fresh comparison-gate write. All other cached comparisons match. Therefore the complete C execution costs

    W0 + Omega(S) + Top_m(S) >= W(P,E).

The writer reproduces at most b0 prefix writes and has m one-use target slots afterwards. Stop off the specified common prefix and never spend a suffix slot twice. This makes it unconditionally bounded by b0+m<=B on every play, including deviations; no unbounded writer is truncated after its observed outcome. This proves forall E in E_B, exists E' in E_B with W(C,E')>=W(P,E), and hence the stated supremum inequality. Input-dependent cheap choices and harmless prefix writes are covered by the exact-prefix construction.

## Corollary and an efficient deterministic instance

For independent jobs, use ascending-work cheap order. Taking C as the already-proved least-curve cheap-then-cached policy gives W_P(B)<=F_r(B) for all B. Since P retains simultaneous optimal protection, the existing all-program lower bound gives equality. Thus the replacement preserves the independent-job least entire work curve. It also preserves the corresponding r=0 any-DAG curve when compared to its all-cached baseline.

One deterministic instance is: choose minimum-ready in the cheap phase; at k=0 choose maximum-ready cached; at k>0 choose the maximum-ready job fresh if (SF) holds, and otherwise choose minimum-ready cached. Ties use job index. It uses ready-job queues, the scalar remaining work, k and ell, plus sorted global prefix sums G. It need not construct an exponential policy tree or receive B. Sorting/preparing G takes O(n log n) arithmetic/comparison operations; maintaining readiness and each min/max choice can use O(log n) per call and O(n+|E_DAG|) graph work over completions. These are operation counts, not measured native latency.

The six-job example shows strict improvement over all-cached continuation: at B=7 the baseline has W=782, while this instance has W=752; both have Q<=9 and the same optimal protected curve. This comparison differs from the separate all-program minimum-ready lower766. For the four-job observation example (5,1,1,2),r=1, the instance reduces the plateau from21 to20, using visible cached flags. These are previously observed authored examples, not representative empirical populations.

## Why the second inequality matters

Consider the chain of works(1,1,10),r=0. A cached mismatch on the first job gives k=1,ell=1. Freshly completing the next unit job satisfies only the first inequality, since2<=G_1=10, but violates the second: ell+remainingWork=12>G_2=11. If that fresh call is nevertheless taken, a cached mismatch on the last job gives L=12 at two writes, exceeding G_2=11. This is a finite two-write counterexample to using the current-protection inequality alone. It does not make (SF) necessary for every alternative safe strategy.

## Fixed corroboration

The fixed protocol checks714 roots, including711 small overlapping DAG/weight/retry roots, the two prior positive examples and the deliberately constructed safety-control chain. Every candidate/baseline pair agrees with the unchanged separate operation interpreter and satisfies the same call/protected curves; all22,583 paths are retained. The safe instance improves W strictly on only the two preselected positive examples; all other checked roots have equal curves. Dropping the second inequality detects the predicted L=12>11 violation. Finite agreement neither proves this theorem nor establishes unrestricted DAG total-work optimality. No native measurement, new independent population, human outcome or acceptance claim is made.

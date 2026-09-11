# Author-side complete algebra and model audit: three fixed actual prices

2026-09-11. SCIENTIFIC, narrow author-side audit. Inputs are the exact snapshots bound by FREEZE01.json: PROOF02.md, THREE_COSTS_HYPOTHESIS03.md, filter01.py, and FULLY_CHARGED_PROOF05.md. This is not blind review, a mechanically checked proof, a new run of the earlier positive-p experiments, or paper/public adoption. The separate finite checker is corroboration, not the reasoning establishing the theorem below.

**Finding:** the proposed threshold and both proposed exact mode conditions are correct under the explicitly inherited residual completion interface and 0<=a_i,f_i<=b_i. They extend to zero charges, p=0, p<0, signed normalized incurred cost, ties, and all integer k>=0 algebraically. There is no required change to formulas (A) or (B). The source-price substitution is also correct. The old positive-p implementation does not implement this extension. In particular, the old statement that future p values do not enter must not be copied into the signed-p result: future d=(a-f)+ as well as t=b-max(a,f) are required.

## 1. Exact statement, including actual costs and quantifiers

Let J be a finite DAG, D a completed ideal, and S=J\D. Every remaining job completes exactly once by a sequential, indivisible protected completion call, after current preparation where required. A fresh call costs the fixed actual nonnegative f_i. A cached call costs actual a_i on match and actual b_i on visible mismatch. Assume b_i>=max(a_i,f_i). There are no additional cheap completion calls, retries, partial work, retained guards, or altered comparison fees inside this residual game. Nonprotected preparation work is outside this scalar protected-cost objective. Waiting and other unpriced native costs are not asserted to be zero in software; they are outside these quantities.

Every mismatch requires an own-key write in that call's disjoint current-capture/comparison interval. One fresh-identity write can realize a mismatch at any selected cached call, while no write gives a match. Fresh identities remain available after every finite admissible history, and the fixed-price jobs remain valid under those identities. The policy completes after finitely many choices and is a single causal deterministic policy, not supplied a future write bound. It can choose any ready job and fresh/cached mode and can condition subsequent choices on observed outcomes. Its success requirement covers every nonnegative integer future bound r and every writer whose future writes are unconditionally <=r on every play. We use r for this bound to avoid collision with the mismatch price b_i.

Define A(U)=sum_(i in U)a_i, q_i=b_i-a_i>=0, and the full, actual all-cached benchmark

    B_j = A(J) + Top_j(q_J),        j>=0.

This is the worst actual protected cost of completing all of J cached under a j-write cap: every leaf has a mismatch subset of cardinality <=j and pays exactly A(J) plus its q sum. Conversely, any subset of <=j jobs can be realized by one own-key write at each of those gates along a topological all-cached execution. Since q is nonnegative, its largest feasible subset sum is Top_j(q_J). This reasoning includes q=0 and j>|J|. It neither says that every write causes a mismatch nor says that this benchmark is optimal among all policies.

The residual state's actual incurred charge is lambda>=0 and its physical mismatch count is 0<=k<=|D|. The contract is

    exists ONE completing causal policy P, not given r,
    forall integers r>=0, forall unconditionally r-write-bounded writers:
        lambda + actual future charge <= B_(k+r).

Here k is a cached-mismatch count in the stated interface, not a claim to observe every past write. This is a residual contract. An arbitrary informative global history may supply extra facts and have a weaker obligation; the theorem does not erase them or assert this numerical state is a sufficient statistic for a different global contract. Every physical pair (D,k) is covered, but an arbitrary chosen lambda need not be reachable from the same initial history. Characterizing all reachable prefix costs is unnecessary for a residual threshold.

Let p_i=f_i-a_i, d_i=max(-p_i,0), t_i=b_i-max(a_i,f_i). Set ell=lambda-A(D), which can be negative even on actual reachable histories. The exact state threshold is

    V(D,k)=sum_S d_i + Top_k(q_D union t_S),
    safe iff ell<=V(D,k).

Equivalently, without signed actual costs,

    safe iff lambda<=A(D)+sum_S max(a_i-f_i,0)
                        +Top_k((b_i-a_i)_(i in D) union
                               (b_i-max(a_i,f_i))_(i in S)).

All multisets include their zero entries and multiplicities. The algebraic formula also holds for surplus integer k>=0; surplus k is not assigned a physical write interpretation.

For a proposed ready i define X_i=q_D union t_(S\{i}) and R_i=sum_(j in S\{i})d_j. The exact root mode permissions are

    cached i: ell <= R_i+Top_k(X_i),
    fresh i:  ell <= R_i+Top_k(X_i union {q_i})-p_i.

For every ready i, the maximum of those two thresholds equals V(D,k). Thus every ready-order choice has a safe mode from a viable state, including an adaptively selected ready order. This does not establish equal work or time for those choices, and the readiness relation itself must still be respected.

## 2. Why the actual benchmark and signed normalization are equivalent

Each remaining job appears once on a complete leaf. Subtracting a_i from the cost of that one call gives increments 0 on cached match, p_i on fresh, and q_i on cached mismatch. Therefore on every leaf

    lambda + actual future cost
      = A(J) + ell + normalized future cost.

Subtracting the same A(J) from both sides of the actual benchmark inequality gives exactly ell+normalized_future<=Top_(k+r)(q_J). No cost is omitted from the actual total. In particular, the baseline is A(J), not only A(D), when translating the whole benchmark; the state offset is A(D) only because future calls contribute their own baseline once.

This identity is valid for negative p and negative ell. Lambda and each actual call price remain nonnegative. Physically admissible lambda corresponds to ell>=-A(D); no clamping of ell to zero is justified. Restricting to actual lambda>=0 simply intersects the theorem's algebraic half-line with that domain. A forced mode may have a negative actual-prefix threshold and hence be unavailable for every nonnegative lambda; clamping such a threshold to zero would wrongly permit lambda=0.

## 3. Complete-policy-tree reduction without supplied budgets

For a fixed deterministic completing policy, restrict writers to no write at fresh calls, and at cached calls either no write or one fresh-identity write. Fix canonical admissible identities and timings for those choices. Even a value- or history-dependent policy then induces a finite full tree, of depth |S| completion calls, with one child at fresh nodes and two outcome children at cached nodes. Different branches can have different continuation policies; they are not merged on a numerical state.

A leaf containing c future mismatches and actual future cost T can be reproduced using exactly c writes. To turn it into an admissible environment, fix the corresponding causal sequence of gate writes and enforce a physical counter cap c on every play; on any off-path behavior it may suppress writes. Gate mode/job choices suffice; the writer need not inspect private policy state. That capped writer reproduces the selected leaf against the fixed policy. Thus the universal contract implies

    lambda+T <= B_(k+c)

for every leaf of that restricted tree. This implication uses r=c separately for each selected leaf against the SAME policy, not a family of policies told different r values.

Conversely, construct a policy depending only on ready jobs and visible abstract outcomes. Any actual execution maps to one of its full-tree leaves with c mismatches. Disjoint own-key intervals imply c<=r for an r-write-bounded environment, including harmless or extra writes. B is nondecreasing because q>=0. Its leaf inequality at B_(k+c) therefore implies the required inequality at B_(k+r). This proves both sides of the tree reduction under the model assumptions.

Equivalently, for an abstract policy P with leaves L(P), its exact permissible actual-prefix limit is

    M(P)=min_(leaf l in L(P)) [B_(k+c_l)-T_l].

There are finitely many abstract policy trees for a finite DAG. The exact state limit is max_P M(P), and an exact forced-root-mode limit is the same maximum restricted to that root job and mode. These maxima are attained. Necessity for arbitrary history-dependent policies follows by the restricted-writer construction above, not by assuming they were already abstract. Sufficiency follows by selecting an attaining abstract policy. These are the direct objects enumerated by the independent actual-price checker.

## 4. Recurrence derived from policy completion

At S empty, the normalized threshold is Top_k(q_J). For ready i, a fresh call incurs p_i and leaves k unchanged. A cached call has a matching successor with increment 0 and a mismatching successor with increment q_i and count k+1. Thus

    V(D,k)=max_ready_i max(
        V(D+i,k)-p_i,
        min(V(D+i,k), V(D+i,k+1)-q_i)).

The two cached continuations may differ by the observed Boolean but must each handle all remaining bounds. No future bound is supplied in this recurrence. A fresh choice costing less than a cached match merely makes p_i negative; it does not change completion depth or the quantifiers. For necessity, if the chosen root is above its threshold, select a violating child and continue to a terminal violating leaf. The capped writer realizes it. For sufficiency, choose threshold-preserving children until the finite DAG is completed. This is a proof of the recurrence's model correspondence, separate from numerical evaluation.

## 5. Local identities, with all boundary cases

Let X have m nonnegative entries. Write C_k=Top_k(X), H_k=Top_k(X union {q}), q>=0. Then for every integer k>=0,

    min(H_k, H_(k+1)-q)=C_k.                         (L1)

For k=0, H_0=C_0=0 and H_1>=q, including q=0 or empty X. For 1<=k<=m, let tau be X's kth-largest value. If q<=tau, H_k=C_k and the union contains the old top k plus q, so H_(k+1)>=C_k+q. If q>tau, H_(k+1)=C_k+q and H_k=C_k+q-tau>=C_k. This proves (L1), including ties and zero tau. For k>m both H terms equal sum(X)+q, giving C_k=sum(X). Multiplicity, zero values and ties require no tie-breaking assumption.

Suppose also p<=q (equivalently b>=f), and define d=max(-p,0), t=q-max(p,0). Here t=b-max(a,f)>=0. We claim

    max(H_k-p,C_k)=d+Top_k(X union {t}).             (L2)

If p<0, H_k>=C_k and -p>0. Fresh strictly dominates cached, so the left side is -p+H_k. Since d=-p and t=q, this is the right side, for every k including zero and saturation. If p=0, the same calculation with weak domination gives H_k on both sides, d=0 and t=q.

For p>0, put h=q-p>=0, so d=0 and t=h. At k=0, max(-p,0)=0=Top_0(X union {h}). At 1<=k<=m,

    H_k = C_k+max(0,q-tau),
    max(H_k-p,C_k)
      = C_k+max(0,max(0,q-tau)-p)
      = C_k+max(0,q-p-tau)
      = Top_k(X union {h}).

The middle equality uses p>=0. At k>m, the left side is max(sum(X)+q-p,sum(X))=sum(X)+h. This equals the right side. These arguments hold over arbitrary real nonnegative actual prices; they are not an inference from integer testing.

The hypothesis p<=q matters in the p>0 branch because h must be nonnegative for this exact expression. Together with q>=0 these are exactly the two relevant inequalities furnished by b>=max(a,f). The result makes no extension to b<a or b<f.

## 6. Induction solving the recurrence and both mode limits

The terminal formula is V(J,k)=Top_k(q_J). Assume the formula at states with fewer remaining jobs. For ready i, both successors' completed/future multiset is X_i union {q_i}, and their common savings term is R_i. Hence the cached threshold is

    min(R_i+H_k, R_i+H_(k+1)-q_i)
      = R_i+C_k

by (L1). Fresh has threshold R_i+H_k-p_i. By (L2), the maximum of these two limits is

    R_i+d_i+Top_k(X_i union {t_i})
      = sum_S d_i+Top_k(q_D union t_S).

It is independent of the selected ready i. Every nonterminal finite DAG has a ready job, so backward induction proves the threshold, the exact forced-root-mode permissions, and per-ready-job availability simultaneously. An inequality that is strictly exceeded gives a violating complete leaf for every policy; equality is safe because all inequalities are nonstrict and the finite maxima are attained.

## 7. Edge cases and interpretation restrictions

- **Zero q:** b=a and the assumption forces f<=a. Thus p<=0 and t=0. A cached mismatch still increments k: it consumes a write even if it adds no charge beyond a match. Its two future k values may have different allowances on other jobs; (L1) handles this exactly. Do not infer a mismatch count from charged cost.
- **All zero prices:** every cost and threshold is zero; all actual nonnegative prefix states are viable only at lambda=0. Both modes complete, so zero cost introduces no nontermination or Zeno issue in the finite-call model.
- **f=a:** p=d=0, t=q. Fresh weakly dominates cached in threshold; at k=0 they tie. At k>0 equality is not required because a possible cached mismatch can consume budget against remaining costs.
- **f<a:** p<0, t=q, d=a-f. Fresh strictly dominates the cached threshold for each fixed ready i, yet cached may still be safe sufficiently below its limit. A viable state can require fresh.
- **b=f>=a:** t=0. The positive-p branch remains valid, including equality at the kth multiset entry. With f=a=b this also has q=0.
- **k=0:** V=sum_S d. With all f>=a this becomes zero as before. With some f<a, future guaranteed savings can support positive ell. Each cached-i limit is the savings in the OTHER remaining jobs; its own savings are available only by choosing it fresh.
- **Terminal and saturation:** S empty gives ell<=Top_k(q_J). For k>=|J| the benchmark saturates at sum_J b_i. Since d_i+t_i=b_i-f_i, the state formula becomes lambda<=sum_J b_i-sum_S f_i, attained by all-fresh future completion. Surplus k is an algebraic check only. The finite checker covers all physical k plus benchmark budgets through n+2; the analytic proof covers all larger k and budgets.
- **Future information:** edges do not enter the scalar threshold, but determine readiness. The signed result requires future d and t. It does not inherit the positive-p claim that future body/normalized-fresh costs are irrelevant. Fixed actual prices, a fixed job set and once-per-job baseline subtraction are essential.
- **All-budget residual safety:** this is one scalar all-cached comparison curve. It gives no optimal total-work frontier, no best ready order for latency, and no supplied-one-write joint-resource optimality.

## 8. Source-shaped prices w,g,c and relation to the other charged proof

With w_i>0, g_i>=0, c_i>=0, assign

    a_i=g_i+c_i,
    f_i=g_i+w_i,
    b_i=g_i+c_i+w_i.

This is the fixed per-protected-call pricing in FULLY_CHARGED_PROOF05: a guarded cached call pays the guard and comparison on either outcome, and a bad outcome also pays the whole protected body; fresh pays the guard and whole protected body. Then

    q_i=w_i, p_i=w_i-c_i,
    d_i=max(c_i-w_i,0), t_i=min(c_i,w_i).

Substituting into the proven actual threshold gives exactly

    lambda <= sum_D(g_i+c_i)+sum_S max(c_i-w_i,0)
              +Top_k(w_D union min(c_i,w_i)_S),

against the ACTUAL benchmark

    sum_J(g_i+c_i)+Top_(k+r)(w_J).

All guard and cached comparison charges are retained. When c_i>w_i, fresh is cheaper than even a matching cached call: this is a valid fixed-price input, not an invalid negative actual cost. When c_i=w_i, p_i=0 and the fresh/match actual costs tie. When every w_i>c_i, the positive-p theorem applies with p=w-c and h=c, within its other assumptions. A common c strictly below every w gives the old completed-only region, but with ell=lambda-sum_D(g+c), not the unadjusted body-only predicate.

This substitution imports per-call prices only. FULLY_CHARGED_PROOF05 supplies B=1, optimizes a joint (total,protected) frontier, permits a cheap suffix after detecting the sole write, and accounts for charged preparation work in its total coordinate. The present residual theorem supplies no B, admits no such cheap suffix, and compares only protected costs with one fixed benchmark. It therefore does not contradict the supplied-B frontier or its NP-completeness. It is not a derivation of the residual policy class from that frontier theorem. Prices here are supplied constants, not native runtime measurements; source calibration and usefulness remain separate work.

## 9. Exact current-implementation gap and two reachable witnesses

The frozen filter01.py enforces integer body>=1 in limits, integer incurred>=0 at construction, and completed q>=1. Its body parameter represents positive normalized p, not generally the actual whole-body w. It changes the future heap value h to h+p and increments incurred by p or p+h. Consequently it does not cover p=0, p<0, q=0, signed ell, or the actual-baseline bookkeeping in this extension. Merely feeding w into it while ignoring c would implement a different predicate. No implementation test of this file is part of this task.

A correct extension would need to track R=sum_future d, future t/completed q, and signed ell (or the equivalent actual lambda and completed A). Completing i removes d_i from R and replaces its heap value t_i with q_i; the value increase is q_i-t_i=max(p_i,0), not always p_i. Fresh adds p_i to ell, cached match adds zero, and cached mismatch adds q_i while incrementing k even if q_i=0. These are derivation notes, not an implementation claim or edits to the old filter.

Two analytical witnesses use only frozen price types and a two-job chain, so their game states are included in attempt01; they were selected for explanation after the run and are not additional trials:

1. Job0 P1=(a,f,b)=(1,2,3), then job1 N1=(3,1,4). Choose job0 fresh. At D={0}, k=0, lambda=2, ell=1. V=2, cached-job1 threshold is 0 in normalized units, and fresh-job1 threshold is 2. Thus the state is viable and only fresh is safe. Actual fresh completion totals 3 versus no-write all-cached benchmark A(J)=4; cached match would already total 5>4. The initial fresh choice is itself safe because the future N1 savings cover it. This shows why every cached action cannot remain permitted throughout the enlarged region. Frozen game844 has actual state/cached/fresh limits 3/1/3, read back in READBACK01.json.

2. Reverse the two types along the chain and choose N1 fresh first. Then lambda=1, A(D)=3, ell=-2, k=0. Remaining P1 has normalized fresh threshold -1, so fresh is safe and ends at actual total 3<=A(J)=4. Clamping ell to zero would incorrectly forbid that fresh action. The old constructor rejects incurred=-2, confirming that its declared API excludes this valid actual history. Frozen game718 has actual state/cached/fresh limits 3/3/2, read back in READBACK01.json. Both games' independently enumerated actual benchmark curves are 4,6,7 and then remain 7.

## 10. Separate finite evidence and audit limits

Attempt01's evaluator enumerates every cached mismatch subset to construct the ACTUAL all-cached curve and every actual completion leaf of every structural policy tree; it does not use the candidate normalization, Top expression, old filter, or a value-function recurrence. Formula comparisons occur only after each game's full raw is written and flushed. The fixed code and actual population precede the sole run. There are 157,465 state games, 1,934,433 policy evaluations, 7,964,521 leaves, 247,312 ready-job/mode thresholds, and 943,459 benchmark comparisons. Every frozen input completed; disagreement, invalid, timeout and not-run counts are zero. Prefix-boundary checking includes 190,965 negative-ell probes among 685,077 actual-prefix probes. These are correlated finite synthetic checks, not independent workload samples, arbitrary retained-record programs, or a proof over real prices.

The analytic audit above is the evidence for the general algebra and model correspondence. Its validity depends on the explicit fixed-price and gate assumptions; it does not prove a source implementation meets them. The author-side checker is independently constructed from actual costs but shares the author's hypotheses and context, so neither it nor this audit is a blind independent scientific review. Root alone decides subsequent paper and artifact adoption. No prior unfavorable result, proof version, or positive-p validation count has been changed.

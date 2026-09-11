# Author check of two direct monotone-objective extensions

**Both (A) and (B) are supported**, taking the completed audit's full-program corner lower and `A_r subset V_r` membership as premises. No repeat audit of those foundations, new experiment, old run replay, external-model call or delegation was performed. The only proof wording adjustment is to express (A)'s tied-weight step with a weight order statistic, rather than an arbitrary fixed label rank.

The work-only part of (A) is **already explicit** in `residual_safety_01/PROOF02.md`, line 64. Its extension to every monotone joint preference uses the supported corner lower and the stronger per-play accounting below. (B)'s equal-weight work formula was already noted for independent jobs in preserved project discussion; the selected old proofs do not explicitly state every-caller/all-DAG/all-monotone exactness. Both should be presented as local consequences of existing proofs, without discovery or significance promotion.

`INPUT.json` freezes ten source files. References below use its IDs. I01 is corrected DERIVATION03; I03/I04 are the completed audit/report receipt, treated as premises. I05 is frozen manuscript232, consulted only for definitions and the residual filter. Current main/public files are untouched. This is an author-side analytical check with inherited context, not blind review or formal verification.

## A. Ascending cheap phase with every permitted filtered suffix

Fix independent jobs with positive weights `a_1<=...<=a_n`, total `Omega`, maximum `M`, and `T_s` the sum of the `s` heaviest weights. Fix any one `A in A_r` whose cheap phase chooses a minimum-weight unfinished job, retries it until completion or the global `r` failures, and then uses any causal, finitely selected ready fresh/cached actions admitted by the exact body filter. Ties among minimum-weight jobs may be broken arbitrarily, including from the observed history. The same caller is used at every budget and for every objective.

For `B>r`, put `m=min(B-r,n)` and define the existing corners

```
v_s = (Omega+r*a_(n-s+1)+T_s, T_s, n+r),   1<=s<=m.
```

First suppose `r>0` and a concrete execution switches to the suffix. Let `h` be the weight of the job at the last failed cheap call, and `s` the number of actual cached mismatches in the completed suffix.

If `s>=1`, all failed cheap preparations have weights at most `h`, because the cheap phase advances in nondecreasing weight. Each of the `s` distinct mismatching jobs was unfinished at the switch, and every such job has weight at least `h`. Therefore the entire instance has at least `s` weights at least `h`, which implies

```
h <= a_(n-s+1).
```

This is tie-safe. The literal index inequality `j<=n-s+1` requires choosing a tie order consistent with the realized cheap prefix; it need not hold for arbitrary preassigned job labels. The weight inequality above is all the proof needs.

Let `H` be the set of actual cached-mismatch jobs. Exact caller accounting and the final filter invariant give, on this same execution,

```
W = Omega + failed-preparation work + sum_(i in H) w_i
  <= Omega + r*h + T_s,
L = ell <= Top_s(D_final) = T_s,
Q = n+r.
```

Here `D_final=J` and the filter counter is `k=s`, the actual mismatch count. In contrast to an all-cached suffix, `L` need not equal `sum_H w_i`: safe fresh jobs may contribute protected work too. The filter invariant bounds **all** of it. Fresh bodies are counted once in mandatory `Omega`; they incur no discarded preparation because `A_r` prepares only before cheap/cached calls. This is the crucial valid replacement of the earlier all-cached equality.

The `r` failed cheap calls and the `s` cached mismatches have disjoint current-capture/comparison intervals, each containing a write, so `r+s<=B`. Thus `1<=s<=m`, and the whole concrete resource vector is dominated by `v_s`.

The remaining cases are covered as follows:

| Case | Same-play bound | Corner domination |
|---|---|---|
| Switched, `s=0` | Filter gives `L<=Top_0(J)=0`; `W<=Omega+r*M`, `Q=n+r` | Dominated by `v_1` when `B>r` |
| Completes before `r` failures | With `f<r`, `W<=Omega+f*M`, `L=0`, `Q=n+f` | Dominated by `v_1` when `B>r` |
| `B<=r` | At most `B` cheap failures. If switched, no mismatch remains possible, and the filter permits no positive fresh work. Vector at most `(Omega+B*M,0,n+B)` | The inherited early corner |
| `r=0` | Skip the nonexistent last failed call. Every `A_0` play on every DAG is bounded by `(Omega+T_min(B,n),T_min(B,n),n)` | This is the largest existing corner for `B>0`; at `B=0` use `(Omega,0,n)` |

For every fixed competitor `P in V_r` and every permitted `s`, the inherited target-`s` construction gives **one complete execution** at budget at most `r+s<=B` with resource vector at least `v_s`. For the early range it supplies the corresponding early corner. These premises apply to the full comparator, including retained records and paid early preparations; the comparator has not been reduced to `A_r` or to ascending policies.

Consequently, for every coordinatewise nondecreasing real-valued `Phi`, monotonicity applied to the concrete upper and each same-execution lower proves

```
sup_(E in E_B) Phi(A,E)
 = inf_(P in V_r) sup_(E in E_B) Phi(P,E)
 = Phi(Omega+B*M,0,n+B),                         B<=r;
 = max_(1<=s<=m) Phi(v_s),                       B>r.
```

No equality between a joint supremum and separate coordinate suprema is used. Different corners can require different environments; the lower's quantifiers are `for every P, for every s, there exists E_(P,s)`. That is sufficient, and no common adverse environment for all policies is required. Continuity or convexity of `Phi` is unnecessary. Each such caller is a common optimizer for all budgets and all preferences; the claim is not about arbitrary full programs in `V_r` being optimal.

Sources: I01 independent monotone statement; I02 caller accounting/membership; I03 same-execution lower and zero-retry conclusions; I05 residual invariant and caller definition, lines 209–266; I10 lines 44–64.

## B. Equal-weight jobs on any DAG, every caller

Let every job have the same positive weight `w`. No cheap-order restriction is needed. For `B>r`, `m=min(B-r,n)` and every concrete `A_r` play is dominated by

```
u_m = ((n+r+m)*w, m*w, n+r).
```

Indeed, a switched play with `s<=m` mismatches has `r` failed preparations, each of work `w`, and `s` duplicate cached kernels. Hence `W=(n+r+s)*w<=u_m.W`. The filter gives `L<=s*w<=m*w`, and `Q=n+r`. A play completing in the cheap phase has `f<r` failures and vector `((n+f)*w,0,n+f)`, also dominated by `u_m`.

There is an additional useful simplification: **no fresh completion is actually permitted at any reachable equal-weight suffix state**. At the switch `ell=k*w=0`. A cached match preserves this equality, and a mismatch increments both sides by `w`. Since physical states satisfy `k<=|D|`, a proposed fresh action would require

```
ell+w <= Top_k(D union {i}) = k*w,
```

contradicting `ell=k*w` and `w>0`. Inductively every reachable suffix action is cached, and `L=s*w` exactly. Thus the nominal fresh/cached freedom does not hide an extra protected-work case here. This observation is specific to the equal-weight, zero-initial-slack body filter used in `A_r`; it is not a statement about arbitrary initialized residual states or charged variants.

For the full general-program comparator, choose any `m` jobs as the heaviest targets; all ties have equal work. The inherited DAG-valid target lower forces on one complete execution

```
W >= n*w+r*w+T_m = (n+r+m)*w,
L = T_m = m*w,
Q = n+r.
```

The upper and this simultaneous lower agree at `u_m`. Readiness may postpone targets but cannot remove their completion obligations; independence is not used. An early-budget full-program lower likewise forces `((n+B)*w,0,n+B)` for `B<=r`. Therefore, at **every** budget, every `A_r` caller is optimal for every monotone joint preference, with the convenient single-corner expression

```
u(B) = ((n+min(B,n+r))*w,
        min(max(B-r,0),n)*w,
        n+min(B,r)),

sup_E Phi(A,E) = inf_(P in V_r) sup_E Phi(P,E) = Phi(u(B)).
```

This includes `B=0`, `r=0`, `n=1`, `B=r`, and saturation at `B>=n+r`. For `r=0`, the value reduces to the already-supported all-DAG `A_0` result. If completion occurs before the retry limit on some other execution, its smaller vector does not change the worst value.

For an explicit caller-side attaining execution, fail its first `min(B,r)` cheap calls. If `B<r`, stop writing; all further current-prepared comparisons match. If `B>=r`, mismatch the first `m` cached completions and then stop. Arbitrary readiness choices still terminate and every paid unit has weight `w`. The writer has an unconditional cap `min(B,r)+m`, using `m=0` in the early case. Thus it attains `u(B)` for each particular caller; it is not merely a coordinatewise ceiling. This direct witness complements, rather than substitutes for, the inherited lower against the full `V_r` class.

## Local overlap and presentation

| Earlier source | What was already stated | Scope of the present consequence |
|---|---|---|
| I10 `residual_safety_01/PROOF02.md`, lines 62–64 | Every permitted filtered suffix with ascending cheap order preserves the independent least **W** curve; any ready suffix choices; also `r=0` on DAGs | (A)'s work-only part is an explicit duplicate. The joint-`Phi` statement exposes the already-available vector argument. |
| I08 `safe_fresh_suffix_01/PROOF01.md`, corollary section | Ascending cheap order plus an earlier sufficient fresh rule preserves the independent work curve | Earlier, narrower policy class; no all-joint-preference theorem stated there. |
| I06 `UNIVERSAL_INDEPENDENT_PROOF10.md` | Independent exact work curve and its corner witnesses | Supplies the lower and the equal-weight specialization. |
| I09 preserved `CLAUDE_UNIVERSAL07_RAW.md`, line 69 | Uniform independent weights collapse the work formula to `Omega+min(B,n+r)*w` for `B>r` | This value was already noticed. It does not explicitly state arbitrary-DAG/every-caller/all-`Phi` optimality. This is cached historical text, not a new model consultation or independent proof source. |
| I02 DAG `PROOF02.md`; I05 manuscript232 work theorem | General-DAG all-caller upper; full-program target lower; exact early budgets and `r=0` | Equal weights make the existing upper/lower coincide. (B) is an immediate homogeneous-instance consequence, not a new algorithm. |
| I01 corrected DERIVATION03; I03 completed audit | All-cached ascending monotone optimum and every-caller `r=0` monotone optimum | These foundations were accepted for this bounded assignment and not re-audited. |

The focused searches and their complete outputs are saved as `LOCAL_SEARCH01.json` and `LOCAL_SEARCH02.json`, including an unsuccessful navigation lookup. The exact (A)/(B) all-monotone assertions were not found explicitly in the selected older sources. This limited wording comparison is not a claim of exhaustive archival or public-literature novelty.

For a short paper corollary, the two conditions can be stated together: every caller with ascending cheap phase on independent jobs, and every caller on an equal-weight DAG, attains the full-contract optimum for every monotone joint resource objective at every budget. Use (J) for the former and `u(B)` for the latter, and cite the existing target lower and filter invariant. If space only permits a work-only sentence, (A) must retain its existing provenance. No stronger FSE importance, native effect, or positive-retry exact result for general unequal-weight DAGs follows.

No numerical computation was necessary. All verification here is direct algebra and comparison of the specified proof fragments; no new finite oracle, timing study or previous-run execution was performed. Exact input hashes and cessation of this audit are recorded in `STOP.json`.

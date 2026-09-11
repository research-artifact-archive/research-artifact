# Author audit: monotone joint objectives and the priced caller factor

**Verdict:** DERIVATION02's two mathematical conclusions are supported under its unchanged whole-kernel model and full universal-contract comparator. I found no substantive counterexample or missing inequality. The all-program lower witnesses really do co-realize the needed coordinates; the proof does not add unrelated worst cases. The early-budget correction from `Q=n+B` to `Q>=n+B` is sufficient and necessary as a general statement. The proof should route `r=0` separately before referring to a last cheap failure. The sharpness argument requires the stated scaling when the fixed call price is positive.

**Project lineage:** the independent-job monotone theorem is a direct corollary of the already-preserved proof10's corner witnesses and ascending accounting. It should not be described as a newly discovered policy, adversary, or independent mechanism. The selected prior files do not state the exact all-`Phi` formula or price-dependent `beta` explicitly. The scalar theorem is an algebraic priced extension of the current all-caller work theorem, using that inherited corner structure. This bounded comparison does not establish literature novelty or strong FSE significance.

This is a separate author-side reasoning check with inherited project context, **not blind review**, formal verification, or a new experiment. Scope: only this directory. `INPUT.json` freezes source bytes; citations below use its input IDs and line numbers. The target is I02 (`DERIVATION02.md`), with I01 preserving its predecessor. Manuscript232 is I11 and was read only for its contract and related proof, not reviewed as a whole.

## 1. Same complete execution for every general program

Fix `P in V_r`, `B>r`, and `1<=s<=min(B-r,n)`. Target the `s` heaviest jobs. At a selected target comparison, write a fresh own-key identity exactly when that call's zero-write continuation would match. Write nowhere else. Count useful cheap failures `f`, useful cached mismatches `c`, and all target completions `t`; stop writing permanently at `f=r+1` or `t=s`.

This is unconditionally capped, without borrowing admissibility to establish the environment budget. At completed-call boundaries `d=f+c` and `c<=t`. Before a next useful write, `f<=r` and `t<=s-1`, so `d+1<=f+t+1<=r+s`. A selected target call cannot escape invalidation by choosing another retained record after the write: the identity is fresh to the whole pre-gate store. Already-stale comparisons consume no useful write.

For an admissible `P`, `r+1` failed calls are impossible because completion requires another `n` completing calls. Since the environment has a finite global cap, every target eventually completes, including on a DAG whose predecessors delay it. Before the final target completion, a target cannot complete by a matching comparison. Thus all targets complete protectively and `L>=T_s`.

Now cap this environment at the realized final write count `d`. This preserves the complete execution, and the all-budget protection promise applies to **that same execution**:

```
T_s <= L <= T_max(d-r,0),      d=f+c <= r+s.
```

Since every job weight is positive, `T_k<T_s` for `k<s`, even with tied weights and even when `s=n`. Hence `d=r+s`, `f=r`, and `c=s`. Consequently:

* `L=T_s`: the upper cap and the target lower agree. There is no extra positive protected work outside these targets.
* `Q=n+r`: the `n` mandatory completing calls and the `r` useful failures exhaust the cap. Additional stale cheap failures are excluded on this complete witness.
* `W>=Omega+r*a_(n-s+1)+T_s`: the existing charging injection assigns a distinct, already-paid counterfactual matching preparation to each useful invalidation, and a separate mandatory completing invocation to every job. Retention, post-gate selection and early preparation cannot erase a charged invocation.

These are simultaneous facts of one finite execution for this `P,s`. The witness can depend on `P,s`; a single environment common to all programs or all corners is neither claimed nor needed. Its budget is `r+s<=B`. Sources: I04 lines 29–50; I06 lines 5–41; I11 lines 115–132, 162–196.

For `0<B<=r`, use the maximum-job `s=1` witness and stop writes **after the completed call** containing its `B`th useful write. All those writes caused cheap failures before the target completes. The preserved prefix has destroyed `B` distinct paid maximum-job preparations. Its eventual completion needs a separate mandatory invocation. The truncated environment is globally `B`-capped; therefore on its completed execution:

```
W >= Omega+B*M,       L=0,       n+B <= Q <= n+r.
```

After truncation, a general program may waste remaining allowance on already-stale cheap failures. The equality in DERIVATION01 was therefore stronger than justified; DERIVATION02 correctly needs only the lower inequality. At `B=0`, the empty-write environment gives `W>=Omega`, `L=0`, `Q>=n`, again sufficient. Nothing requires separate environments for these three coordinates. Sources: I02 line 21; I04 early-budget section; I05 per-play/prefix capping; I11 lines 196–198.

## 2. Ascending concrete plays are dominated by attainable corners

Fix independent jobs and the same ascending policy `P*`, configured with `r` but supplied with neither `B` nor `Phi`. It retries the current job on a cheap failure and starts all-cached completion after exactly `r` failures.

For `B<=r`, every completed play has at most `B` cheap failures, no protected work, and

```
(W,L,Q) <= (Omega+B*M, 0, n+B).
```

Matching all smaller jobs, failing the largest job `B` times, then stopping writes attains this corner. At `B=r`, the final completion is cached and matching; its preparation is the mandatory completion work, not an additional failed preparation.

For `B>r` and `r>0`, a switched play with `s>=1` cached mismatches has last cheap-failure rank `j`. All failed preparations have weights at most `a_j`. Each mismatching job lies in the unfinished suffix `j,...,n`; the existence of `s` such jobs implies `j<=n-s+1`. Hence the **entire vector**, rather than separate extrema, satisfies

```
(W,L,Q) <= v_s := (Omega+r*a_(n-s+1)+T_s, T_s, n+r).
```

The `r` cheap failures and these `s` mismatches need disjoint capture/comparison intervals containing writes, so `s<=B-r` and `s<=n`. Wasted or invisible writes do not weaken this upper bound. All-cached means `L` is exactly the sum of mismatching works on this concrete play.

The two omitted-looking cases are harmless. A switched play with zero mismatches has vector at most `(Omega+r*M,0,n+r)`. A play completing before the switch has `f<r` failures and vector at most `(Omega+f*M,0,n+f)`. Both are dominated by `v_1=(Omega+(r+1)*M,M,n+r)`, which exists whenever `B>r`.

Each `v_s` is itself attainable by `P*`: match the first `n-s` jobs, fail the next job `r` times, then mismatch all `s` remaining cached completions. This is a finite `r+s`-write execution. Thus the corners are not fictional combinations of separate maxima.

For `r=0`, there is no last cheap-failure rank. Handle this before that argument: `P*` is all-cached from the start, and all its vectors are dominated by `(Omega+T_m,T_m,n)`, attained by mismatching the `m=min(B,n)` heaviest jobs. At `B=0`, use `(Omega,0,n)`. More generally **every** `A_0` caller on **every** DAG has `Q=n`, `L<=T_m`, and `W<=Omega+T_m`, including callers making permitted fresh completions. The all-program target witness forces the same corner. The stated all-`Phi` exactness for every `A_0` therefore follows.

For any coordinatewise nondecreasing real-valued `Phi`, every `P*` play is below one corner; for every competitor `P`, each corner is below one of `P`'s complete executions at the same budget bound. Apply `Phi` in those inequalities and then take suprema. The finite maximum of the corners is an upper bound for `P*` and a lower bound for every `P`; hence it is the minimum and `P*` is a common attainer for all `B,Phi`. No continuity, convexity, probability distribution, or exchange of `inf` and `sup` is used. A competitor's supremum may be `+infinity` despite finite cost on each play; this does not affect the argument or the finite value attained by `P*`.

This is a statement about worst joint preferences, not a pointwise comparison of two policies in the same environment, nor a claim that one execution maximizes all three coordinates. Sources: I02 lines 9–23; I04 upper/witness and lower sections; I11 lines 173–201.

## 3. Scalar theorem and endpoints

Assume fixed **finite** `lambda,gamma>=0` and put `theta=1+lambda>=1`. Nonnegative coefficients are used both in the per-play bound and in applying the lower vector. The denominator is positive because mandatory work `Omega>0` is charged.

For `B>r`, the actual operation identity for an `A_r` play is

```
W = Omega + failed-preparation work + cached-mismatch work.
L = fresh protected work + cached-mismatch work.
Q = n + number of cheap failures.
```

Therefore `C=W+lambda*L+gamma*Q <= Omega+gamma*(n+r)+r*M+theta*T_m`. In particular fresh completions cause no missing body term: their one body belongs to `Omega`; their extra priced contribution is `lambda` times their protected work. They are bounded along with the mismatch contribution by `theta*L<=theta*T_m`. Adding separate upper bounds is legitimate here; the argument does not assert that their peaks co-occur.

The **same-execution** target lower gives, for every full general program,

```
sup C >= Omega+gamma*(n+r)
         + max_{1<=s<=m} (r*a_(n-s+1)+theta*T_s).
```

Taking its infimum retains this lower bound. It is at least the same baseline plus `max((r+theta)*M,theta*T_m)`. Let `x=T_m/M>=1` and `z=(Omega+gamma*(n+r))/M>=x`. The ratio is bounded by

```
R(z,x) = (z+r+theta*x)/(z+max(r+theta,theta*x)).
```

Its derivative in `z` is nonpositive: the numerator's added term is at least either possible denominator term. At `z=x`, the first branch has derivative

```
theta*(r+theta+1)/(x+r+theta)^2 > 0,
```

and the second branch is `1+r/((theta+1)*x)`, nonincreasing, strictly decreasing when `r>0`. They meet at `x=(r+theta)/theta`, giving exactly

```
beta_(r,theta) = 1 + r*theta/((theta+1)*(theta+r)).
```

For `B<=r`, the common value is `Omega+B*M+gamma*(n+B)`. For `B=r+1`, the sole corner has `W=Omega+(r+1)*M`, `L=M`, `Q=n+r`, matching the all-caller upper. These establish exactness for all callers through `B=r+1`. The preceding zero-retry argument establishes exactness at every budget for `r=0`; the formula also gives `beta=1` there. Setting `lambda=gamma=0` recovers the work-only `alpha_r`, and `r=1,lambda=1` gives `11/9`.

The price-dependent factor need not improve on the work-only factor as `lambda` grows: for fixed `r`, the added fraction has derivative with sign `r-theta^2`. It increases up to `theta=sqrt(r)` when that lies in the domain, then decreases. Accordingly the work-only uniform bound below `3/2` must not be carried over to arbitrary priced objectives. No negative-price, variable-price, nonlinear-approximation, randomized-policy, or elapsed-time result is inferred.

## 4. Sharpness and scaling

For fixed integer `r>=1`, real `theta>=1`, and finite `gamma>=0`, take independent descending weights `w_j=t*q^(j-1)`, `q=r/(r+theta)`. Define a causal caller that processes jobs in that order, retrying its current cheap job until the total failure count reaches `r`, then uses only cached completions. It is a member of `A_r` on every history, not merely on the adverse path; all-cached continuation preserves the filter invariant.

At `B=n+r`, an unconditionally capped environment can fail its first job `r` times and mismatch all `n` cached completions. It gives the simultaneous vector `(2*Omega+r*t,Omega,n+r)` and scalar cost `(theta+1)*Omega+r*t+gamma*(n+r)`. The per-play upper supplies equality for this caller's worst scalar cost.

For every `s`, the finite geometric identity is

```
r*w_s+theta*T_s
 = r*t*q^(s-1)+(r+theta)*t*(1-q^s)
 = (r+theta)*t.
```

The independent monotone theorem therefore makes the **full `V_r` optimum** exactly `Omega+t*(r+theta)+gamma*(n+r)`. Dividing by `t`, write `o_n=Omega/t` and `g_n=gamma*(n+r)/t`. The ratio is

```
((theta+1)*o_n+r+g_n)/(o_n+r+theta+g_n).
```

Choose the explicit sequence `t_n=n^2*(1+gamma)`. Then `g_n->0` for fixed `r,gamma` and `o_n->(r+theta)/theta`; the ratio tends to `beta`. This is sharpness as a supremum over finite instances and permitted callers, not finite-instance equality or a lower bound on the best constructor. Independent ascending order remains optimal on these witnesses.

Keeping `t` fixed with positive `gamma` instead makes call costs dominate as `n` grows and the ratio tends to one. Thus the scaling qualification is material and DERIVATION02 includes the needed repair. For `gamma=0`, fixed positive `t` is enough. The stated model admits positive real works, so irrational `theta` causes no gap. Clearing denominators gives integer works for rational `theta` with a suitable rational scale; rationality of `gamma` is not actually necessary for that limited observation. No exact geometric integer construction for irrational `theta` is claimed or required. If a later theorem insists on integer inputs for all real prices, it needs a separately stated rational-approximation argument.

## 5. Related project results and contribution status

| Frozen input | Relevant existing content | Relationship to this derivation |
|---|---|---|
| I04: `UNIVERSAL_INDEPENDENT_PROOF10.md`, upper/witness and full-program lower sections | Exactly the ascending `s`-corner executions; globally capped target construction forcing `f=r,c=s`; separate work/protection maxima explicitly distinguished | Already supplies the mathematical substance for the monotone corollary. The new presentation exposes their joint vector implication. Do not count it as rediscovery of these results. |
| I14: `UNIVERSAL_INDEPENDENT_DRAFT09.md` | Earlier version of the same corner strategy and target construction | Confirms the lineage predates this task. Its early-budget uncertainty is superseded by the preserved corrected proof, not silently erased. |
| I06: general-r `PROOF02.md`, contract and realization sections | For each canonical-tree play, one full-program execution componentwise dominates `Q,W,L`, uniformly in budget | Already implies preservation for monotone functions under that reduction. It does not itself select one ascending tree optimal for every preference. Its frontier recurrence stores separate peaks and must not be used as a joint-cost oracle without additional justification. |
| I05: `UNIVERSAL_SCOPE_PROOF11.md` | Realized-play/prefix capping, early DAG work equalities, and the later chain counterexample | Supplies the exact capping premise and the boundary on removing independence; no positive-retry exact DAG optimum is established here. |
| I07 and I15: `ANALYTIC_DRAFT01.md`, `INDEPENDENT_PROOF07.md` | Earlier strict-call and supplied-budget joint `W/L` frontiers; separate worst coordinates may have distinct witnesses | Different admissible class and objective. They do not directly supply the present unknown-budget common-policy statement. |
| I08, I12, I13: charged-comparison/guard-only proofs | Mode-dependent guard/validation fees and supplied-budget Pareto results; some lower/upper pairs co-occur on a no-write execution | Co-occurrence reasoning is already used in the project. Those prices and changing protection contracts are not the present fixed `W+lambda*L+gamma*Q` objective; do not import their frontier complexity or native fee interpretation. |
| I03: DAG `PROOF02.md`; I11: manuscript232 Sections 4–5 | Current `alpha_r`, full-program lower, all-caller accounting and geometric sharpness | `beta` extends this same proof with a price parameter. It is not a second independent algorithmic mechanism. |

The exact all-`Phi` formula and `beta_(r,theta)` were not located in these selected pre-derivation texts. This is a bounded local comparison, not an exhaustive archive or public-source novelty search. `LOCAL_COMPARISON_SEARCH.json` saves the focused queries and their full outputs. Strong novelty, significance, native demand and manuscript adoption remain separate decisions for root.

## 6. Saved arithmetic and actionable notes

Nine declared examples were evaluated once using exact rational arithmetic. `ARITHMETIC_INPUT.json` predates the calculation; `ARITHMETIC_OUTPUT.json` retains all inputs, weights, corner vectors, costs, geometric terms and rational outputs. All five geometric examples satisfy their displayed constant-term identities and upper factors. These computations check algebraic illustrations only; no policies were enumerated, native programs executed, or old evaluation stages rerun.

The correlation example uses independent works `(1,100)`, `r=1`, `B=3`. Its attainable corners are `(301,100,3)` and `(203,101,3)`. With `lambda=1,gamma=0`, the true joint optimum is `max(401,304)=401`, whereas adding separate peaks gives `301+101=402`. With `lambda=100,gamma=2`, the second corner is worst and the true value is `10309`; adding separate peaks gives `10407`. The same ascending policy remains optimal. Even the discontinuous monotone function `1[W>=301 and L>=101]` is zero at both corners but one at their coordinatewise maximum. This makes the joint statement meaningful while demonstrating why separate resource curves alone do not prove it.

Before any adoption, only these local exposition points need attention:

1. Route `r=0` before I02 line 19's last-failed-call index; handle `B=0` with its early corner. In line 53 use “nonincreasing,” or restrict strict decrease to `r>0`.
2. Keep `Q>=n+B` in the arbitrary-program early lower; equality belongs to the ascending attainer, not every competing program.
3. State finite nonnegative prices and the explicit scaling sequence for positive `gamma`. Keep sharpness over the full caller class, not minimum-ready or a fixed normalized workload.
4. Present the monotone result as a consequence of the existing vector witnesses and `beta` as the priced extension of the current theorem. No new-discovery or importance promotion follows from this audit.

No substantive theorem repair, additional experiment, new public-source investigation, or original-proof edit was needed within this audit. All original files and adverse historical records remain untouched. Completion time, input verification and the absence of active audit processes are recorded in `STOP.json`.

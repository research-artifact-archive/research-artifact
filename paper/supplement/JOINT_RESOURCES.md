# Joint resource objectives and exact classes

This analytical supplement derives consequences of the manuscript's existing vector witnesses and caller accounting. It is separate from the manuscript's numbered theorems and the 60 fixed-evidence replay stages. The policy mechanism and underlying lower-bound construction are inherited from this project. These consequences do not establish a new native workload, elapsed-time guarantee, independent literature novelty, or submission readiness.

## Model and inherited proof obligations

Use the exact whole-kernel interface, full program class `V_r`, and immediate-preparation filtered caller class `A_r` of the [caller-work proof](../../charged/evidence/RESUMED_20260911_1123/dag_approximation_01/PROOF02.md). Every program in `V_r` must complete against every finite-budget environment and meet **both** `Q <= n+r` and `L <= T_max(B-r,0)` simultaneously at every unknown integer write budget `B`. Retained records, free inspections and paid early preparations remain in the full comparator. The caller subclass prepares exactly once immediately before each cheap/cached call and never before fresh; after `r` cheap failures, it uses only completing modes permitted by the residual filter.

There are `n>=1` jobs of positive real body works `w_i`; `r>=0` is an integer. Write `Omega=sum_i w_i`, `M=max_i w_i`, ascending weights `a_1<=...<=a_n`, and `T_s` for the sum of the `s` heaviest works, saturated at `n`, with `T_0=0`. `W` is all executed body work, `L` its protected part, and `Q` logical completion calls. None counts elapsed time or arbitrary native guard fees.

The [independent-job proof10](../../charged/evidence/RESUMED_20260910_1617/joint_work_general_r_01/UNIVERSAL_INDEPENDENT_PROOF10.md), [scope proof11](../../charged/evidence/RESUMED_20260910_1617/joint_work_general_r_01/UNIVERSAL_SCOPE_PROOF11.md), and current caller-work proof supply the following **co-occurring** lower vector on every DAG. For every full `P in V_r`, every `B>r` and `1<=s<=m=min(B-r,n)`, one complete, unconditionally `(r+s)`-capped execution satisfies

```
W >= Omega + r*a_(n-s+1) + T_s,   L = T_s,   Q = n+r.       (1)
```

For clarity, the existing construction targets the `s` heaviest jobs and freshly invalidates only target comparisons whose zero-write continuation would match. Let `f` count useful cheap failures, `c` useful cached mismatches and `t` all target completions. Stop writing at `f=r+1` or `t=s`. Before another useful write, `d+1<=f+t+1<=r+s`, so the cap is unconditional, even for inadmissible programs. A valid program cannot reach `f=r+1`, and all targets eventually complete protectively. Capping the realized complete execution at its own final count `d=f+c` gives `T_s<=L<=T_max(d-r,0)`. Positivity forces `d=r+s`, `f=r`, `c=s`; these targets exhaust protected work and the `r` failures exhaust spare calls. The existing distinct-charge injection counts the mandatory work, all target duplicate kernels and `r` distinct paid failed preparations, proving (1). Fresh identities invalidate the full pre-gate store. Dependencies delay readiness but cannot prevent target completion in a valid program. No separate worst cases are added.

For `B<=r`, the completed-call truncation of the maximum-job construction gives one complete execution with

```
W >= Omega+B*M,   L=0,   Q>=n+B.                            (2)
```

The inequality in (2) suffices below. In fact the witness has equality in `Q`: in the early range the universal zero-protection contract prevents total failures exceeding actual writes. Otherwise a prefix with `d<=r` writes and `F>d` failures could be followed by fresh invalidations up to total `r`; protection would be forbidden, forcing more than `r` failures before completion. At `B=0`, mandatory work and calls suffice. An earlier analytical draft's suggestion that extra stale failures could make (2) strict on this witness was withdrawn; all predecessor drafts remain preserved in the author archive.

For every `A_r` execution, operation accounting is

```
W = Omega + failed-preparation work + cached-mismatch work,
L = fresh protected work + cached-mismatch work,
Q = n + cheap failures.                                   (3)
```

The residual filter's final invariant is `L<=T_s` when the suffix has `s` cached mismatches. It includes safe fresh completions in `L`.

## A common optimum for every monotone joint objective

Let `Phi` be any coordinatewise nondecreasing real-valued function on nonnegative `(W,L,Q)` vectors. Policies receive neither `Phi` nor `B`. On independent jobs, **every caller with ascending cheap order, retrying its current job until completion or the global `r` failures, followed by any permitted filtered suffix**, minimizes

```
inf_(P in V_r) sup_(E in E_B) Phi(W(P,E),L(P,E),Q(P,E)).
```

For `B<=r` its value is `Phi(Omega+B*M,0,n+B)`. For `B>r` its value is

```
max_(1<=s<=m) Phi(v_s),
v_s = (Omega+r*a_(n-s+1)+T_s, T_s, n+r).                   (4)
```

**Proof.** First assume `r>0`, and consider a switched play with `s>=1` cached mismatches. Let `h` be the weight at the last failed cheap call. All failed preparations weigh at most `h`; every still-unfinished job weighs at least `h`. In particular the instance has at least `s` weights at least `h`, so `h<=a_(n-s+1)`. This uses weight order statistics and allows arbitrary tie breaking among minimum-weight unfinished jobs. Equations (3) and the final filter invariant give `(W,L,Q)<=v_s`. The `r` cheap failures and `s` mismatches require disjoint writes, giving `s<=m`. With zero mismatches the filter permits no positive protected work; that play is dominated by `v_1`. Plays completing before `r` failures also are dominated by `v_1`. Early budgets satisfy `(W,L,Q)<=(Omega+B*M,0,n+B)`.

At `r=0`, no last failed rank is defined: every filtered caller's vector is at most `(Omega+T_m,T_m,n)`, with `m=min(B,n)`. This is the largest corner; at `B=0` use `(Omega,0,n)`. Lower vectors (1)–(2) hold for every full comparator, including the proposed caller itself. Applying monotonicity to each concrete upper and lower vector proves (4), and that each stated caller is a common minimizer for all `B,Phi`. No continuity, convexity, probability distribution, or exchange of infimum and supremum is needed. A general comparator may have an infinite supremum; the displayed finite value is attained by the stated callers. This is worst-case optimality, not pointwise domination on the same environment.

The all-cached suffix is one member, and its corner plays are explicit: match the first `n-s` jobs, fail the next cheap call `r` times, then mismatch all `s` remaining cached completions. The extension to any filtered suffix uses the final invariant, including its fresh costs; it does not assume fresh is free.

**Equal-work DAGs.** On any DAG with `w_i=w>0` for all jobs, **every** `A_r` caller, including arbitrary cheap order, is optimal for every such `Phi` at every budget. For `B>r`, its entire vector is bounded by `(n*w+(r+m)*w,m*w,n+r)`. Lower witness (1) with `s=m` forces this same corner for every full program. Early budgets use (2). Equivalently the single corner is `((n+min(B,n+r))*w, min(max(B-r,0),n)*w, n+min(B,r))`. From the standard zero-slack initialization, fresh is never permitted here: induction gives `ell=k*w`, while a fresh request would require `ell+w<=k*w`. Thus equal-work exactness does not demonstrate a fresh-mode advantage. This is an exact restricted class, not an exact positive-retry solution for arbitrary heterogeneous DAGs. At `r=0`, all callers are exact on every DAG even with heterogeneous works.

**Why joint vectors matter.** Works `(1,100)`, `r=1`, `B=3` give corners `(301,100,3)` and `(203,101,3)`. For `W+L`, the optimum is `max(401,304)=401`; adding separate resource peaks gives `402`. For `W+100L+2Q`, the second corner wins at `10309`. The monotone discontinuous function `1[W>=301 and L>=101]` is zero on both corners but one on their coordinatewise maximum. Separate optimal resource curves alone therefore do not prove (4).

## A sharp priced bound on arbitrary DAGs

Fix finite real prices `lambda,gamma>=0`, put `theta=1+lambda`, and charge each **concrete execution**

```
C = W+lambda*L+gamma*Q.
```

Let `C_A(B)=sup_E C(A,E)` and `F_C,J(B)=inf_(P in V_r) sup_E C(P,E)`. For every `A in A_r`, every finite DAG and every `B`,

```
C_A(B) <= beta_(r,theta) * F_C,J(B),
beta_(r,theta) = 1 + r*theta / ((theta+1)*(theta+r)).        (5)
```

Every caller is exact for `B<=r+1`; at `r=0` every budget is exact. At `lambda=gamma=0`, (5) is the manuscript's work-only factor. At `r=1,lambda=1`, it gives `11/9`.

**Upper and lower bounds.** For `B>r`, (3) and filter safety give the concrete upper

```
C <= Omega+gamma*(n+r)+r*M+theta*T_m.
```

Fresh bodies are already in mandatory `Omega`; their additional priced protection is included by `theta*L`. Applying prices to each same-execution lower (1) gives

```
F_C,J(B) >= Omega+gamma*(n+r)
             + max_(1<=s<=m) [r*a_(n-s+1)+theta*T_s].
```

The maximum is at least `max((r+theta)*M,theta*T_m)`. Put `x=T_m/M>=1` and `z=(Omega+gamma*(n+r))/M>=x`. Their ratio is at most

```
(z+r+theta*x)/(z+max(r+theta,theta*x)).
```

It is nonincreasing in `z`. At `z=x`, the branch before `x=(r+theta)/theta` increases, with derivative `theta*(r+theta+1)/(x+r+theta)^2`; the later branch is `1+r/((theta+1)*x)`, nonincreasing. The meeting value is (5). For `m=1` the original upper and lower coincide; at `B<=r` both give `Omega+B*M+gamma*(n+B)`.

**Sharpness.** Fix `r>=1,theta>=1,gamma>=0`. On independent descending weights `w_j=t*q^(j-1)`, `q=r/(r+theta)`, use a caller that retries its current job until completion or global `r` failures, then caches every remaining job. At `B=n+r`, failing the first job `r` times and mismatching all `n` suffix completions attains its upper cost

```
(theta+1)*Omega+r*t+gamma*(n+r).
```

For every `s`, `r*w_s+theta*T_s=t*(r+theta)`, so (4) gives full optimum `Omega+t*(r+theta)+gamma*(n+r)`. Choose `t_n=n^2*(1+gamma)`. Then `gamma*(n+r)/t_n -> 0` and `Omega/t_n -> (r+theta)/theta`, so the ratio tends to (5). Sharpness is a supremum over finite instances and permitted callers, not finite-instance equality or tightness for minimum-ready scheduling. At positive `gamma`, keeping `t` fixed would instead yield limit one; scaling is essential. Positive real works are allowed. Rational `theta` allows integer scaling; no exact integer geometric construction for irrational `theta` is claimed.

The price-dependent factor need not improve monotonically with `lambda`. Its added term increases up to `theta=sqrt(r)` when that lies in the domain, then decreases. For example `r=4,theta=2` gives `13/9`, larger than the work-only `7/5`. Do not extend the work-only uniform bound below `3/2` to arbitrary prices. Negative prices, nonlinear approximation factors, randomness, and arbitrary mode-dependent native fees are outside (5).

## Evidence and lineage

The independent all-cached result is a corollary of proof10's vector witnesses. The work-only ascending-cheap/any-filtered-suffix statement was already explicit in this project's residual-safety proof02; its all-monotone formulation uses the joint vector bound. Equal-work DAG exactness is a direct coincidence of the existing upper and lower bounds. These are further characterizations of the same interface, not rediscovered work-only results. Equation (5) extends the existing caller-work argument by scalar prices; it is not a separate synchronization mechanism. Author-side checks and a conditional model check concern these logical consequences, not human evaluation, formal certification, or public-literature novelty. Their exact scope and hashes are recorded in the accompanying supplement manifest.

The nine saved [arithmetic inputs](ARITHMETIC_INPUT.json) and [outputs](ARITHMETIC_OUTPUT.json) check displayed expressions only. They include the joint-correlation diagnostic, early/zero-retry cases, finite geometric equality, a positive-call-price scaling example, and a price that worsens the work-only factor. They are neither a policy enumeration nor new native measurements. No 61st standard replay stage is claimed. The earlier 60-stage proof/code/trace payload remains unchanged; its public replay receipt retains its original immutable evidence commit.

To replay only the nine algebraic examples with Python3.10+ and an empty output path:

```sh
python3 -I -S -B paper/supplement/reproduce_arithmetic.py --out work/joint-arithmetic
```

The wrapper copies the unchanged original checker and input into the new directory, runs once, and requires every saved output field to match except the completion timestamp. It does not enumerate new policies or repeat native measurements.

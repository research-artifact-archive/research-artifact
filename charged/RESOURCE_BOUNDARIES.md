# Resource boundaries and independent-job price bound

This extension reports source-event resource counts, separate from the failed timing-to-fee calibration preserved elsewhere in this artifact. It does not measure throughput, user benefit, lock waiting, latency, or actual monetary charges. All inputs and full original outcomes remain in nine study directories under `evidence/RESUMED_20260909_0056/`: the six price/resource studies below and `charged_budget_blind_native_01`, plus two explicitly post-outcome work analyses. A portable replay checks those records without declaring new evaluation samples.

## Protected work under a completion-call cap

Use the paper's causal interface: private current-key reads, cheap identity-based validation, fresh computation inside an atomic callback, and cached computation reused or recomputed inside an atomic callback. Each call can complete at most one job. There is no retained guard across calls, callback spanning several jobs, outside completion, or reuse of an identity by external writes. At most B writes occur; unused writes are allowed. All jobs must complete in every permitted environment. Dependencies may form any DAG.

Here each job's w_i is mandatory kernel work on every input, including when called inside protection; it is not merely an upper bound. W counts all selected kernel work, L the portion inside atomic callbacks, and Q the foreground completion/validation API calls, including failed conditional calls. Q excludes read-only gets, initialization and external-writer calls. Let Omega_k be the sum of the k largest w_i, Omega_0=0, and Omega=Omega_n.

For integer B,r >= 0, under Q <= n+r on every execution, the minimum worst L is

```
three modes: Omega_min(max(B-r,0),n)
two modes:   0 if B <= r, otherwise Omega
```

Upper bound: when B <= r, fresh cheap attempts suffice. Their disjoint read-to-validation intervals charge each failure to a distinct write. Otherwise use cheap attempts until r failures, then cached-complete every remaining job. At most B-r writes remain, and each cached failure completes one job while paying its work inside protection. Protecting every job gives the two-mode upper bound.

Lower bound for two modes when B>r: reject every cheap call with a fresh own-key write, and stop writing after the (r+1)st rejection. This environment uses at most r+1 <= B writes. A program obeying the call cap cannot reach r+1 noncompleting calls, so all its jobs complete under protection.

For three modes when B>r, target the k=min(B-r,n) largest jobs; for B<=r the lower bound L>=0 is immediate. Reject their cheap calls and invalidate preparations for their cached calls with fresh own-key writes just before comparison. A fresh protected callback already incurs the target work inside protection. Stop writing after r+1 target cheap rejections. Before any next write, there can be at most r such rejections and k-1 cached target completions, so that write consumes at most r+k <= B writes. An admissible program cannot incur r+1 noncompleting calls. Thus every target completes with its kernel inside protection. Fresh identities invalidate all retained preparations; inspections and prior callbacks do not retain a guard across this boundary.

For equal works and B>r the two-/three-mode ratio is n/min(B-r,n), reaching n when r=B-1. At r=0, all-cached execution additionally has Q=n and W <= Omega+Omega_min(B,n). These statements concern Q versus worst L, not a full three-dimensional Pareto frontier. A scalar-cost-minimizing policy constrained to Q=n need not minimize L: the preserved decreasing five-job chain at kappa=0, B=1 has L=48 for `qn_three`, versus 40 for `cached_all`.

Optimistic retries and starvation fallback are established mechanisms. Kung and Robinson, *On Optimistic Methods for Concurrency Control*, ACM TODS 6(2), 1981, DOI [10.1145/319566.319567](https://doi.org/10.1145/319566.319567), section 3.3 p.220, describes retaining a critical-section semaphore during restart after starvation. This artifact does not claim to invent that mechanism. Likewise, sorting the largest deviations under an integer uncertainty budget is established in budgeted robust optimization. The contribution asserted here is the exact interface-specific all-program boundary and its relation to the charged policy compiler; its broader importance remains a research question.

## One policy for every writer budget

The resource policy need not receive B or any price or work weight. Fix r>=0 and let U_j(r) be the j-mode programs that receive no B and complete all jobs with Q<=n+r in **every finite-write environment**. Define their pointwise worst protected work as

```
U_j(B,r) = inf_(P in U_j(r)) sup_(E with at most B writes) L(P,E).
U_3(B,r) = Omega_min(max(B-r,0),n)
U_2(B,r) = 0 if B<r, otherwise Omega.
```

One policy in each class attains these values simultaneously for all B and all positive mandatory works on any DAG. Choose any ready job, using a fresh read and cheap attempt; count failed cheap calls globally. After r such failures, use cached completion (three modes) or fresh protected completion (two modes) for every remaining job. Successful cheap attempts do not consume the allowance; for r=0 switch immediately. Every cached completion starts with a fresh own-input read and preparation, including immediately after the rth cheap failure; it does not reuse that failed preparation. The rule has no budget, weight or fee input. Completion consumes n calls and each cheap failure consumes one extra, giving Q<=n+r in all environments. At B<r no protected work is needed. At B=r, cached callbacks after switching cannot mismatch and still have L=0. For B>r the preceding upper bound applies; its three-mode lower bound remains valid on the restricted class of universal policies.

For the two-mode lower bound at B>=r, invalidate every cheap comparison with a fresh own-key write until r cheap rejections have occurred, then stop. Before this, all completing jobs use protection. Write s for completed jobs and f for noncompleting calls. The call allowance remaining is `(n-s)+(r-f)`. At f=r each future call must complete: if the program instead makes a rejectable call, a different finite environment can insert one further write and violate Q<=n+r. That hypothetical additional write rules out a policy choice; **it is not included in the lower-bound execution**, which uses at most r<=B writes. Therefore every job completes under protection. At r=0 even the quiet execution requires all-protected completion in two modes. Retained preparations and free inspections do not prevent a fresh write immediately before comparison; no completed call retains a guard.

This is simultaneous pointwise minimax optimality, not per-execution optimality or a full W,L,Q Pareto frontier. The two-mode class is defined by behavior: failure does not complete a prepared job within the same call. A method that validates and recomputes on mismatch is cached completion even if its API name also permits other modes. All foreground conditional/publication and callback calls count toward Q, including noncompleting calls. Whole mandatory kernels, persistent completion, eventual foreground scheduling/operation completion, no cross-job callbacks, no retained guard, no outside completion and no free certificate of future writer absence remain necessary.

The native selector stores only a cloned dependency array, a mode-family boolean and a remaining cheap-failure allowance. `choose(mask)` and `failedCheap()` are its only policy operations. The writer fixture, assertions and cost-ceiling oracle retain B, but no B, Input, writer, fee table or weights are passed to the selector. All 17,714 original native runs are retained, including 256 exhaustive groups at B=r. These finite tests and the recorded bytecode inspection support the implementation; the universal quantifiers rely on the proof above. Scalar-price minimax compilation elsewhere still uses a supplied B.

## Total work of the universal policy

The [full r=0 proof](evidence/RESUMED_20260909_0056/charged_universal_work_01/THEORY.md) establishes a cost of simultaneous protection optimality. Among universal three-mode programs with Q<=n whose worst L is optimal for **every** writer budget, the minimum worst W at B is `Omega+Omega_min(B,n)`. All-cached attains this for every B. The lower-bound adversary targets the largest jobs, inserting a fresh write before a target's first counted call exactly when that job has already executed its whole kernel. If h<k writes sufficed to force the k target kernels inside, the all-budget protection guarantee at t=h would be contradicted. Thus each target must have paid both a prior kernel and a protected kernel. No initial preparations, mandatory whole kernels and the single-job call interface are essential.

Unknown B alone does not imply this W cost: the full proof gives a B-unaware two-job counterpolicy with Q=2 and worst (W,L)=(32,16) at B=1, but L=16 at B=0. All-cached has worst (40,16) at B=1 and L=0 at B=0. The counterpolicy is a mathematical construction; the retained native comparison separately uses the known-B scalar policy with the same B=1 maxima.

The [fixed-policy proof for every r](evidence/RESUMED_20260909_0056/charged_universal_work_02/THEORY.md) characterizes the implemented rule that retries its current job until completion before advancing in a fixed topological order pi. Put M_i=max work in the prefix through i and S_i=the suffix including i. In both mode families Qmax=n+min(B,r). Two-mode Wmax is `Omega+min(B,r)*wmax`. Three-mode Wmax is `Omega+Top_B(all works)` at r=0, `Omega+B*wmax` at r>=1,B<=r, and

```
Omega + max_i [(r-1)*M_i + w_pi_i + Top_(B-r)(S_i)]
```

at r>=1,B>r. These are component maxima of this policy, not all-program W optimality for r>0 or a scalar/Pareto frontier. All 1,280 complete finite path groups and 17,200 already-observed records match the formulas; there are zero new measurements. The earlier r=0 analysis checks its full subset of160groups/1,632records. Both original analysis plans and the subsequent proofs are preserved with their chronology.

## Sharp scalar ratio for independent jobs

Let k_i=g_i+r_i, c_i=w_i+min(v_i,k_i), delta_i=k_i-min(v_i,k_i), P_i=p_i+delta_i, and A=sum c_i. Write F_2,F_3 for the exact excess values of the original two and three modes. For independent jobs, arbitrary nonnegative fees and premiums, and any integer B>=0,

```
(A+F_2(B))/(A+F_3(B)) <= (1+sqrt(2))/2.
```

This is a supremum. Equivalently the supremum relative total-cost saving is 3-2sqrt(2), about 17.16%. No corresponding bound is asserted for arbitrary dependency DAGs.

Proof outline: set X=F_2(B), Y=F_3(B). Assigning private integer failure budgets yields D(B)=max_(sum b_i<=B) sum min(P_i,b_i*c_i) <= Y, valid also when delta_i>0. A protected completion pays P_i excess, a cached mismatch pays P_i+w_i, and exhausting a private budget with cheap failures pays b_i*c_i. The paper's normal form carries this bound to its full causal interface.

Pack two-mode premiums in reverse sorted-c order and label every contribution by its job. Each final unit column containing job i has height at most c_i, because later caps are no larger. If x_i is that job's mass in the first B columns, sum x_i=X, 0<=x_i<=P_i, and sum x_i/c_i<=B. The last inequality follows column by column: dividing each label mass by its own cap gives a sum no greater than total mass divided by column height, which is one.

Let phi_i interpolate min(P_i,b*c_i) at integer b. Its nonincreasing unit slopes give max_(z_i>=0,sum z_i<=B) sum phi_i(z_i)=D(B): take the B largest slopes, preserving tied prefixes. Do not impose an additional z_i<=P_i/c_i constraint in this maximization; a terminal fractional slope can require a whole integer budget slot. For z_i=x_i/c_i=m_i+rho_i <= P_i/c_i, with integer m_i>=0 and 0<=rho_i<1, phi_i(z_i)>=c_i*(m_i+rho_i^2). Set alpha=sqrt(2)-1. The identity

```
m+rho^2-2*alpha*(m+rho)+alpha^2
  = m*(1-2*alpha)+(rho-alpha)^2 >= 0
```

implies Y>=2*alpha*X-alpha^2*A. Since 1-alpha^2=2*alpha, the ratio follows.

For sharpness take n=M^2 equal independent jobs, w=1, v=k=M, p=floor(alpha*M), and B=ceil(n*p/(M+1)). Their excesses are min(n*p,B*(M+1)) and min(n*p,B*(p+1)); the total-cost ratio tends to the stated bound. The finite study retains all seven family inputs, up to 65,536 jobs. Its largest observed ratio is about 1.20545, below the limiting constant.

## Evidence and replay scope

| Study | Preserved denominator and scope |
|---|---|
| `charged_price_bound_01` | 13,295 direct cases, 172,835 budget roots, seven growing equal-job families and 42 family queries. Original inputs, outcomes and large family artifacts are retained. |
| `charged_price_bound_02` | 622 bases at three uniform integer scales, hence 1,866 cases, 24,378 direct roots and 3,732 huge-budget tail queries. Includes positive-delta positive-premium cases outside the compact condition; 630 compact and 1,236 fallback outcomes. |
| `charged_resource_frontier_01` | 5,421 weight/DAG inputs, 265,629 pairs of budget and call slack. Checks the finite original-mode recurrence, not an all-program proof by testing. |
| `charged_resource_vector_native_01` | 96 policy/shape/price cases, 2,440 ordinary Java runs plus two native controls, 576 exhaustive replay groups. Counters W,L,Q and scalar cost are checked separately. |
| `charged_resource_vector_recheck_02` | A later strict input-class check of all 96 tables and aggregation of 2,442 saved verification decisions, with an explicit old-checker counterexample and five aggregation controls. It was not a native rerun. The public worker additionally regenerates causal checks from the raw records. |
| `charged_resource_frontier_native_01` | 128 cases, 9,312 ordinary Java runs plus two native controls, 1,024 exhaustive replay groups. Every group reaches the formula's L bound while obeying its Q cap. Native budgets are restricted to 0..3; no native constant-tail claim. |
| `charged_universal_work_01` | Post-outcome r=0 analysis: all160groups/1,632original path records and two retained known-B comparison pairs. No new measurements. |
| `charged_universal_work_02` | Post-outcome fixed-policy W,L,Q analysis: all1,280groups/17,200original path records. No new measurements. |
| `charged_budget_blind_native_01` | 128 cases, 17,200 complete-path replays, 512 concurrent runs and two native controls, 1,280 exhaustive groups; all attain the universal formula. Selector receives no B, price or table. Oracle budgets0..4 and remaining cheap-failure allowance0..3; 256 groups at B=r establish the finite boundary contrast. |

Each native study has eight record-corruption, five sequence-certificate and four parser controls. Source jobs use p=w, common v=k=kappa in {0,2}, g=0, and two to five jobs. The Java kernel performs eight elementary work units per declared w, so the checked linear metric is W+L+8*kappa*Q. Maxima of W,L,Q may occur on different executions: their separately maximized weighted sum must not be mistaken for the maximum scalar cost.

The old vector checker omitted a standalone input-class guard, although all actual fixed inputs belonged to the intended class. The preserved one-job out-of-class example shows why its claimed constant tail cannot be used universally. The strict check rejects that input and also refuses to treat unrelated resource failures, timeouts, wrong rejection layers or wrong reasons as the intended native negative control. No original code, outcome or failure was replaced.

Run from the repository root:

```sh
python3 charged/reproduce.py price-bounds --out work/price-bounds
python3 charged/reproduce.py resource-frontier --out work/resource-frontier
python3 charged/reproduce.py resource-vector --out work/resource-vector
python3 charged/reproduce.py resource-frontier-native --out work/resource-frontier-native
python3 charged/reproduce.py budget-blind --out work/budget-blind
python3 charged/reproduce.py universal-work --out work/universal-work
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py resource-vector-java --out work/resource-vector-java
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py resource-frontier-java --out work/resource-frontier-java
JAVA_BIN=java JAVAC_BIN=javac python3 charged/reproduce.py budget-blind-java --out work/budget-blind-java
```

The optional Java commands require JDK17, generate new replay records and independently reconstruct their causal certificates. The fixed corruption controls remain tied to the original records. Standard replay checks the complete fixed inputs and original measurements; it does not rerun timing campaigns. `--quick` only checks a subset and is not full reproduction. Private author correspondence and generated classes/caches are omitted and listed in provenance. Historical manifests retain original source hashes and projected paths; the public provenance binds every distributed byte and the portable entrypoints.

Two fixed study documents refer to omitted private author proof-check correspondence. Those historical references are retained as provenance, not as public evidence dependencies; the public proofs are in the manuscript and this guide. Automated author checks are not independent blind review.

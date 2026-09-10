# Joint frontiers with nonzero guarded completion costs

This is the second author proof version, following the first fixed corroboration and Cost10 criticism. The first version, inputs, run and raw criticisms remain unchanged. They extend the manuscript's explicitly bounded operation class. W is body work; L is its protected part. Every guarded completing call for job i pays a nonnegative fixed g_i under protection, including matching cached completion. Cheap publication pays no such guarded charge. Let Gamma=sum_i g_i and P_g=L+sum_guarded g_i. Waiting is outside this work model. Guards remain confined to a single completing call, every call completes at most one job, input identities can be freshly invalidated at the selected operation's gate, and no partial kernels or outside completion are available. All works w_i are positive, all computed initialization is charged, and the exact observation contract is unchanged.

## Explicit operation and adversary contract

Programs are deterministic. Their two objective coordinates take separate pathwise suprema over admitted environments and initial inputs; expected randomized costs are outside this theorem. Each whole kernel execution necessarily costs exactly w_i, independent of its inputs, not merely at most w_i. Its computed record contains the exact live own-key identity read and completed predecessor outputs. The charged common start supplies no free computed records. Inspections and local record choices do not complete jobs or protect kernels.

Each job needs its own completing call; a call completes at most one job. Cheap publication compares a saved record and either completes on a match or counts as one unsuccessful call. Fresh completion executes the kernel and completes under its guard. Cached completion compares under its guard and, within that same single counted call, either reuses the matching record or executes the kernel and completes on mismatch. The guard is released at return. The cached comparison is exact, with no spurious mismatch. Its Boolean result is visible in part A, although B's attaining policies need no cached result. A kernel callback that instead returns an error and requires an additional call is a different interface.

Before each selected operation's gate, a writer can install a fresh own-key identity distinct from all retained target identities. All preparations count toward W, including discarded and early computations. Writers and programs can depend on the observed history; a globally b-bounded environment must respect its cap on every play, including inadmissible-program plays. A finite prescribed own-gate write sequence, with an unconditional cap, supplies each lower-bound witness used here. Completed jobs persist and can be used as parents without being invalidated again.

## A. Complete supplied-one-write frontier for W and P_g

Let the controller be supplied B=1 and require Q<=n (r=0). Require completion, Q<=n and W<=S+M in every globally at-most-one-write environment, where S=sum_i w_i and M>=0. Define heavy jobs H_M={i:w_i>M} and

    p_i = g_i + w_i * 1[i in H_M],
    q_i = w_i * 1[i not in H_M].

For a topological order pi, C_i^p(pi) is the cumulative p through i. Then the candidate exact value is

    ell_g(M) = min_topological pi max_i (C_i^p(pi)+q_i).

The nondominated pairs (S+M,ell_g(M)) for M in {0,w_1,...,w_n} are the complete frontier of separate worst-case W and P_g. With g=0 this is the manuscript's existing one-write reduction; with M>=max(w) this is the all-cached entry-cost result in guard_entry_01/PROOF02.md. The algorithm is Lawler's inherited backward minimum-q sink rule, not a new scheduler. It allows zero processing times. A straightforward implementation takes O(n^2+|E|) per threshold and O(n^3+n|E|) for the complete sweep.

### Upper bound

Follow a chosen topological order. Complete heavy jobs fresh. For each light job, prepare just in time and invoke cached completion. Upon the first cached mismatch, switch every remaining job to just-in-time prepare/cheap publication. That mismatch identifies a write in its fresh read-to-comparison interval; since the supplied bound is one, there can be no later write and every suffix cheap call succeeds. An unobserved write before a fresh call or an irrelevant write does not make this inference unsound: it may prevent a mismatch altogether, and cannot create a second write.

Exactly n calls complete the n jobs. Every completed job pays its mandatory body once, and only the mismatching light job can pay a duplicate body, of weight <=M. The no-mismatch protected cost is sum_i p_i. A mismatch at a light job i gives protected cost C_i^p+w_i and no further guarded cost. These cases attain the maximum of sum_i p_i and all light terms C_i^p+w_i. Fresh-job terms are C_i^p and are bounded by sum_i p_i, so the value is exactly max_i(C_i^p+q_i). Distinct terms may have distinct witness executions, as required by separate suprema.

### Lower bound for arbitrary admitted programs

Follow an admitted program's no-write execution. A cheap completing call is impossible: its fixed prefix has a one-write failing continuation, and n mandatory completions together with this failure violate Q<=n. Thus every job completes by a guarded operation. These completions induce a topological order pi.

Let F contain the jobs whose whole bodies are protected on this path, with all paid preparations accounted for. Its no-write protected charge is at least Gamma+sum_F w. Every other job i completes with a matching cached operation and admits an own-gate fresh-write continuation. Global charging gives W>=S+w_i on that continuation even with early preparation, retained records and unused computations. Consequently every heavy job is in F. The same continuation gives protected cost at least

    sum_(j through i) g_j + sum_(j in F before i) w_j + w_i.

These are lower bounds from alternative executions of the same original program; no purported implementation transformation is used. Let H_pi(F) be their maximum together with Gamma+sum_F w. If a light job j belongs to F, remove it from this algebraic expression. The no-write total and later terms decrease by w_j. The new j term equals its old guarded charge through j and is no greater than the old no-write total. Earlier terms are unchanged. Therefore this removal cannot increase H_pi. Repeat until F=H_M. The resulting expression is exactly max_i(C_i^p+q_i). Minimizing over possible no-write orders proves the lower bound.

For the scheduling rule, put a remaining sink j with minimum q_j last. If an optimal order instead ends in sink k, moving j to the end weakly decreases all intervening completion times. Its new term T+q_j is no larger than the old last term T+q_k, where T is total remaining processing. Recurse. This is Lawler's classical exchange proof. For an intermediate threshold, the actual duplicate bound is max({w_i:w_i<=M} union {0}); equality with M is needed only at the retained weight thresholds. As a threshold crosses a weight, that job's own term remains unchanged while later p-prefixes decrease, so ell_g is nonincreasing and the finite threshold sweep suffices.

### Important separation

This theorem's first coordinate is body work W, not W plus guard charges. Since a mismatch allows a cheap suffix, total entry charge is path-dependent. Merely adding Gamma to each W frontier point is wrong in general. Native calibration is not supplied by this equivalence.

## B. A positive cached-comparison cost creates a subset-selection boundary

Now additionally charge every cached completion a known positive c_i under protection, whether it matches or mismatches. Fresh completion has its g_i charge but does not perform this additional saved-record comparison. Cheap comparison costs, if modeled, are irrelevant to the zero-write lower-bound executions below because no cheap call is allowed there. For precision one may set any outside cheap comparison cost to zero; no positive cheap-cost result is used.

Define fully charged resources

    W_t = W + sum_guarded g_i + sum_cached c_i,
    P_t = L + sum_guarded g_i + sum_cached c_i.

Thus protected comparison costs are included in total work as well. Costs are fixed scalar resource charges, not observed clocks or new side channels. They do not allow comparison skipping, shared-guard amortization, partial record reuse or batched completion.

Consider universal Q<=n programs (r=0), which receive no write bound and must complete in every finite-write environment. Evaluate their separate worst-case resources at B=0. Even independent jobs suffice. The proposed exact frontier is

    nondom { (S+Gamma+sum_(i in C)c_i,
              S+Gamma-sum_(i in C)(w_i-c_i)) : C subset of jobs }.

This is a value/frontier statement for this zero-write coordinate over universally admissible programs, not a guarantee of a single least frontier curve at all B.

### Exact upper and lower bounds

For any chosen C, follow any topological order, freshly prepare/cache-completing jobs in C and fresh-completing all other jobs. Every operation completes despite arbitrary writes, so the program is universally n-call admissible. At zero writes, cached comparisons match. Each fresh job contributes (w_i+g_i,w_i+g_i); each prepared matching cached job contributes (w_i+g_i+c_i,g_i+c_i). Summing yields the displayed pair.

Conversely, the no-write execution of any universally admitted program cannot contain a cheap call. At its first such call, an additional own-gate write in a finite alternative continuation would invalidate every retained target record; one failed call plus n mandatory completing calls violates the universal n-call promise. On the no-write execution all jobs therefore complete through guarded calls. Classify its matching cached completions as C and its fresh completions as the complement. Correctly formed target records do not become stale on a no-write run; initial preparations are charged. Even if an enlarged interface admitted an initially stale record, its cached completion would pay at least a fresh completion in both coordinates, provided mandatory computation remains charged. Every job requires its mandatory body work once, including paid preparation. Further preparations increase W_t and cannot reduce the lower bound on P_t. Each cached matching completion must pay its c_i and g_i. For this no-write execution e_0, let Phi(C) be the displayed subset pair. Componentwise, Phi(C) <= (W_t(P,e_0),P_t(P,e_0)) <= (sup_E0 W_t(P,E0),sup_E0 P_t(P,E0)). The original pair of separate suprema is therefore weakly dominated by the displayed pair for C. This proves completeness for arbitrary admitted programs and arbitrary input-dependent local decisions, without reusing the body-only normal-form theorem.

Jobs with w_i<=c_i may be omitted from C: including one weakly increases protected cost and strictly increases total cost. Ties and duplicate resource pairs are removed by ordinary Pareto pruning.

### Decision complexity and exact frontier size

For positive integer costs encoded in binary, ask whether a universally n-call-admissible program has its B=0 coordinates bounded by K_W and K_P. Given a subset C, the two sums can be checked in polynomial time, and the preceding theorem makes such a subset a complete certificate. Hence this restricted decision problem is in NP.

Reduce 0/1 knapsack with positive item sizes a_i, values v_i, size limit A and target V by setting c_i=a_i, w_i=a_i+v_i and g_i=1. Set K_W=S+Gamma+A and K_P=S+Gamma-V. The two inequalities become exactly sum_C a_i<=A and sum_C v_i>=V. The encoding length grows polynomially. Thus the restricted decision problem is NP-complete. It has the standard knapsack pseudo-polynomial dynamic program in the integer capacity min(K_W-S-Gamma,sum c_i), so this is a weak NP-completeness boundary; no strong hardness is asserted. The inherited knapsack algorithm and reduction source must be cited accurately.

For an explicit output-size family, take c_i=2^i, w_i=2c_i and g_i=1, i=0,...,n-1. Every subset has a distinct sum s. Its pair is (S+Gamma+s,S+Gamma-s). Increasing s strictly worsens total cost and improves protected cost, so all2^n pairs are nondominated. The instance uses O(n^2) bits in these binary integers. This proves exponential output size in number of jobs for this charged-comparison class; it does not prove a2^n time lower bound in total input-bit length.

If all c_i equal one common c>0, sorting positive profits w_i-c gives the full n+1-or-fewer-point frontier: for each cardinality k choose its k largest profits, omit nonpositive ones, and add the common k*c total charge. This special case is polynomial and is not covered by the heterogeneous-cost hardness conclusion. At c_i=w_i, cached choice loses any protected saving and is dominated by fresh completion at this coordinate.

### Information contract and attribution

Supplying B=0 would instead permit cheap completion and would destroy the lower-bound premise. The stated decision problem uses a universal completion contract evaluated at B=0, so there is no claim of hardness for an informed zero-write instance. There is also no new hardness claim for the original free-comparison model, the fixed-g-only model, the general positive-retry DAG body-work problem, or actual native performance. This is an interface/cost boundary identifying why positive, heterogeneous protected comparisons change the optimization structure.

Numerical checks can refute an implementation or a candidate formula, but cannot establish the all-program reduction, asymptotic output-size statement, or complexity theorem. Those remain proof obligations.


## C. Information and comparison-charge boundaries within the same regime

These statements keep the same n-call, whole-kernel, single-completion-call interface and the same fully charged W_t/P_t resources. They are direct consequences of B's equivalence, not comparisons between the different regimes of A and B.

**Supplied zero-write information.** If B=0 is supplied, immediate preparation followed by cheap publication of every ready job terminates in exactly n calls. It pays exactly S total work and no protected or guarded charge. Mandatory kernel work gives W_t>=S, and costs are nonnegative, so (S,0) is the single nondominated point. This holds with arbitrary nonnegative g and c and every DAG. It assumes the stated zero charge for cheap publication; an added positive cheap charge defines a different cost model.

**Universal completion with zero additional comparison charges.** Retain the requirement of completion with Q<=n for every finite-write environment, evaluate costs at B=0, and set all c_i=0. The no-write lower bound from B still rules out cheap calls. All-cached dominates each fresh choice and attains the unique pair (S+Gamma,Gamma). Thus the heterogeneous-positive-c result is a transition within this same universal, zero-write evaluation regime; changing g alone gives a constant shift, not the subset tradeoff.

**At most d distinct positive comparison charges.** Omit all jobs with w_i<=c_i from the cached set. Partition the remaining jobs into d groups with equal charges c_v and sizes n_v. Sort each group's positive profits w_i-c_v in nonincreasing order and let A_v(k) be its first-k profit sum. For a fixed cardinality vector (k_1,...,k_d), total comparison cost is sum_v k_v c_v and does not depend on identities within a group. Protected cost is minimized by the top k_v profits in each group, because replacing a smaller selected profit by a larger unselected one preserves total cost and decreases protected cost. Hence Pareto pruning the candidates

    (S+Gamma+sum_v k_v c_v, S+Gamma-sum_v A_v(k_v))

for 0<=k_v<=n_v is exact. There are at most product_v(n_v+1)<=(n+1)^d candidates. Group sorting and prefix sums take O(n log n) comparisons; forming and sorting m candidates takes O(dm+m log m) arithmetic/comparison operations, with ordinary polynomial-bit integer sums. Fixed d therefore gives a polynomial-time frontier. This is an exponent depending on d, not a fixed-parameter tractability assertion. For d=1 it gives the common-charge result; the exponential example has d=n. Since B's argument depends on a topological no-write completion order but not on which order it is, the subset frontier and these statements hold on any DAG as well as independent jobs.

These elementary consequences describe the price of universal completion and heterogeneous validation charges in this interface. They do not establish an empirical speedup, a real caller SLA, strong NP-hardness, original free-comparison hardness, or a least full curve for positive-retry DAGs.

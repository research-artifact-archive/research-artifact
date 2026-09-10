# Fully charged supplied-one-write frontier: final author proof05

This author proof follows the candidate04 fixed check, the read-only author inspection and the Fable 5.1 ultra Cost11 critique. All predecessors and raw responses remain immutable. Finite/model agreement is not a proof certificate. PROOF03's deterministic whole-kernel operation class, old raw snapshots, charged initialization, fresh gate identities, exact comparisons, single-call protected completion, and no amortized/partial/batched completion remain in force. Every whole-kernel invocation costs exactly w_i>0. Guard charges g_i>=0 apply to fresh and cached calls; cached calls additionally pay c_i>=0 under the same guard, on either outcome. These supplied scalar charges count in both W_t and P_t. Cheap comparison/publication has zero additional charge. Waiting and native-time calibration remain outside the model.

The following operational assumptions are explicit. A preparation reads an immutable own-key input and exact completed predecessor outputs; records cannot be fabricated or retagged without their mandatory computation. Initial old raw snapshots may already differ from the live identity at the charged start. They do not certify a write in the evaluated interval; every computation from them is charged. Charged initialization accounts for computations actually performed, not an obligatory fixed fee. The attaining policy ignores old snapshots and computes just in time, with no extra initialization. The live initial state and old raw snapshots are fixed before the evaluated writer interval begins.

The program chooses its ready job, mode and available record store before the gate. The adversary's fresh own-key write can occur after that choice and before the indivisible guarded comparison/recomputation/publication begins; it does not interrupt protected work. Free outside inspections do not eliminate this interval. Cached comparison exposes its match/mismatch Boolean, and either outcome completes that job within the same counted call. Cheap mismatch counts as a failure in Q. Only a mismatch of a fresh JIT record proves a write since that capture; mismatch of an initially stale record is not such evidence. Programs are deterministic; separate pathwise suprema, not expected randomized costs, are used.

Here the program is SUPPLIED B=1 and must complete with Q<=n in every globally at-most-one-write environment. Both coordinates are separate worst-case suprema over that same environment class. This is the same one-write, zero-retry setting as the manuscript's Lawler theorem, now with both total and protected charges included.

## 1. Complete frontier via one no-write order and mode assignment

For a topological order pi and a subset C of cached jobs, put F=J\C, h_i=g_i+c_i*1[i in C], H=sum_i h_i, H_i=sum_(j through i in pi)h_j, and F_i=sum_(j in F before i in pi)w_j. Let S=sum_i w_i. Define

    A(pi,C) = S + max({H} union {w_i+H_i : i in C}),
    D(pi,C) = max({H+sum_(j in F)w_j} union
                  {w_i+H_i+F_i : i in C}).

The full (W_t,P_t) frontier is nondom{(A(pi,C),D(pi,C)): pi topological, C subset J}. A policy witness has only an order, a mode bit per job, and a flag recording whether a cached mismatch has occurred.

### Attainment

Follow pi. Until a mismatch, complete F fresh and immediately prepare/cache-complete C. Once the first cached comparison mismatches, immediately prepare/cheap-complete every remaining job. The mismatch of a just-in-time record proves that the only possible write has occurred. Exact comparison has no spurious failure, so the cheap suffix is safe. There are exactly n completing calls in every admitted environment.

If no cached mismatch occurs, total body work is S and protected body work is sum_F w. The extra charge is H; the path pair is (S+H,H+sum_F w). If cached job i mismatches, its body is performed twice, all other mandatory bodies once, and no later guard or comparison charge is incurred. The pair is (S+w_i+H_i, w_i+H_i+F_i). No writes and a single fresh write at the selected i gate respectively realize these paths. Other writes do not enlarge the set of charged outcomes. Taking coordinatewise maxima gives exactly A and D.

### All-program lower bound

Follow any admitted deterministic program P on any fixed no-write execution. It must terminate, and each job requires a distinct completing call. A cheap call cannot appear: the fixed no-write prefix admits a one-write failing continuation, which leaves a failed call in addition to the n required completing calls. The n-call promise would fail. Therefore all jobs complete by a guarded operation in a topological order pi.

Let C be matching cached completions and F be fresh or already-stale cached completions on this execution. Old raw snapshots can be stale initially; their preparations and protected recomputations are charged. Treating each already-stale cached completion as fresh in the lower-bound expression only removes nonnegative comparison/preparation charges. The no-write execution thus gives W_t>=S+H and P_t>=H+sum_F w.

For every i in C separately, extend the identical prefix by a fresh own-key identity write at its gate and then stop writing. This is a globally one-write environment, with an unconditional one-write cap on every history. That write invalidates every retained target record. The global charging lemma gives W>=S+w_i, including paid early or discarded preparations; it does not charge a suffix as if it started for free. All earlier guarded calls, and i's cached comparison, have already incurred at least H_i. The protected bodies on the prefix contribute at least F_i, and i recomputes its whole body under the guard. Thus this execution gives W_t>=S+w_i+H_i and P_t>=w_i+H_i+F_i.

These are different witnesses against the same P. Its separate coordinate suprema dominate their respective maxima, namely (A(pi,C),D(pi,C)). The explicit policy above attains this pair, so arbitrary free inspections, retained records, paid initialization, value-dependent choices and late branch choices do not improve the frontier. This is a resource domination result for the supplied-one-write class, not a transformation preserving the original program's exact outputs on the same environment.

## 2. Decision complexity and an embedded subset frontier

With positive integer works and nonnegative integer charges encoded in binary, deciding whether both bounds are at most K_W,K_P belongs to NP: an order pi and mask C are polynomial-size certificates. Check topological legality, calculate prefix sums and the two maxima, and compare the caps. The all-program lower bound makes this certificate complete. No exponentially large policy tree is required for this decision problem.

Use nonempty item instances; out-of-range targets and empty instances can be decided first. For a 0/1 knapsack instance with positive item sizes a_i, values v_i, size cap A and target V, create original jobs with c_i=a_i, w_i=a_i+v_i, and g_i=1. Add one dummy job z with w_z=c_z=1 and g_z=G=max_i w_i. Set base=sum_all w+sum_all g. The resulting N=n_original+1 jobs have call cap Q<=N. Jobs may all be independent; requiring every original job to precede z also works.

Given an original-item subset C, run those jobs with its selected cached/fresh modes in any order, then complete z fresh last. On the no-write execution the pair is

    Phi(C)=(base+sum_C a_i, base-sum_C v_i).

Every mismatch before z saves the final guard G. More explicitly, for a cached i,

    w_i+H_i <= H, since H-H_i >= g_z=G>=w_i,
    w_i+H_i+F_i <= H+sum_F w,

where the second inequality follows already from the first and F_i<=sum_F w. Hence the no-write execution simultaneously attains both worst coordinates. This proves upper attainment of every displayed subset pair in the supplied B=1 class.

Conversely, follow any admitted program's no-write execution and extract its matching cached subset C' as above. Its coordinate pair dominates the corresponding no-write Phi(C'). If z is in C', remove z: c_z=w_z, so total charge decreases by one and protected cost is unchanged. The remaining original subset C therefore satisfies Phi(C)<=the original worst pair. It follows that this entire family's frontier is exactly the nondominated original subset pairs. Caps K_W=base+A and K_P=base-V are feasible precisely when the knapsack instance is feasible.

Alternatively, reduce exact positive SUBSET SUM directly with c_i=a_i,w_i=2a_i and the two caps base+T,base-T. Both inequalities require sum_C a_i=T. Karp's primary completeness statement and exact 0-1 integer KNAPSACK definition are verified at printed pages94--95 of the archived reprint. A negative coefficient -a times x can be replaced by a times (1-x), shifting the target by a; discard zeros and handle trivial targets. This polynomial conversion gives the positive exact subset-sum source used here. The reduction and NP-hardness are inherited; the completion-program embedding is proved above.

Thus the general supplied-one-write fully charged decision problem is NP-complete, already for independent jobs. Do NOT call the entire general problem weakly NP-complete without a general pseudopolynomial algorithm: the reduction alone does not settle possible strong hardness. The embedded family is the usual weakly NP-complete subset/knapsack problem and admits its inherited capacity DP. This does not give hardness for the original free-comparison body-work problem.

For an output-size family, take n original jobs c_i=2^i,w_i=2c_i,g_i=1, i=0,...,n-1, and the same final fresh dummy with G=2^n. Each original subset has a distinct sum s and pair (base+s,base-s). All 2^n pairs are nondominated. There are n+1 jobs and O(n^2) input bits. This is exponential output size in jobs; it is not a 2^n time lower bound in total input-bit length or an optimality claim for a particular exponential algorithm.

The dummy's large fixed guarded charge is a mathematical construction, not measured synchronization behavior. The result identifies a change in exact optimization structure when cached comparisons incur supplied heterogeneous costs; no natural workload is asserted to realize these prices. Knapsack, subset pruning and any DP are inherited mathematics. The new proof obligation is their equivalence to all admitted completion programs under the stated resource contract.

## 3. Finite implementation corroboration and recurrence

An independent direct mode recurrence is available for B=1. At remaining set U and ready i, put R=U minus {i}. Let (a,d) be a suffix pair on R with one possible write remaining and S_R=sum_(j in R)w_j. The selected i is excluded from S_R. Fresh gives (w_i+g_i+a,w_i+g_i+d). Cached has the matching pair (w_i+g_i+c_i+a,g_i+c_i+d) and mismatching pair (2w_i+g_i+c_i+S_R,w_i+g_i+c_i), because the known-zero-write suffix is cheap. Take maxima separately and Pareto-prune across root choices. Suffix pairs may differ across root choices, but only the matching child retains uncertainty. This recurrence and an independent enumeration of order/mask paths should agree with the closed form. All-program completeness and complexity still require the analytic proof above.


Each recursion state stores a Pareto set. Every displayed root cost map is coordinatewise nondecreasing in the chosen suffix pair, so replacing a dominated suffix pair is safe. The fixed04 run checks 14,696 general inputs and 1,662 subset embeddings in its declared scopes, with no discrepancy. It does not enumerate arbitrary retained-record programs or establish the asymptotic claims.

## 4. A fresh final job suffices

If the last job z in a fixed order is cached, make it fresh. The new no-write total removes c_z and is no larger than the old last-mismatch total. The new no-write protected cost equals the old last-mismatch protected cost minus c_z. Any earlier mismatch path is unchanged because it already finishes z cheaply after the single write. Thus this change weakly improves both maxima; order/mask certificates may require a fresh last job without losing frontier points. For one job, fresh therefore dominates caching at supplied B=1,r=0. This analytic consequence was not retrospectively preregistered as a separate fixed04 test.

COST_BOUNDARY_NOTE05 gives a c-only zero/uniform/heterogeneous transition for the fixed-dummy subset family, keeping its works and guard costs unchanged. It does not classify all general g-only or uniform-comparison-cost DAG instances.

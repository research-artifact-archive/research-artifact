# Exact all-budget boundary for multiple partial-repair jobs

Author-derived candidate, 2026-09-10. Initial no-toll proof proposed by read-only helper Fermat; root rechecked it and added the full-work saturation statement. Numerical results are separate. This is not a theorem about arbitrary Roslyn operations.

## Interface

There are n>=1 jobs in a finite DAG, all initially unfinished. Job i has finite positive component weights, a fixed nonempty family of nonempty footprints, and reachable repair work W_i>0. After all predecessor jobs complete, it may be freshly prepared. Each invocation observes dirtiness D caused by writes since that preparation. One may accept, pay w_i(D), publish a permanent output and remove the job, or reject and consume one global failure allowance. Every new invocation uses a fresh preparation, resetting dirtiness. At most n+r counted calls are available, r>=0; no other operation completes a job. Work is protected repair only. There are no cross-job footprints or retained protection; different invocation intervals can independently realize the same footprints. Kernels/calls and foreground scheduling terminate. All policies here are deterministic.

Let c_i(D) be the minimum number of footprints whose union is exactly D. G_i(b)=max{w_i(D):c_i(D)<=b}, and sigma_i=min{b:G_i(b)=W_i}. Let Sigma=sum sigma_i, W=sum W_i, and Omega_k the sum of the largest min(k,n) reachable works W_i. Positivity implies sigma_i>=1, and each G_i saturates after finitely many writes. The environment uses at most B writes, may leave some unused, and may add redundant writes that reveal no extra information. The controller observes dirty sets, not B or actual repeated-write counts. The aware comparator is supplied B; a universal unaware policy must meet the cap in every finite-write environment. Let K(B) be the aware minimax protected repair work.

## Theorem1: the multi-job simultaneous-optimality boundary

For r>=1 one policy is optimal for every B iff G_i(1)=W_i for every job i. The result holds both for a prescribed order and for choices among DAG-ready jobs. Under the condition,

    K(B)=Omega_min((B-r)+,n),

and the policy rejecting its first r nonempty observations globally and otherwise accepting attains this curve simultaneously. For r=0, accepting every observation is simultaneously optimal for all footprints; its value is max_{sum b_i<=B} sum G_i(b_i).

**Sufficiency.** Every rejection consumes at least one write. Before r rejections every acceptance is clean; after them, at most (B-r)+ jobs can accept nonempty damage. Each costs at most W_i, giving the displayed upper bound. To force the matching lower bound, target the k=min((B-r)+,n) heaviest jobs and issue one saturating write before each of their observations; other jobs see no writes. Every targeted completion costs W_i. On any admissible run there are at most r rejections, so at most r+k writes suffice. Formally truncate the adversary after an (r+1)st rejection if needed: that forbidden prefix can be reached within r+k<=B writes, so an admissible program never takes it. Precedence/selection cannot avoid eventually completing each target. This proves the pointwise aware lower bound and the common unaware upper policy.

**Necessity.** At every B<=r, a policy can reject all nonempty observations and complete cleanly after those writes end; hence K(B)=0. Any simultaneous optimum must attain all these zeros. Issue one nonempty-footprint write in each of the first r attempted observations. After observation t<=r, the history is compatible with a complete execution using only t writes in total. Accepting positive damage would violate its zero optimum, so the policy must reject; no job has yet completed. Then saturate each job on its next attempted completion. This uses Sigma more writes. No rejection remains, so the unaware policy pays W under B0=Sigma+r.

If some j has sigma_j>=2, a comparator can reserve all r rejections for job j's fully dirty observations, accepting every other observation. This meets the cap in every finite environment. To pay total W, every job must complete with full reachable damage. In particular j must encounter r rejected full observations and then a full completion. All invocation intervals are disjoint and freshly prepared, so this needs at least Sigma+r*sigma_j > Sigma+r=B0 writes. Hence its worst work under B0 is strictly below W; the possible total repair costs form a finite set. Thus K(B0)<W, contradicting a common optimum. This reserve-j policy may use the same fixed order as the tested program, so the argument covers any DAG or fixed order.

At r=0 every call must complete; observing/accepting dominates fresh whole completion. An adversary may distribute at most B writes across jobs, giving exactly the maximum-convolution curve. No policy needs B to attain it.

## Theorem2: when the known-budget optimum first reaches full work

For all such inputs and r>=0, the first budget with K(B)=W is

    B_sat=Sigma+r*max_i sigma_i.

For the lower bound at this budget, saturate the currently attempted job before each observation. Each completed job costs W_i, and the r rejected invocations cost at most max sigma_i writes each. Truncate after an (r+1)st rejection as above; until that inadmissible prefix the write bound is respected. Every admissible policy therefore pays W using at most B_sat writes. The trivial upper bound is W.

For any B<B_sat, select j of maximum sigma_j and reserve all r rejections for its full observations, accepting everything else. Full total work requires Sigma+r*sigma_j=B_sat writes, so worst work is strictly below W. This also covers r=0. The statement identifies a saturation threshold, not the entire nonsaturated curve K(B).

## Observation-state recurrence and independent finite-policy question

For a supplied B, after each observed D deduct its minimum c_i(D). This is the largest remaining budget consistent with the observations. Every such minimum sequence is realizable by fixed repeatable footprints and independent preparation intervals; redundant writes only reduce the remaining allowance. The exact recurrence is

    F(S,b,t)=min_ready_i max_{D:c_i(D)<=b}
                 min{ w_i(D)+F(S-i,b-c_i(D),t),
                      F(S,b-c_i(D),t-1) if t>0 }.

Base F(empty,b,t)=0. This is the aware value, not a program receiving the actual write count. Accepting/rejecting is chosen after D is observed.

To test one common policy, keep minimum prefix consumption e and accumulated work ell. At each state, choose a ready job; every attainable D must admit either a winning accepting continuation or (with remaining slack) a winning rejection continuation. At completion require ell<=K(e). This suffices for every larger true budget by monotonicity, and is necessary because the least-consumption history itself is realizable. The finite search does not use the saturation theorem as an oracle. It checks existence against the whole curve with the correct information pattern.

The agent-observed example (A has two unit singleton components; C one; r=1) has K(B)=0,0,1,2,2,3 at B=0..5. Here Sigma=3; low-budget optimality forces cost3 at B0=4, while K(4)=2. B_sat=5. Its raw reproduction is explicitly not held-out data.

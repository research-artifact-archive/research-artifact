# Unit guard charges: the precedence complexity boundary

Use the exact full-program model and fully charged one-write representation in [FULLY_CHARGED_PROOF05](../charged_comparison_01/FULLY_CHARGED_PROOF05.md). This is the all-program premise; the following statements do not restrict programs syntactically to fixed orders. Writer bound B=1 is supplied, Q<=n, comparisons are visible, c_i=0, and every guarded completion has the SAME incremental charge g_i=1 in BOTH total and protected resources. Thus Gamma=n. Complete policies may use arbitrary legal free inspections, raw snapshots and paid retained records; the representation is not assumed as a syntactic restriction.

For a topological no-write order pi and its matching-cached subset C, F=J\C, let pos(i) be its 1-based position and F_i the body work of earlier F jobs. The complete representation specializes to

    W(pi,C) = Omega + max(n, max_{i in C}(pos(i)+w_i));
    P(pi,C) = max(n + sum_{i in F}w_i,
                  max_{i in C}(pos(i)+w_i+F_i)).

Every admitted program is coordinatewise dominated by a displayed pair and each pair has an attaining first-mismatch-switch policy. This is the previously proved all-program theorem. It implies NP membership through an order and mask certificate.

## Inherited scheduling construction and completion-specific reduction

The incidence construction and prefix argument below are inherited from Garey and Johnson, Scheduling Tasks with Nonuniform Deadlines on Two Processors, JACM23(3),461–467,1976, Theorem2 at465–466 (https://doi.org/10.1145/321958.321967). Despite its title, that theorem concerns the one-processor unit-time tardy-job problem. PRIMARY_ATTRIBUTION01 records the exact verification scope. The proof here must additionally connect this classical construction to two separate worst-case resources over all admitted completion programs. It does not claim a new scheduling-hardness construction.

Take a simple undirected graph G=(V,E) and integer k>=3. The restricted source remains NP-complete: k<3, k>|V|, or |E|<choose(k,2) can be decided in polynomial time, with a fixed yes/no target used for such trivial cases. For an exact-height-two target take two predecessor jobs and their common successor, all works and guards1; caps(6,6) are feasible by all-fresh and caps(5,6) are infeasible because total work is at least6. For the nontrivial reduction assume |V|>=k and |E|>=K=choose(k,2).

Add two new vertices and their single isolated edge. This does not create a k-clique for k>=3. Let v,m be the augmented vertex and edge counts. Then m>=K+1, v>=k+2. The spare edge is essential to the following cap choice: without it, m=K would give K_P=n, below the constructive cached-edge mismatch cost. Padding creates room for that cost while preserving the source answer.

Create v vertex jobs and m edge jobs, n=v+m. Every vertex job has body work1, and every edge job has body work H=n+1. The only DAG edges are vertex-job -> edge-job for each endpoint. The DAG has height two and each edge job has exactly two immediate predecessors. All g_i=1 and c_i=0. Define

    D=k+K; Omega=v+m*H;
    M=D+H;
    K_W=Omega+M;
    K_P=n+(m-K)*H.

All numerical values are polynomial in graph size: works<=n+1, caps O(n^2). Since n>D and m-K>=1, K_P>=n+H>M; also M>n.

### If G has a k-clique

Process its k vertex jobs first, then its K internal edge jobs, completing this prefix at position D. Process all other vertex jobs next, then all other edge jobs. This is topological. Cache all vertex jobs and the K clique-edge jobs; finish all remaining edge jobs fresh on the no-write path. After any first mismatch switch to immediate prepare/cheap as in the full representation.

For each cached clique-edge job, pos(i)+w_i<=D+H=M. For every cached vertex, pos(i)+1<=n+1=H<M. Thus W<=Omega+M=K_W. All fresh edge jobs lie after C, so every cached mismatch term has F_i=0 and is at most M<K_P. The no-write protected term is n+(m-K)H=K_P. This policy is feasible (indeed its worst pair equals the chosen caps, as the last clique-edge gate attains M).

### If a program meets both caps

Fix ONE no-write execution and extract its topological order pi and matching-cached subset C using the complete representation. Every own-gate lower witness below preserves this same no-write prefix/order, although different jobs use different one-write environments. A pair of separate supremum caps must bound all of these environments. The no-write protected term forces

    n + (#fresh edge jobs)*H + (#fresh vertex jobs) <= K_P,

so at least K edge jobs belong to C. For any such edge job, the total-work own-gate witness forces

    pos(i)+H<=M, hence pos(i)<=D.

Look at the first D positions of pi. They contain at least K distinct cached edge jobs and therefore at most D-K=k vertex jobs. All endpoints of those edge jobs must already be in that prefix. A simple graph on at most k vertices containing at least choose(k,2) edges has exactly k vertices and all pairs: a k-clique. The added isolated edge cannot form a new k-clique. Hence the original graph contains one.

Thus joint-cap decision is NP-hard. Because every numerical parameter is polynomially bounded in the underlying graph size, the hardness is strong. Together with the order/mask certificate it is strongly NP-complete in this unit-guard, free-comparison, height-two class. The generic precedence scheduling decision is inherited; the claimed result is this embedding into the completed-program joint resource contract. This does NOT contradict the independent common-g greedy theorem or scalar-P Lawler theorem.

## Polynomial number of frontier points, even on any DAG

More generally set every g_i=g>=0, c_i=0, at supplied B=1,Q<=n. The first coordinate of any represented pair lies in

    {Omega+n*g} union {Omega+w_i+j*g : i in J, j=1,...,n},

after retaining only values actually produced by the max. There are at most n^2+1 possibilities. For one first coordinate, only the least second coordinate can be nondominated. Thus every DAG has at most n^2+1 distinct frontier points under common g. The strong hardness at g=1 is search hardness despite this polynomial output bound. It does not imply that the independent O(n^3) frontier algorithm works on DAGs.

## A positive cost on every counted call

If every mode on job i additionally pays a fixed protected call fee d_i>=0 in both coordinates, then every admitted execution pays exactly sum_i d_i because each admitted execution must complete all n jobs within Q<=n. Thus it contains exactly n calls, all completing; no failed call occurs, and every job completes in one call. Translate both caps and all frontier points by this constant. Taking d_i=1 makes cheap calls positively charged, guarded calls have the extra unit, and preserves the strong-hardness construction. This is a specified deterministic fee model, not native calibration or arbitrary mode costs; positive-retry failures would destroy the constant-fee argument.

## Proof checking and finite corroboration

Candidate01 preceded the fixed observations. Read-only author criticism and the normal-usage Cost13 critique found no counterexample conditional on the full-program premise. Their scope and any attribution corrections remain explicit. Neither establishes research novelty or acceptance.

The fixed final matrix and all outcomes are in PROTOCOL02, INPUT_FIX_RECEIPT02 and run02. All1,399 nontrivial reductions agree with direct source CLIQUE enumeration (728yes/671no), with all3,208 source cases retained. The675 general DAG cases also agree with complete order/mask enumeration, the output bound and the separately implemented all-call-fee recurrence. These checks corroborate the construction and witnesses; the asymptotic and all-program conclusions rest on the proofs above and the inherited representation. RESULT02 provides the exact denominators and controls. No native timing, caller SLA or practical overhead calibration is inferred.

## Zero guard charge on any DAG: inherited polynomial counterpart

This consequence is already contained in the earlier body-work/guard-cost Lawler theorem; it is restated to expose the zero-versus-unit boundary. Assume the same B=1, Q<=n interface, c_i=0 and g_i=0. A total cap below Omega is infeasible. For a cap Omega+M, M>=0, only jobs with w_i<=M may be matching-cached. For any fixed topological order, changing an eligible fresh job i to cached does not increase protected cost: the new mismatch term w_i+F_i is bounded by the old no-write protected load; later fresh-body prefixes decrease and earlier ones remain unchanged. Hence choose all eligible jobs C={i:w_i<=M} and F=J\C.

Set scheduling processing times p_i=w_i for i in F and0 otherwise, and tails q_i=w_i for i in C and0 otherwise. The protected objective is exactly max_i(C_i^p+q_i), where C_i^p is the processing completion time in the topological order: cached terms give F_i+w_i, and fresh completion times are bounded by their total Omega(F), attained at the last fresh job if F is nonempty. If F is empty all processing times are0 and the maximum is max_i w_i. The unchanged Lawler backward rule (1973, DOI https://doi.org/10.1287/mnsc.19.5.544) applies also to zero processing times. Run it at M in {0} union {w_i} and prune the actual pairs to obtain the complete frontier in O(n^3) arithmetic/comparison operations.

Thus, on the same arbitrary-DAG completion interface with supplied B=1, Q<=n and c=0, changing the common guard price from0 to1 changes joint-cap decision from polynomial to strongly NP-complete. The output has at most n+1 points at0 and at most n²+1 at1. The earlier inherited scheduling algorithms remain unchanged; the boundary concerns charging entry work in both completion-resource coordinates. The common positive all-call fee can be added on either side as the proved constant translation.

Read-only author review checked this specialization against paper187's existing proof, including F empty, negative M and zero processing times. No additional scientific execution is claimed for this restatement.

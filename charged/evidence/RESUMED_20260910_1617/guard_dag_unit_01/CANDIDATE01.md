# Unit guard charges: author strong-hardness candidate01

Assume the exact full-program model and fully charged one-write representation of FULLY_CHARGED_PROOF05 and paper192 Theorem10. Writer bound B=1 is supplied, Q<=n, comparisons are visible, c_i=0, and every guarded completion has the SAME incremental charge g_i=1 in BOTH total and protected resources. Thus Gamma=n. Complete policies may use arbitrary legal free inspections, raw snapshots and paid retained records; the representation is not assumed as a syntactic restriction.

For a topological no-write order pi and its matching-cached subset C, F=J\C, let pos(i) be its 1-based position and F_i the body work of earlier F jobs. The complete representation specializes to

    W(pi,C) = Omega + max(n, max_{i in C}(pos(i)+w_i));
    P(pi,C) = max(n + sum_{i in F}w_i,
                  max_{i in C}(pos(i)+w_i+F_i)).

Every admitted program is coordinatewise dominated by a displayed pair and each pair has an attaining first-mismatch-switch policy. This is the previously proved all-program theorem. It implies NP membership through an order and mask certificate.

## Reduction from CLIQUE

Take a simple undirected graph G=(V,E) and integer k>=3. The restricted source remains NP-complete: k<3, k>|V|, or |E|<choose(k,2) can be decided in polynomial time, with a fixed yes/no target used for such trivial cases. For the nontrivial reduction assume |V|>=k and |E|>=K=choose(k,2).

Add two new vertices and their single isolated edge. This does not create a k-clique for k>=3. Let v,m be the augmented vertex and edge counts. Then m>=K+1, v>=k+2.

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

Extract its topological order pi and matching-cached subset C using the complete representation. The no-write protected term forces

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

If every mode on job i additionally pays a fixed protected call fee d_i>=0 in both coordinates, then every admitted execution pays exactly sum_i d_i because Q=n and every job completes in one call. Translate both caps and all frontier points by this constant. Taking d_i=1 makes cheap calls positively charged, guarded calls have the extra unit, and preserves the strong-hardness construction. This is a specified deterministic fee model, not native calibration or arbitrary mode costs; positive-retry failures would destroy the constant-fee argument.

## Small-case expectations and unresolved obligations

Candidate proof needs independent author criticism of the first-D-prefix argument, the isolated-edge padding, the polynomial numerical bounds and all-program dependence. Finite checks should enumerate source graphs and CLIQUE directly, then compare the reduced caps to an unrestricted mode/DAG DP from fixed check04.py. Direct order/mask enumeration on large edge-incidence inputs is not needed to prove the reduction; retain exact state counts and timeout/invalids for bounded checks. Verify positive and negative source instances, not only clique witnesses. A single agreeing constructed instance is not a complexity proof.

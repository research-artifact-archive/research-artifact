# Comparison-free fully charged one-write class: author proof02

Status: author proof after read-only criticism and fixed01/greedy02 corroboration. These are not mechanical proof certificates or an independent acceptance verdict. Supplied B=1,Q<=n, independent jobs, positive body works w_i, nonnegative guarded-entry charges g_i, comparison charges c_i=0. Both total W_t and protected P_t include all guard charges. Waiting is excluded. Full original operation/record/gate/charging assumptions and all-program representation are inherited from FULLY_CHARGED_PROOF05. This does not change any prior result; in particular manuscript Section5 counts only body work in its first coordinate.

Write Omega=sum w_i and Gamma=sum g_i. For a cached subset C, place all cached jobs before fresh jobs, and order the cached jobs by nonincreasing w_i. Put

    K(C)=max_{i in C}(sum_{j in C through i}g_j+w_i), K(empty)=0.
    A(C)=Omega+max(Gamma,K(C));
    D(C)=max(Gamma+sum_{i notin C}w_i,K(C)).

Theorem: the whole independent-job frontier is nondom{(A(C),D(C)):C subset J}.

## Ordering proof

For any order/mask in the complete one-write representation, interchange adjacent fresh a then cached b. The new cached b gate omits g_a from its guard prefix and w_a from its fresh-body prefix. Every other cached gate has the same guard prefix and same earlier-fresh-body sum; the no-write charges and body sum are unchanged. Thus both maxima cannot increase. Repetition places C before F. This uses independence; it is not a valid DAG exchange in general.

Now F has no body contribution before a cached gate. Both coordinates depend on the cached order only through K(C). If adjacent cached a,b have w_a<w_b, their old maximum is max(t+g_a+w_a,t+g_a+g_b+w_b)=t+g_a+g_b+w_b. After swapping, both t+g_b+w_b and t+g_b+g_a+w_a are no larger. Hence descending w weakly minimizes K, with arbitrary tie order. The full representation's lower bound and these exchanges prove completeness. All-program completeness is inherited from its stated proof, not established by this finite ordering calculation alone.

## Joint-cap decision and pseudopolynomial DP

For integer cap values K_W,K_P, put M=K_W-Omega and T=min(M,K_P). If Gamma>M or Gamma>K_P, no policy is feasible. Otherwise a subset is feasible exactly when

    every selected prefix p+g_i+w_i <= T,
    sum_{i in C} w_i >= Gamma+Omega-K_P.

Sort by descending w. The standard subset DP keeps dp[p]=largest selected total w among the processed jobs with selected guard sum p and all selected prefix tests satisfied. Initially dp[0]=0 and other states are absent. Skipping i preserves a state; choosing i sends p to p+g_i and adds w_i only if p+g_i+w_i<=T. Use a fresh array or previous-layer values, including at g_i=0, to prevent repeated selection. Induction over processed jobs proves exactness. Compare max dp against Gamma+Omega-K_P. Integer time O(n*(Gamma+1)), space O(Gamma+1) for rolling-layer decision values; explicit all-layer predecessor storage may take O(n*(Gamma+1)) for witness recovery. Zero Gamma is handled by the same layered DP. This is pseudopolynomial in summed guard charges, with arithmetic on binary-sized works/caps.

For common g_i=g, a count DP of O(n^2) arithmetic operations is already sufficient. A faster attaining rule scans the same descending-work order and selects i exactly when (h+1)*g+w_i<=T, where h jobs have been selected. Compare its selected positions r_j to those o_j of any feasible subset. Inductively r_j<=o_j: after the greedy has selected j-1 jobs, the feasible comparison job at o_j passes its rank-j test, so greedy chooses its jth job no later. It therefore selects at least as many jobs, with at least as much work at every matched rank. Positive works prove maximum saved work. Decision takes O(n log n) arithmetic/comparison operations including sorting and O(n) after the order is supplied.

For a complete uniform frontier, use thresholds {Gamma} union {w_i+j*g>Gamma:1<=i,j<=n}. At each threshold maximize saved work with the greedy, recover its subset, compute its ACTUAL pair and Pareto-prune. For any original subset C, T=max(Gamma,K(C)) belongs to the threshold set. Its maximizing witness C' has K(C')<=T and at least C's saved work. Its total cost is at most Omega+T=A(C), while protected cost is at most max(Gamma+sum_F w,T)=D(C), since D(C)>=Gamma. Thus the sweep is complete. There are at most n^2+1 thresholds, giving O(n^3) arithmetic operations after one sort, and at most n^2+1 frontier points. Each witness is an order/mask/one-switch policy, with a linear-size mask/order representation.

For general integer guards a finite analogous threshold set is {Gamma} union {w_i+p>Gamma:0<=p<=Gamma, p integer}, evaluated by the inherited O(n*(Gamma+1)) DP. This is a pseudopolynomial frontier construction, not a polynomial output bound in binary encoding.

Candidate01 and checker01 already included the equivalent baseline threshold0 along with all actual K values. The author's warning that a baseline must be retained is valid, but is not an error in those saved versions. For n=1,w=1,g=0, dropping every baseline gives only the dominated cached pair(2,1), missing fresh(1,1); greedy02 records that deliberate alteration. The revised Gamma baseline avoids redundant smaller thresholds.

The subset DP is inherited scheduling mathematics. With processing g_i, profit w_i and deadline T-w_i, this is maximum-weight on-time subset selection. The publisher abstract of Lawler and Moore1969 (Management Science16(1):77--84, DOI10.1287/mnsc.16.1.77) identifies this DP line; Bringmann et al., ICALP2020, Theorem1.1 on printed19:2 explicitly states their O(n*sum processing) bound for weighted tardy jobs. Our deadline and profit are linked, so NP-hardness cannot simply be imported from unrestricted weighted scheduling: the reduction below proves it for the linked subclass. No new general scheduling algorithm or optimal pseudopolynomial exponent is claimed.

## NP-hardness with c=0 and strictly positive guards

Reduce positive SUBSET SUM a_1,...,a_m, target A with 1<=A<=S=sum a. Empty/out-of-range cases can be decided before the reduction. Let N=2m jobs have b=(a_1,...,a_m,0,...,0), with m zeros. Define

    d=q=S+1;
    g_i=q*(d+b_i);
    Gamma=q*(2m*d+S);
    k=Gamma+S+1;
    w_i=k+b_i; c_i=0;
    Omega=2m*k+S;
    ell=m*d+A;
    M=k+q*ell+S;
    K_W=Omega+M;
    K_P=Gamma+m*k+S-A.

All works and guards are positive binary integers of polynomial encoding length. Gamma<=M and K_P>=M: the latter difference is q*(m*d+S-A)+(m-1)*k-A>0. Therefore T=M.

For any subset C, K(C)<=M if and only if sum_C g_i<=q*ell. If the guard sum is at most q*ell, every prefix plus w_i is at most q*ell+k+S=M. Otherwise it is at least q*(ell+1), and the last selected job gives K(C)>=q*(ell+1)+k>M, since q=S+1. Thus the work-cap condition is

    |C|*d+sum_C b_i<=m*d+A,

which forces |C|<=m because d>A. The protected no-write cap requires sum_C w_i>=m*k+A. Since k>S, fewer than m selected jobs cannot meet it. Hence |C|=m and the two inequalities force sum_C b_i=A. Conversely any original subset of sum A can be padded with zeros to exactly m items, giving a feasible policy. Thus the joint-cap problem is NP-hard already in this comparison-free independent class; the order/mask certificate gives NP membership. The DP above supplies a pseudopolynomial algorithm for this class. Do not infer a general-DAG pseudopolynomial algorithm or free-body-W hardness.

## Exponentially many frontier points without comparison charges

For N>=2 jobs set b=(0,1,2,...,2^(N-2)), S=sum b=2^(N-1)-1, d=q=S+1,

    g_i=q*(d+b_i), Gamma=q*(N*d+S),
    k=Gamma+S+1, w_i=k+b_i, c_i=0,
    Omega=N*k+S.

For any nonempty C, write h=|C| and s=sum_C b_i. Every added guard exceeds S, so along descending b the final selected job realizes K:

    K(C)=k+q*(h*d+s)+min_C b_i.

For any proper C, the no-write protected cost dominates K(C), because an omitted guard exceeds every b_i and at least one fresh body costs k. Therefore

    A(C)=Omega+k+q*(h*d+s)+min_C b_i;
    D(C)=Gamma+(N-h)*k+S-s.

Different proper nonempty subsets have distinct (h,s): powers of two identify their nonzero members, and h determines whether zero is present. Lexicographic increase of (h,s) strictly increases A and strictly decreases D. At equal h, q>S dominates possible changes of min b; across h, d>S separates the guard-sum bands and k>S separates the protected-cost bands. The empty subset has (Omega+Gamma,Omega+Gamma), strictly smaller A and larger D than every nonempty proper subset. The full cached set has (Omega+k+Gamma,k+Gamma) and is dominated by leaving the b=0 job fresh. No proper-subset point is dominated by the full set. Exact frontier size: 2^N-1. This is also the maximum possible frontier size in the independent c=0 class: one canonical pair per subset gives at most2^N candidates, and making the final cached job fresh weakly improves both coordinates, removing the full-cached subset as a necessary point. The family attains2^N-1. Encoding size is O(N^2) bits. This is exponential in job count, not a claimed optimal exponential runtime in total bit length.

## Protected cost alone remains polynomial at B=1,c=0

This conclusion can use the original Section5 theorem with the body-work cap removed. Alternatively, in the full one-write representation change each fresh job to cached when optimizing protected cost alone. The new mismatch term at that job is at most the previous no-write/prefix-protected bound, later mismatch terms lose that fresh body, and no-write protected cost decreases. With all jobs cached, P_t=max_i(prefix g+w_i). For any DAG, Lawler's inherited precedence algorithm with processing g_i and tail w_i minimizes it. This is a different objective from the NP-complete joint total/protected cap problem. The statement does not cover c_i>0 or arbitrary B,r.

## Interpretation limits

This theorem identifies a boundary caused by adding guarded-entry charges to TOTAL work, even with free comparisons. It does not show that the previous dummy-family c-only transition was false: in that restricted family c=0 still collapses its frontier. Costs here are specified mathematical weights, not native timing calibration. Mixed source results and the Major Revision187 verdict remain. No acceptance or SE importance is established by this derivation.

## Fixed checks and scope

Fixed01 compared764 independent inputs with390,378 order/mask pairs and26,254 cap queries;836 uniform inputs with43,565 cap queries and7,692 count-DP thresholds;55 subset embeddings over420 targets (339 yes,81 no); and eight output families N2..9 with1,012 frontier points and5,116 interpreted paths. All declared comparisons agree; all seven deliberate alterations are detected. Greedy02 is a new algorithm check using the same836 uniform inputs,3,780 reduced thresholds and43,565 stored cap queries; all agree, including concrete witnesses. Its omitted-baseline alteration is detected. Populations overlap, and finite agreement does not prove the all-program or asymptotic statements. The original body-W comparisons-free complexity and general-DAG strong hardness remain separate questions.

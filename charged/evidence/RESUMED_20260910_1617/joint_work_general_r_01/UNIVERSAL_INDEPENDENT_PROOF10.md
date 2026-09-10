# Least universal total-work curve for independent jobs: corrected proof10

Author mathematical result, following DRAFT09 and a separate author proof inspection. All earlier drafts/results and uncertainty statements remain historical records. This proof does not establish novelty, acceptance, or mechanical/source-level verification. It applies to the explicit completion-program contract in PROOF02 and INDEPENDENT_PROOF07; only the attaining policy's ordering needs independence. A zero-write matching record is charged counterfactually when a useful own-gate fresh write invalidates it, whether or not the actual fresh-write branch selects that record. No record is computed for free at the common start.

Let positive works be sorted a1<=...<=an, Omega their total, Top_m the sum of the m largest works (Top_0=0, saturated at n). Let V_r consist of deterministic B-independent programs that complete with Q<=n+r in every finite-write environment and achieve L(P,E)<=Top_(B-r)+ for every B and globally B-bounded environmentE. This is the simultaneous optimal-protected-work class, not the class of all universally terminating policies.

For independent jobs, define

    F_r(B) = Omega+B*a_n,                                      if 0<=B<=r;
             Omega+max_{1<=m<=min(B-r,n)}(r*a_(n-m+1)+Top_m),     if B>r.

Then for EVERY P in V_r and EVERY B>=0, worstW_P(B)>=F_r(B). ONE P in V_r attains equality simultaneously at all B: execute jobs in ascending work order, prepare/cheap until r cheap failures, then prepare/cached for every unfinished job. This establishes a least attainable vector, not equality of all optimal-protection policies' W curves. The policy observes no B, values, work counter, clock or cached comparison Boolean. It needs only cheap success/failure and the fixed ordering. Hence the same independent-job optimum holds if cached observations are fully erased.

## Upper bound and witnesses

Every failed cheap call needs a distinct invalidating write since its immediate preparation. Cached mismatches require further disjoint intervals. There are at most r cheap failures, so Q<=n+r for every finite write pattern. The standard protected-work bound gives L<=Top_(B-r)+; writing r times at the first job of a suffix of the p=min((B-r)+,n) heaviest jobs and once at each subsequent cached comparison attains Top_p. For B<=r there is no protected mismatch and L=0.

For B<=r, at most B failed preparations each cost at most a_n; no cached mismatch can add work, so W<=Omega+B*a_n. Match all smaller jobs, fail cheap B times at the largest job, then stop writing and complete it. This attains the bound even when B=r; the safe completion then uses cached. At B0 it is just mandatoryworkOmega.

For B>r, first consider a run that switches at job j. All preceding jobs matched cheaply, and all cheap failures were at ranks<=j. Thus their duplicate preparations cost at most r*a_j. If m>=1 cached mismatches occur, they involve m distinct jobs in suffixj..n, so j<=n-m+1; their total work is at most Top_m. Also m<=B-r. Therefore W-Omega<=r*a_(n-m+1)+Top_m, bounded by the displayed maximum. If there is no switch or m0, duplicate work is at most r*a_n, strictly below the m1 term (r+1)*a_n. For any permittedm, match the first n-m jobs, fail cheap r times at job n-m+1, then mismatch all m remaining cached completions. This uses r+m<=B writes and attains its term. Choose a maximizingm forW; choosingp forL may select a different path. The maximizingm need not be largest: for works(1,100),r1, termsm1/m2 are200/102.

## Full-program lower bound at B>r

Fix m in1..min(B-r,n), and target exactly the m heaviest jobs. At selected target comparisons whose zero-write continuation matches, the adversary installs a never-used own-key identity; elsewhere it writes nothing. Let f count these useful cheap failures, c useful cached mismatches, t all target completions, and d all writes. Stop permanently after f=r+1 or t=m.

At every completed-operation boundary, d=f+c and c<=t. Before a further write, f<=r and t<=m-1, so d+1<=f+t+1<=r+m. Thus the adversary is globally(r+m)-bounded, including on programs/plays that violate admissibility. The stop rule does not derive its environment bound from P's promised call cap.

For admissibleP, reaching f=r+1 would require n completing calls plus at least r+1 failures and is impossible. Globally finite writing and admissibility force every target eventually to complete. Before all targets complete, a matching target comparison is invalidated; a stale cheap call neither completes nor receives a write. Consequently each target completes protectively, by fresh, stale cached, or useful cached mismatch. Hence L>=Top_m.

Let d<=r+m be the actual write count on this complete execution. Cap this same adversary unconditionally at d. This preserves the complete execution: every write it originally made remains within the new cap, and there were no later writes on that play. The resulting environment belongs to E_d globally. P's simultaneous guarantee therefore gives

    Top_m <= L <= Top_(d-r)+.

Positive works imply d-r>=m. Together with d=f+c<=r+m, f<=r and c<=t=m, this forces d=r+m, f=r and c=m. Thus every target completion is a useful cached mismatch; fresh/stale cached target completion is ruled out by the guarantee, not assumed away. Any additional stale cheap failure would also exceed the call cap.

Global counterfactual-matching-record charging supplies one distinct duplicate kernel for each of the r useful cheap failures, all at targets of weight>=a_(n-m+1), and for each of the m distinct cached mismatches, whose total is Top_m. It also supplies mandatoryOmega from the common start. Therefore W>=Omega+r*a_(n-m+1)+Top_m. This environment is allowed for every B>=r+m; maximizing over permittedm proves the lower formula.

## Early budgets from a truncated maximum-job witness

Apply the preceding construction withm1. Its complete witness has exactly r useful cheap failures at a maximum-work job and then that job's useful cached mismatch. For0<B<=r, cap that adversary after its firstB writes. The identical prefix already invalidated B distinct paid preparations of the maximum job, which is still unfinished. No foreground operation or later restricted write can restore their identities. Eventual completion in this globallyB-bounded environment needs an additional distinct kernel for that job, and every other job still owes a distinct completing computation counted globally from the common start. Thus W>=Omega+B*a_n. B0 uses mandatoryOmega. This argument avoids presupposing which free/stale actions an arbitrary program would attempt next.

## Complexity, scope and comparison

Sorting, Top prefix sums and prefix maxima over m construct F_r inO(nlogn) comparison/arithmetic operations, plus its at mostr initial linear segment; a query uses the precomputed max atmin(B-r,n). Representing the initial segment analytically does not require enumerating r coordinates. Exact arithmetic bitcosts depend on weight encoding. No polynomial claim follows for arbitrary-DAG positive-r frontiers or their universal least curves. The lower bound holds on any DAG, but ascending attainment may be illegal. At r0 every ordering uses cached from the outset, so F_0(B)=Omega+Top_B on any DAG, recovering the earlier theorem.

The informed optimal-L independent corner from07 has k=n-p forp=(B-r)+<n, hence workOmega+min(r,B)*a_(n-p)+Top_(p+1)-a_n; whenp>=n it isOmega. ForB<=r its difference fromF_r iszero. AtB=r+1 andn>=2 the simultaneous unknown-budget contract costs an additional(r+1)*(a_n-a_(n-1)); forn1 the informed saturated corner isOmega and the gap is(r+1)*a_n. These are differences between specified optimal-protection policy classes, not an unrestricted pointwise information lower bound.

## Fixed corroboration

UNIVERSAL_PROTOCOL09 preceded formula comparisons. Retrospective117 independent roots and237 r0DAG roots (39 overlap) agree. The separate fixed647 independent roots span n1..4/weights1,2,4,7,11/r0..3 plus n5/weights1,3,9/r0..2 andn6/weights1,2,4/r0..2. Every all-ready-job universal Pareto oracle frontier has the displayed least vector;34,814 independently interpreted policy paths attain the exactW/Lcurves and call cap. All paths/results/errors andhashes are retained. These finite checks cannot establish the all-program lower bound; they check its formula and attaining implementation. Earlier arbitrary-chain and intermediate-continuation counterexamples remain and are not contradicted by the independent-job theorem.

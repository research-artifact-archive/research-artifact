# Candidate closed independent frontier for every retry allowance and write budget

New author extension of INDEPENDENT_FRONTIER04, September10,2026. Fixed before evaluating this formula against general-r rows. The r0 predecessor remains unchanged and was not yet executed as a separate retrospective analysis. This claim needs symbolic critique; finite agreement will not serve as its proof.

Sort positive works a1<=...<=an, let Ak=sum_(j<=k)aj,A0=0,Omega=An. For supplied B,r>=0 put h=min(r,B), p=B-h=(B-r)_+. If p>=n the frontier is the all-fresh point(Omega,Omega). Otherwise define, for k=1,...,n-p,

    Ck = h*a_k + A_(k+p-1)-A_(k-1),
    Lk = Omega-Ak.

When p=0 the prefix difference is empty and zero. Candidate complete independent-job frontier: ND of(Omega,Omega) and all(Omega+Ck,Lk). At B=0 everyCk=0 andk=n gives(Omega,0), dominating the rest. At r0 this reduces exactly to04; its last k=n-B is the earlier independent optimal-L corner. Construction is O(n log n) sorting plus a linear prefix sweep for a requested(B,r), with at most n-p+1 candidates.

## Policy and upper bounds

Process in nondecreasing work order. Count unprotected matching COMPLETIONS s and failed/mismatching comparisons d. Use immediate prepare/cheap until r cheap failures, then immediate prepare/cached. Stop this main phase at the FIRST of s=k or d=B. If s=k, finish every remaining job fresh. If d=B, immediate prepare/cache the entire unfinished suffix; within the supplied B all these calls match. For B0 go directly to the latter phase. No job chosen for fresh is prepared beforehand. The controller receives cheap success/failure and the cached comparison Boolean; it never receives the actual write count. Different writes can be invisible, so d is a conservative lower bound on writes spent. The suffix uses cached to preserve Q outside B without claiming the W/L caps there.

At most h=min(r,B) cheap failures occur before the suffix, so Q<=n+h<=n+r. If s=k, at least k jobs complete unprotected, so at most n-k jobs contribute to L, bounded by Lk. If d=B before k matches, at most p cached mismatches protected work and no later work is protected; since p<=n-k the same bound holds. The no-write path matches the k smallest jobs then fresh-completes the rest, attaining Lk (except B0, whose all-safe suffix attains the sole nondominated point).

Every cheap failure in the main phase is at a job of rank at most k: before cached mode all completions are matches, and s<k. Hence those duplicate preparations cost at most h*a_k. If B>r and cached mode is reached, exactly r=h cheap failures preceded it. Before the m-th cached mismatch there have been at most k-1 matching completions; hence that mismatch's job rank is at most k+m-1. At most p such mismatches occur. The largest possible sum of their m<=p distinct ascending weights is a_k+...+a_(k+m-1), at most the window sum in Ck. If the main phase stops earlier in cheap mode there is no cached duplicate and the same bound holds. After d=B no duplicate occurs within the promise. Thus worst W<=Omega+Ck.

For B>0, k-1 initial cheap/cached matches followed by h cheap failures of job k and then p cached mismatches at ranks k,...,k+p-1 realizes duplicateCk. If p0, h=B and exhaustion directly gives the safe suffix, including the failed job. If h0 use cached from the outset. There are enough jobs becausek+p-1<=n-1 forp>0, andk<=n forp0. These witnesses attain W. Separate maxL andmaxW need not share a path.

## Full-program target lower bound

For each k, targetTk=ranksk,...,n. A globally B-bounded adversary writes a fresh own-key identity only at a target comparison whose zero-write continuation MATCHES, until B writes are spent, and nowhere else. Already-stale cheap calls consume no adversary write and already-stale cached calls protect their job without consuming a write. This useful-comparison restriction avoids wasting a write on an already-invalidated preparation. If all targets complete protectively then L>=Omega-A_(k-1). Otherwise a target's unprotected completion needs a matching comparison after all B writes are exhausted. Of the B earlier writes let f be cheap failures and m=B-f cached completing mismatches. The call cap gives f<=r, hence f<=h; cached mismatches are at distinct target jobs. Every cheap failure invalidates a distinct paid counterfactual-zero-write matching preparation; every cached mismatch duplicates its target job. The global per-version argument from PROOF02 gives duplicate work at least

    f*a_k + sum_(j=k)^(k+B-f-1) a_j.

Only feasible f occur: if too few targets exist for B-f distinct mismatches, that unprotected-completion case cannot happen. Over feasible f this expression is nonincreasing as f increases, because replacing its last window weight by a_k cannot increase it. Its minimum is bounded below by its value at h, namely Ck, for which the window exists (p<n-k+1). Therefore

    worstL < Omega-A_(k-1)  =>  worstW >= Omega+Ck.

The Ck sequence is nondecreasing: C_(k+1)-Ck=h*(a_(k+1)-a_k)+(a_(k+p)-a_k) forp>0, and h*(a_(k+1)-a_k) forp0. Given extra-work allowance M, belowC1 the bound forcesL>=Omega. Otherwise take the largest k withCk<=M. If a next k exists its target inequality forcesL>=Omega-Ak. At the last k, the previously proved optimal-L lower bound Top_p gives the same conclusion. The attaining policies prove the complete frontier; duplicate tied thresholds are handled by nondominance. The all-fresh point and p>=n saturation use the mandatory Omega work and prior Top_p lower bounds.

## Stronger topology/observation corollary when r>=B

Here h=B,p0,Ck=B*a_k. The same target lower bound holds on ANY DAG. Upper bounds need no ascending execution: choose the k smallest jobs as cheap, the rest fresh, execute ANY topological order until B cheap failures, then safe prepare/cached for all unfinished jobs. Cheap failures can only duplicate selected jobs of weight<=a_k, total<=B*a_k. Protected work is at most the sum of unselected worksOmega-Ak and the no-write path attains it. A repeated-write witness at a maximum selected job attains the work cap. The policy branches only on cheap failure, so it needs NO cached comparison Boolean, even for fully erased constant outputs. ForB>0, the exact cap form on every DAG is

    min worstL subject to worstW<=Omega+M = sum_(i:B*wi>M)wi.

B0 is(Omega,0). This extendsONE_WRITE_RETRY03 without claiming that one extra retry absorbs arbitraryB. Sufficient retry slack removes precedence/Boolean dependence from this particular supplied-budget resource frontier, not from every continuation or every unknown-budget contract.

## Fixed retrospective analysis protocol

Read all independent-job rows of the original96795-case archive, all n1..4 weights{1,2,4}, r0,1,2 andB0..n+r, exactly1,998 cases (sum_n3^n*(3n+6)). Compare the formula's COMPLETE frontier to both archived immediate and retained frontiers, retaining all thresholds, inputs and results. Also inspect every archived DAG row with r>=B, exactly32,526 cases (5,421 inputs times1+2+3 budget cells), against the all-DAG corollary. Overlap is intentional and identified; do not add these as distinct native/exploratory inputs. Preserve all errors and hashes, no original rerun. This analysis is retrospective. If it survives, a separately fixed prospective check should use wider integer weights, independent direct policy-path interpretation and selected arbitrary-program operation cases; no automatic favorable repetition.

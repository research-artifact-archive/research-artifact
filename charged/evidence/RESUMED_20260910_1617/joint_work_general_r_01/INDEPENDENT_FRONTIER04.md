# Supplied-budget complete r0 frontier for independent jobs: analytic candidate

New author deduction, September10,2026, after inspecting existing small frontier rows. This is not a previously unseen preregistration. Do not adopt from finite agreement alone. Preserve all old independent-corner and DAG statements.

Let a1<=...<=an be positive job works, Ak=sum_(j<=k)aj, A0=0, Omega=An. For independent jobs, supplied1<=B<n, r=0, define for k=1,...,n-B

    Ck=A_(k+B-1)-A_(k-1),
    Lk=Omega-Ak.

Candidate: the complete full-program Pareto frontier is the nondominated set of all-fresh(Omega,Omega) and (Omega+Ck,Lk). At B0 it is(Omega,0), and at B>=n it is(Omega,Omega). The latter saturated case follows the positive-work lower bound on L; do not infer it merely from an empty candidate range. Construction takes sorting O(n log n) and a linear sweep of prefix sums, plus O(n) policy storage per selected k. No theorem about adaptive ordering or general DAG frontiers is implied.

## Attaining policy

Before either stopping condition, process jobs in nondecreasing work order using immediate prepare/cached. Stop this comparison phase when either k MATCHES have been observed or B MISMATCHES have been observed. If k matches occur first, finish the remaining jobs fresh. If B mismatches occur first, prepare/cache the remaining jobs; within the supplied B budget all those calls match. Cached after budget exhaustion maintains Q=n outside the promise too, without asserting W/L caps there. The two stopping conditions cannot be reached at the same call.

When k matches stop the phase, at least k jobs complete unprotected, so no more than n-k jobs contribute to L; their total is at most the n-k heaviest works, Lk. When B mismatches stop it first, no later work is protected, so L consists of at most B<=n-k works and is bounded by Lk. The no-write execution first matches the k smallest jobs, then fresh-completes the remainder, attaining Lk.

All duplicate executions happen before B mismatches or k matches. On a path with d<=B mismatches before k matches, the last mismatch's position is at most k+d-1, hence its d weights sum to at most the last d weights of that prefix, a_k+...+a_(k+d-1)<=Ck. If B mismatches stop first, their B largest possible positions are k,...,k+B-1, giving the same Ck bound. A witness with k-1 initial matches then B mismatches attains Ck. Hence separate worst W and L are exactly Omega+Ck and Lk. Costs from fresh nodes never include a speculative preparation.

## Target-set lower bound

For k=1,...,n-B let Tk={k,k+1,...,n} in sorted-rank indices. Fix a globally B-bounded adversary that writes a never-before-used own-key identity at each selected comparison of a target until B writes are spent, and nowhere else. Under r0 every selected cheap call with a possible fresh-write failure is inadmissible. If all targets complete protectively, L>=sum_Tk wi=Omega-A_(k-1). If a target completes unprotected, its comparison can match only after all B writes have been spent. Each earlier fresh write caused a cached completing mismatch of a distinct target. The original full execution therefore paid at least B additional target kernels, whose sum is at least the B smallest weights in Tk, namely Ck. Retained records, late record selection and prepaid computations are handled by the existing global per-job argument; freshness invalidates every prior record, and the counterfactual matching preparation was paid before the gate.

Thus every full program with worst L<Omega-A_(k-1) must have worst W>=Omega+Ck. The Ck sequence is nondecreasing, since C_(k+1)-Ck=a_(k+B)-a_k>=0. If a total-work allowance M lies below C1, this lower bound forces L>=Omega. Otherwise let k be the largest index with Ck<=M. If k<n-B, the next target-set bound forces L>=Omega-Ak=Lk because M<C_(k+1). If k=n-B, the established optimal-L lower bound Top_B=Omega-A_(n-B) gives the same conclusion. The attaining policies prove equality, including tied Ck values handled by nondominance. Therefore the stated complete frontier follows, subject to author critique.

## Retrospective corroboration protocol (not yet executed)

Read every existing r0 independent-job row from ROWS01.jsonl: n1..4, all weights{1,2,4}^n, B0..n. Exact denominator3*2+9*3+27*4+81*5=546. Compare the closed threshold set to BOTH saved complete immediate and retained frontiers. Preserve every input, threshold and disagreement. No re-execution of scientific inputs; one analysis attempt, full hashes. In a separate prospective successor if this survives, larger integer-weight independent inputs and an independent direct interpreter should test the new stopping policy, including tied thresholds and saturation. Finite agreement is not a general proof or a new scheduling-method claim.

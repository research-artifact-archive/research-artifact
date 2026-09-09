# Author proof: cheapest-ready optimality within the global-threshold family

Scope is the exact restricted family in PLAN.json: no retained speculative preparations, all jobs fresh before each selected attempt, only cheap calls until r global failures, then only cached completions. We now permit arbitrary adaptive next-job choices, including after failure, and permit B to the comparison policy. The candidate minimum-work ready selector receives no B. This is not all-program optimality and does not establish the broad importance of the paper.

Write X(S,b,t) for minimum worst extra work over the mandatory sum of the works of unfinished jobs. The direct recursion in PLAN.json applies. Its terminal t=0 value is Top_b(S), independent of job order. Its b=0 value is0.

First X(T,b,t)<=X(S,b,t) whenever T is a subset of S (absent predecessors treated as complete). Simulate a strategy for S on T, virtually completing omitted jobs with successful zero-extra-work attempts. These virtual completions spend no failure or slack, and every selected retained job is physically ready. The virtual execution's extra work equals the physical extra work, and it is among the original adversary's executions. Taking worst cases and then infima yields the inequality. In the cached phase the same argument also follows from Top_b subset monotonicity. The simulation is finite because every virtual success removes an omitted job.

Now let i and j be ready in S with w_i<=w_j, b,t>0. Any policy selecting j first has optimal continuation value

Y_j=max(X(S-j,b,t),w_j+X(S,b-1,t-1)).

Consider selecting i first, and on success selecting j next before optimal continuation. The failure of i costs at most Y_j, since w_i<=w_j. If i succeeds and j fails, cost w_j+X(S-i,b-1,t-1)<=Y_j by subset monotonicity. If both succeed, X(S-i-j,b,t)<=X(S-j,b,t)<=Y_j. Thus an i-first policy is no worse than the j-first optimum. Optimizing its continuation can only improve it. A least-work ready job is therefore optimal at every state.

Repeated least-ready selection is a stationary rule independent of b and t while t>0, so one implementation simultaneously attains all these finite-budget optima. A failure changes neither readiness nor the weights, so it repeats the same current job. Its work formula is the previously proved fixed-greedy formula. Empty DAG has zero cost/calls.

This exchange is an instance of the already-used cheapest-validation dominance argument. It extends the stated comparison class from fixed orders to adaptive selections within this threshold family; it does not by itself supply a new general synthesis contribution. A numerical check reuses5519 observed cases and176608(B,r) roots, all equal. Numerical agreement is separate from this proof and is not a new native measurement.

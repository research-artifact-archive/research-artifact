# Exact resource maxima of the implemented policy

This subsequent author proof interprets already-observed native results. It does not change PLAN.md, inputs, equations, outcomes or denominators and does not claim a new evaluation population. Use the interface and work accounting of the paper and the universal policy theorem. Fix a topological order pi. The policy repeatedly attempts the current job until it completes, then advances to the next job in pi. It makes fresh cheap attempts until r cheap failures globally, and then freshly prepares and cached-completes all remaining jobs (three modes), or fresh-protected completes them (two modes). Successful cheap attempts do not decrement r. This is the implemented least-ready rule. Merely fixing completion order in an arbitrary causal program is insufficient for these formulas.

Let Omega=sum w_i, wmax=max w_i, M_i=max_(j<=i) w_pi_j, and S_i=(w_pi_i,...,w_pi_n), including position i. Write Top_k(S) for the sum of the largest min(max(k,0),|S|) works.

Both families have Qmax=n+min(B,r). In two modes:

```
Wmax = Omega + min(B,r)*wmax.
Lmax = 0 if B<r, otherwise Omega.
```

Every cheap failure adds one kernel and consumes one distinct write; all such failures can be placed on a maximum-work job. The L maximum is attained by placing all r failures at the first job and then protecting every job, whenever B>=r. These component maxima need not share an execution.

In three modes, Lmax=Top_(B-r)(all works), and

```
r=0:          Wmax = Omega + Top_B(all works).
r>=1, B<=r:   Wmax = Omega + B*wmax.
r>=1, B>r:    Wmax = Omega + max_i [(r-1)*M_i + w_pi_i + Top_(B-r)(S_i)].
```

For r=0 each cached mismatch adds one whole kernel and completes its job; invalidate the largest min(B,n) jobs. For B<=r, all extra work consists of at most B cheap failures, placed on a maximum-work job; at B=r the subsequent fresh cached preparations match because no writes remain. For B>r, if the rth cheap failure occurs at i, previous r-1 failures cost at most (r-1)M_i, the last costs w_pi_i, and at most B-r cached mismatches occur at distinct suffix jobs, costing at most Top_(B-r)(S_i). Each i is attainable by placing r-1 cheap failures on a prefix-maximum job, completing intermediate jobs, failing cheaply at i, then invalidating the largest suffix jobs. A path that never reaches r failures adds at most (r-1)wmax, dominated by the i=n term. Disjoint fresh read-to-comparison intervals charge the failed attempts to distinct actual writes. Dependency order remains legal throughout.

All 1,280 complete finite path groups and 17,200 original native replay records match all W,L,Q formulas. Native works are eight times the declared weights. Concurrent records and intentional controls retain their original study outcomes and are not part of these complete-path maxima. General all-program W optimality is asserted only by the separate r=0 theorem restricted to simultaneous protection-optimal programs. No scalar maximum is computed by adding these separate component maxima.

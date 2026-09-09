# Work required by simultaneous protection optimality

This is a subsequent author proof, not a new measurement or a retrospective preregistration. The original candidate, analysis, raw records and results are unchanged. Adopt the paper's whole mandatory kernels, no initial preparations, fresh nonreused input identities, single-job atomic calls, no retained guard across calls, no outside completion, no cross-job completion, persistent completed outputs, and eventual foreground scheduling and operation completion. Every foreground validation/publication or callback call counts in Q, including a noncompleting call. Let all w_i>0, Omega=sum w_i, and Omega_k sum the largest min(k,n) works.

Let U_3(0) consist of causal three-mode programs that receive no writer bound and complete every finite-write environment with Q<=n. Let V be its subclass with sup_(writes<=t) L <= Omega_min(t,n) for every integer t>=0. For every integer B>=0,

```
inf_(P in V) sup_(writes<=B) W(P,E) = Omega + Omega_min(B,n).
```

A policy that freshly prepares and cached-completes any ready job attains the equality simultaneously for every B. It uses Q=n and W=Omega+L; at most B distinct cached completions can be invalidated. It does not receive B, prices or work weights.

For the lower bound fix P in V and k=min(B,n). Target the k largest jobs. Each counted call must complete one job: otherwise n persistent single-job completions require Q>n. For each target's first counted call, inspect the history immediately before the atomic comparison/acquisition boundary. If its whole kernel has previously been executed outside protection, using any retained or discarded preparation, insert one fresh own-key write at this boundary; otherwise insert none. Make no other writes. The rule uses only past events and at most k writes. A write invalidates every prior preparation. Therefore each target must execute its whole kernel inside its completing call, either because its preparation was invalidated or because it has no preparation. A rejectable call cannot be chosen: failure under this finite environment would violate the universal call cap.

Let h<=k be the actual number of writes in this execution. Then L>=Omega_k, while membership in V implies L<=Omega_h, applying its all-t guarantee at t=h after the execution. Positivity forces h=k. Thus every target had already paid one whole kernel before its completing call, and pays another inside it. All other jobs still pay their mandatory work, so W>=Omega+Omega_k. This proves the bound for every DAG and programs retaining arbitrarily many preparations.

The restriction to V is essential. Unknown B alone does not force this W curve. For the two-job chain with works 8 then16, use cached completion first; if it matches, protect the next job, and if it mismatches, cached-complete the next job. This B-unaware policy has Q=2 universally and worst (W,L)=(32,16) at B=1, but incurs L=16 at B=0 and hence is outside V. The all-cached policy has worst (W,L)=(40,16) at B=1 and L=0 at B=0. Component maxima may occur on different paths. This result is a cost of simultaneous protection optimality, not a full Pareto characterization or a timing claim.

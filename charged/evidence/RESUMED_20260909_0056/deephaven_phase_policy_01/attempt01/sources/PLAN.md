# Cycle-phase policies — exploratory plan before new computed/native outcomes

Primary route SCIENTIFIC. The completed216-cell prefix experiment remains unchanged. Its424 tight execution establishes the worst cost of that particular flat-budget compiled policy on one native script; it does not establish a lower bound on all native mode policies. This new investigation tests whether the phase of a bounded update cycle permits a better policy.

The native domain and selected-operation caps remain exactly deephaven_prefix_import_02: K4,V104, immutable balanced31-node structure, value-only updates, fixed viewport16 and synchronous writer cuts. The sole control choice is FAST or PROTECTED at an existing callback boundary. There is no independent wait/acquire/release action. These omitted actions would require a broader model and could further improve work at unpriced waiting/locking cost. A protected call while Updating waits for the cycle to complete before its body. The current harness drains that cycle explicitly before acquiring the lock.

Let r be the remaining permitted cycle starts and z=0/1 indicate Idle/Updating. Initial state is r=q,z=0. Success of a FAST call removes a job and keeps the phase. A failed FAST from Idle may end Updating with r-1, or Idle with r-1. From Updating it may end Idle with r, or Updating with r-1. Multiple cycle boundaries may occur within a body; their dominance has to be proved, not assumed by an exact-native claim. PROTECTED removes a job and ends Idle with the same r. Every body has a selected-operation cap w; protection adds declared p=lambda*w. Full-body END updates can realize these abstract failure outcomes in the fixed driver.

First explore a finite-budget DP over unfinished masks, r and z using ALL single-cycle-end branches (including FULL and COMPLETE+START); optionally include every legal boundary sequence up to r to test dominance. The proposed simplified recurrence is, for r>0,

F0(S,r)=min_ready_i min(p_i+F0(S-i,r), max(F0(S-i,r),w_i+F1(S,r-1))), F0(S,0)=0;
F1(S,r)=min_ready_i min(p_i+F0(S-i,r), max(F1(S-i,r),w_i+F0(S,r))).

Its monotonic interlacing and equality to the full phase game are hypotheses for author checking. Decisions will record the actual phase, remaining starts, and full value. This first implementation may use a finite r-sized DP; it is not the existing all-budget compiler import and must not be reported as such. An all-budget representation is a later investigation.

Pre-computation/native prediction from the proposed recurrence: with lambda3,q2,W4,104 the initial phase-aware worst-work cap is420, versus424 for the existing flat2q compiler. On the existing cross_stage script, after the first K failure caused by START, a phase-aware rule protects K, draining the open cycle; the predicted path costs332 rather than424. The hypothesis may be refuted by the full model, the actual callbacks or the source review.

The native follow-up, if the DP checks support the candidate, will fix lambda1,3,10 and all12 prior scripts, comparing phase DP with both tie choices against a local rule receiving the same r,z information (fast iff2r+z<=lambda, fast on equality). The full matrix is108 cells. All fixed new cells, failure/timeout/invalid outcomes and unchanged prior216 cells remain reported. Prior policies are not rerun merely to improve their results. No claimed population frequency, elapsed-time improvement, whole-program optimality or independent review follows from this exploratory matrix. Native execution requires a later input manifest and bounded one-shot attempt.

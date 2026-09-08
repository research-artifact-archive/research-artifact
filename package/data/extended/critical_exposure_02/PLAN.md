# Common protection ratio: expanded falsification search

Exploration only, following critical_exposure_01's zero observed adaptive-order
gaps. Its 27,105 units remain unchanged. The earlier physical-work motivation
was incorrect; see critical_exposure_01/MOTIVATION_CORRECTION.json. The current
native implementation ALREADY uses work plus weighted protected work. This
study restricts existing heterogeneous weights to one common ratio p_i/c_i;
it does not introduce a newly validated physical or application cost model.

Freeze 65,536 n=4 units: every upper-triangular DAG, work in {1,2,3,5}^4,
and lambda in {3/2,5/2,3,5}. Add 1,024 n=5/6 units: 128 deterministic
seeded DAG/work cases per n times the same four lambdas. Among each 128,
first16 are antichains; the remainder cycle edge probabilities .1,.3,.6,.9.
Seed 202609080730; costs are sampled from integers1..31. Costs are doubled:
c_i=2w_i, p_i=2lambda*w_i. Retain duplicate/coincidence IDs before execution.
No exact case duplicates against critical_exposure_01 are expected because
these lambdas are disjoint. No units are silently removed.

Budgets are all integers0..max(4,sum ceil(p_i/c_i)). For every unit construct,
serialize, reload and check an all-budget certificate using the policy-aware
sweep checker or the existing packed ordered checker as applicable. Compare
the roots with the unchanged separately implemented scalar ideal Bellman DP;
enumerate EVERY topological order and compute its scalar fixed-order optimum.
Report any strict gap; a zero finding is no universal fixed-order theorem.
A budget-dependent best fixed order is not one common order for all budgets.
Save the full best-order-by-budget vectors so that distinction is inspectable.

One run, 5-second per-unit and600-second total cap, all SUCCESS/FAILURE/TIMEOUT/
INVALID/NOT_RUN retained with artifacts emitted before later rejection. No
replacement, exclusions, case changes, or timeout reruns. All code, inputs,
runtime and delegated imported dependencies bound before execution. This is
an author-generated falsification search, not independent final evaluation.
No native experiments or human evaluation. Closeout at10:50JST; stop11:00JST.

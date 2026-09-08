# Strong B1 comparator: development plan

SCIENTIFIC author development, 2026-09-08 04:24 JST. The new B1 no-failure certificate makes an exact constraint-programming formulation possible without enumerating completion ideals. Investigate this as a strong single-budget comparator, not a replacement for all-budget compilation or a claimed contribution of the OR-Tools engine. A successful comparator may outperform the current compiler and that result must be retained. No runtime/input outcomes are yet observed for this formulation.

Install pinned OR-Tools9.15.6755 in an isolated project-local virtual environment. The default and bundled Python environments contain neither OR-Tools nor SciPy. Preserve installation logs, exact dependency versions/report and runtime paths; do not modify earlier environments or scientificsources. The official solver status definitions distinguish OPTIMAL, FEASIBLE, INFEASIBLE, MODEL_INVALID and UNKNOWN. Only OPTIMAL plus a valid independently scanned certificate counts as an exact answer. Timeout with a feasible incumbent retains that certificate and lower/upper bounds, not an optimum. No expected outcome/held-out/pre-result claim is attached to development examples; final comparison inputs and caps will be fixed separately after semantic conformance.

## Candidate exact formulation

Let P=sum_i p_i and choose Boolean h_i for protection. Use integer start t_i in[0,P], end e_i=t_i+p_i h_i, and optional positive interval [t_i,e_i) present iffh_i with sizep_i. Impose NoOverlap on protected intervals, e_u<=t_v for everyDAG edge, K>=sum_i p_i h_i, and t_i+c_i<=K wheneverh_i=0. Minimize integer K in[0,P]. Forp_i=0 forceprotection; empty/zero-premium instances may be handled explicitly. Allprotected is always feasible. Clock t represents cumulative protected premium, not elapsed computation time.

Every ordered B1 certificate produces a model by placing protected intervals consecutively and fast jobs at their preceding premium. Conversely, fast points inside a positive protected interval can be moved to that interval's start and placed before it: they cannot depend on the current protected job, whose end is later, and any intervening fast predecessors can be moved with them. NoOverlap guarantees earlier protected predecessors have already ended. Sort these normalized points and protected intervals by time, with a topological tie order placing available zero-duration jobs first. The extracted certificate's protected prefix is no greater than the original t_i, so its scan cost is<=K. This extraction argument needs explicit development/refutation, including endpoint ties, zero premiums, relabeling, diamonds and cases with a fast point inside a protected interval. Keep any counterexample.

The formulation solves onlyB1. It neither computes allbudgetcurves nor demonstrates that the current allbudgetcompiler is necessary when one budget is requested. Model construction, solve, extraction/check and serialization costs must all be included in later comparisons.

Primary API sources inspected before implementation:

- https://developers.google.com/optimization/cp/cp_solver
- https://developers.google.com/optimization/install/python
- https://github.com/google/or-tools/releases (pinnedv9.15.6755)
- https://or-tools.github.io/docs/python/classortools_1_1sat_1_1python_1_1cp__model_1_1CpModel.html

This is a draft implementation plan, not a frozen final evaluation protocol. No user/production application claim or correctness certificate is created by installing a solver.

# Partial repair with a common publication cost: exploratory check 01

Fixed before computation, 2026-09-10 06:22 JST. Author-side SCIENTIFIC exploration; no human evaluation, native timing calibration, or novelty certification.

The preceding partial_repair_01 interface is retained: one mandatory job with m independently prepared components, positive weights, a fixed family Γ of nonempty write footprints, only dirty-set observations, and at most q protected calls including final publication. Every rejection releases protection and prepares the job again outside. Versions are fresh; union damage resets after each preparation. Fresh whole protected execution remains allowed and costs W. This successor changes exactly one cost assumption: every successful publication, through any mode, incurs the same declared μ≥0 once. Protected loss is μ plus the repaired component weight (or W for fresh). Failed validation and outside preparation add no protected loss. μ is not measured Roslyn merge cost.

Already hand-derived hypotheses, not blinded predictions: known-budget optimum Kμ(B)=μ+G(floor(B/q)). At μ=0 finite competitive ratio forces zero extra loss at B<q and retry-first is optimal. Positive μ removes that necessity. For singleton unit components m=q=3, accepting one dirty component early may beat retry-first when μ>1. No numeric outcome has yet been computed for this successor.

Test an exact B-unaware deterministic compiler. Let c(D) be the minimum number of writes whose union is the observed dirty set D. The controller computes e=Σc(D) over observations without reading actual write count or B. Because any additional hidden writes only increase the known-budget denominator, each transcript's worst ratio uses its least consistent budget e. The proposed dynamic program is

V(left,e)=max_D min{(μ+w(D))/(μ+G(floor((e+c(D))/q))), V(left−1,e+c(D)) if left>1}.

q is the original call cap in the denominator. Fresh before observing is dominated by prepare-and-accept-any-D, since w(D)≤W and the same μ is paid. For μ=0 use 0/0=1 and positive/0=∞. The DP returns an action table indexed by remaining calls, the observable lower bound e, and D. The claim is finite deterministic optimality, not a trial-only weight-threshold normal form.

Inputs: every nonempty family of nonempty subsets for m=1,2,3; every ordered weight vector in {1,2}^m; q=1,2,3,4; μ in {0,1/2,1,2,4}. This gives 1046 footprint/weight instances and 20,920 parameter rows. Preserve every row, tie and failure. Additional declared controls: direct history-tree minimax without the e state quotient for all m≤2 parameter rows; exhaustive deterministic policy enumeration for m=2 singleton weights (1,2), q=3, μ=1/2 and 2; compare the μ=0 result to the prior exact competitive formula; compare retry-first both by explicit transcript DP and its profile formula. The script may report whether positive μ improves on retry-first and return the first strict witness. The m=q=3 unit example is also included explicitly (already hypothesized).

Internal time cap 170 seconds, process cap 180 seconds. A timeout/error is retained with completed denominator and is not relabelled SUCCESS. No exclusions, retries of unchanged input, or post-result input changes. This is a finite exact-arithmetic check supporting a separately reviewed proof; it cannot establish real application impact or nearest-work novelty.

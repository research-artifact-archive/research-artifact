# Uniform protected-computation exposure: price-restriction exploration

Motivation under investigation, not an established application fit: replace
artificial extra physical kernel work with a declared objective W + lambda H,
where W counts all whole-kernel work and H counts whole-kernel work executed
while conflicting updates are excluded. Lambda is a common nonnegative design
weight. This objective does not measure waiting, elapsed time, throughput,
actual blocked requests, or human effort. Existing native experiments and their
physical extra work remain exactly as recorded. No native outcome is relabeled.

At the abstract cost level this gives c_i=a_i=w_i and p_i=lambda w_i. The current
game formulas can therefore be reused after rational scaling. A concrete
refinement would still need to count incidental protection consistently and
satisfy the readiness/captured-output/write-bound conditions. This exploration
does not establish such a refinement or motivation by itself.

Question: under one common weight, does adaptive completion ordering ever
improve on every initially fixed topological order, and do policy choices
remain nontrivial? If not, report that loss of scope honestly. Do not treat a
zero finding on this grid as a universal theorem.

Freeze all n=1..4 upper-triangular DAGs, all work vectors from {1,2,4}^n,
and lambda in {0,1/2,1,2,4}: 27,105 case-weight units. All integer costs are
scaled by two: c_i=2w_i, p_i=q*w_i for q in {0,1,2,4,8}. Budgets cover
0..max(4,sum ceil(p_i/c_i)), including saturation and a zero-weight control.
Original case-price coincidences with the 4,232 final DAG inputs are recorded
before execution; these are author-generated/known structural families, not
new independent final evaluation samples.

Per unit, construct and JSON-reload an all-budget hybrid certificate. Check
the ideal route with sweep_certificate_02 (direct policy attainment), and the
ordered route with the unchanged packed checker. Compare every selected root
against a separately implemented finite scalar Bellman DP. Enumerate EVERY
topological order and compute each fixed-order optimum with a separate scalar
suffix recurrence. Check general optimum <= every fixed-order envelope.
Retain full budget vectors, the best order at each budget, exact objective
ratios, code/input hashes, and any emitted artifact (including an artifact
preceding a later rejection). No post-result case selection changes.

Count equality/strict-gap units and roots by n and lambda; give exact largest
gap witnesses. Initial normal work is sum c, so reported relative gaps use
(fixed-general)/(sum c+fixed). Prices are doubled objective units, not measured
CPU instructions. Saturation, lambda=0, and n<=3 zero-gap checks are explicit
regressions. Mathematical theorems are not proved merely by this finite grid.

One run, 2-second unit cap, 240-second total cap. Retain all SUCCESS/FAILURE/
TIMEOUT/INVALID/NOT_RUN, all IDs, and no replacement or exclusion. Preserve
earlier science; any correction is a new version with a recorded reason.
No human evaluation or public release. Closeout begins September8 10:50JST;
the active session stops at11:00JST. This is exploration, not final evaluation.

# Counting a cached mismatch twice: author boundary proof01

Keep the original pure whole-kernel operations, atomic gate/comparison/recomputation/publication semantics, visible cached Boolean, old raw snapshots, free inspections, paid retained records, deterministic programs and per-job persistence. Change only the call resource: cheap success, cheap failure, fresh completion and cached match each cost1; a cached mismatch costs2. Preparation costs no calls. Let Q' be this resource. At an operation boundary with u completions and z=#cheap failures+#cached mismatches,

    Q'=u+z;

hence a complete execution has Q'=n+z. Kernel W and protected body L are unchanged. A cached mismatch still completes atomically in the original operation; the doubled charge does not split its semantics into two separately interleavable actions. The supplied-bound and one-policy-for-all-budgets admissibility classes use Q'<=n+r. Global write budgets count external identity publications only, not controller completions, stale initial values or initially charged computation. No new normal-form restriction is imposed.

## Supplied writer budget

If B>r, the exact whole-program body frontier is {(Omega,Omega)} on every DAG. If B=0 it is {(Omega,0)}. If 0<B<=r it equals the original sufficient-retry frontier from Proposition5: under W<=Omega+M, least L is

    Omega - sum_{i:B*w_i<=M} w_i.

Equivalently, sweep M=0 and the distinct positive thresholds B*w_i, then remove dominated pairs. At each threshold an attaining policy handles the selected low-work jobs cheaply and all others fresh; after B cheap failures it may use freshly prepared cheap calls for every remaining job, since no write remains. The body/coordinate frontier is independent of precedence, subject to readiness.

For B>r, use the following globally bounded adversary. At any cheap or cached gate, write a fresh own-key identity only if the zero-write continuation would match. Do not write at fresh calls or already-stale comparisons. Stop writing permanently after z reaches r+1. At operation boundaries v<=z; before the next useful write while z<=r, v+1<=r+1<=B. This is unconditionally budgeted, including on inadmissible program histories. Every cheap call fails, and every cached completion mismatches. Admissibility and mandatory completion forbid z=r+1, because then final Q'>n+r. Therefore every completed job is fresh or cached-mismatching and protects its whole body. Finite-write completion forces every job to finish, so L>=Omega; mandatory charged body work gives W>=Omega. All-fresh attains both simultaneously.

For B<=r, Q'>=Q implies inclusion in the original admitted class and therefore inherits its frontier lower bound. The original sufficient-retry attaining policy spends at most B failures, each requiring a distinct write. Its cached suffix follows B failures and consists entirely of matches, so Q'=Q. Equivalently replace that known-zero-write suffix by fresh-preparation/cheap calls; it then literally uses only cheap and fresh. Thus it also attains the old frontier under Q'. B=0 follows directly from all cheap just-in-time preparations.

## One unaware policy at every finite writer budget

The least worst protected-body curve is

    U'_L(B,r)=0 if B<r; Omega if B>=r.

One policy attains the whole curve: use fresh-preparation/cheap calls until r failures, then complete every remaining job fresh. It completes with Q'<=n+r in every finite-write environment. If B<r the switch is never reached and L=0. Otherwise L<=Omega, with r failures at the first chosen job attaining Omega.

For the lower bound at B>=r, run the preceding reject-all-comparisons adversary but impose an unconditional cap of r bad outcomes, and therefore at most r actual writes. Before that cap every completion is protected. If all jobs complete earlier, L=Omega already; the argument never requires the rth bad event to occur. After r bad outcomes, if an unfinished job remains, no further cheap/cached call is compatible with universal admissibility: an already-stale comparison is bad immediately, or one further fresh write makes it bad in a different finite-write environment. That hypothetical extra write is not added to the realized lower-bound execution. Thus all remaining completions are fresh and L=Omega. Free inspections and retained records cannot remove the selected-operation write gate; endless free activity contradicts completion in a finite-write environment.

At r=0 this gives unknown optimum L=Omega even at B=0; supplied B=0 still gives L=0. For one job and 0<B<=r, the supplied frontier is {(w,w),((B+1)w,0)}. These are different resource contracts, not counterexamples to the original Q theorems.

## Interpretation

The original primitive gives a cached mismatch one atomic completion call. If a consumer charges its recomputation as another resource unit, the tight guarantee changes as proved above. An implementation must state the semantic primitive and counted resource together. This is an illustrative alternative charge model; it does not assert that Q' equals every native API-call count or model two non-atomic APIs. The Linux public-invocation and six-primitive count results remain the measured source conventions. The read-only author check found no counterexample and required the explicit finite-completion and already-stale qualifications retained above.

# Candidate scope extension: positive guard-entry charges

Author derivation before dedicated finite checks. This is a new resource extension motivated by the Linux comparator, not an already-established main claim. The original whole-kernel results and native raw results remain unchanged. No native elapsed charge is calibrated here.

Keep the paper's whole-kernel game, observations, persistent completion and Q≤n+r. A cheap conditional publication charges no guard; each fresh/cached completing operation charges g_i≥0 for its job, even on a cached match. Its body work remains w_i>0. Let Γ=Σg_i, G=#guarded completions, and **P_g=L+Σguarded i g_i**. W still denotes body work unless explicitly written W_g=W+Σguarded i g_i. P_g is not claimed to be a subset of body-only W. These primitives fit the lockless-validation/guarded-completion distinction but do not assert that Java replace is lockless or that all native costs have this law.

## Proposed universal optimum of charged protection

For all DAGs and B,r≥0, propose

    inf over universally Q-admissible B-unaware P of sup_E_B P_g(P,E)
       = Γ * 1[B≥r] + Top_(B-r)+(w).

One policy attains the curve at every B: JIT cheap attempts until r failures, then JIT cached completions for every unfinished job. If B<r there is no guard. Otherwise guard charges are at most Γ, and at most B-r distinct cached mismatches add at most Top_(B-r)+. No extra cost observation is given to the selector.

Lower bound when B≥r: fix k=min(B-r,n) heaviest jobs. Use an adversary that rejects every cheap comparison (fresh identity) while the global cheap-failure count f<r, and additionally writes at every matching cached comparison on a target not already completed, until all k targets finish. A stale cheap failure increments f without needing a write. Once f=r, another cheap comparison on any reachable prefix cannot be selected by a universally Q-admissible program: its failure in an extended finite-write environment would give more than r noncompletions. Every job therefore completes by a fresh/cached operation, so total guard charge is Γ. Each target either completes fresh, stale cached, or a freshly invalidated cached comparison, and pays its w_i under protection. At most r useful cheap writes and at most k target cached writes occur, so the adversary is unconditionally bounded by r+k≤B on all admissible histories. To make the environment unconditionally bounded even against an inadmissible policy, disable cheap writes at f=r and target writes after the k selected targets complete, maintain one write per target cached completion, and terminate all writes after r+k publications. This preserves its behavior against every admitted program. Completion follows from universal finite-write admissibility. This yields Γ+Top_k. For B<r, nonnegativity matches the zero upper bound.

Need careful audit of the universal Q argument when some cheap successes could occur: before f=r the adversary rejects all cheap calls; after f=r another failing call would make Q exceed n+r because n permanent completions remain mandatory across the whole execution. Therefore there are no cheap successes on the lower-bound play. Arbitrary old records, free inspections and readiness do not prevent the fresh own-gate continuation. Fresh target completion consumes no adversarial write but still contributes its body cost.

## Immediate information gap at the boundary

For a supplied B=r, an informed policy can keep trying cheaply: there can be at most r failures, then one further successful comparison per pending job. Thus informed optimum P_g=0. The universal value at B=r is Γ. For every Γ>0, the equality of informed and unaware optimum body protection in the original three-mode theorem is lost as soon as guard entry receives a positive charge. This holds already for n=1, and also at r=B=0. It is a resource-scope boundary, not a failure of the original body-work theorem.

## Proposed exact informed r=0, B=1 reduction

Let π be a topological order and C_i^g(π) the sum of g_j through i in that order. Propose

    min_P sup_E_1 P_g(P,E)
      = min_π max{ Γ, max_i [C_i^g(π)+w_i] }.

For the upper bound, cached-complete in order until the first mismatch, then cheaply complete the remaining jobs. With no detected mismatch, total charge is Γ. A mismatch at i spends the only write, and accumulated charged protection is C_i^g+w_i; the remaining jobs can safely complete cheaply. Writes absorbed before preparation or otherwise undetected cost no larger charged protection.

For the lower bound, take any Q≤n program's no-write execution. No cheap comparison can appear: a fresh own-gate write could fail it and force at least n+1 calls. Every no-write completion is guarded, inducing a topological order. Its fresh-job set F gives no-write cost Γ+Σ_F w_i. For every cached job i, the history up to that gate has a one-write continuation with prefix charge C_i^g+Σ_(fresh before i)w_j+w_i. These are distinct witnesses, not simultaneous outcomes. Replace a fresh job j by cached in this lower-bound expression: no-write cost and all later fresh prefixes decrease by w_j; its newly introduced cached witness equals the old cost through its fresh completion and is at most the old no-write total. Repeating yields F empty without increasing the expression. This lower-bounds every original program by the all-cached expression in its no-write order. Charge all relevant guarded operations and preserve old-record/inspection arguments as in the paper.

The scheduling objective is inherited Lawler maximum completion-plus-tail, with processing times p_i=g_i and tails q_i=w_i; max with Γ is an extra common floor. For independent jobs a nonincreasing w order is optimal, independently of g_i (an adjacent exchange puts the larger tail first). If g_i=0, the value reduces to w_max, as in the original body objective. Example w=(1,10), g=(1,1): light-first gives12, heavy-first11. Original body-only optimal-L/least-W corner instead uses light-first with worst W12 versus heavy-first21. The objectives differ; this is not an inconsistency.

Full joint W/P_g frontiers and least unknown-budget W curves are not yet derived. Adding a positive cost to cached matches can change which matching continuation is dominated; do not reuse a proof that relied on a free matching cached operation. Existing full-program extraction appears to preserve guard counts if its known-zero-budget suffix uses prepare/cheap rather than prepare/cached, but this needs explicit checking. No finite result or novelty judgment has been supplied yet.

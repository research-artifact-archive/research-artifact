# Fixed finite check of a general safe-fresh suffix transformation

This is a new author theorem/algorithm candidate following ordinary-model Cost18, which suggested a two-inequality fresh rule on the already observed six-job root. The general invariant and worst-work domination are new proof obligations, not conclusions drawn from that model's reported private computation.

Fix all forward-edge DAGs on n1..3, every weight vector in{1,2,4}^n, and r0,1,2 (711 roots, overlapping earlier studies). Add the existing six-job distinct-order root, the existing four-job observation root (A5->U1->V1 and independent Z2,r1), and the deliberately constructed three-job chain(1,1,10),r0. Total714 roots; no independent empirical population claim.

For each root, generate and interpret every branch of two deterministic policies: cheap minimum-ready until r failures then all-cached minimum-ready; and the same cheap phase followed by the safe rule. At k=0 cached mismatches after switching, choose maximum-ready cached. At k>0 choose maximum-ready fresh only if both ell+w_i<=globalTop_k and ell+remainingWork<=globalTop_(k+1); otherwise choose minimum-ready cached. d/k count observed bad comparison results, not actual hidden writes. The rule receives no B, and every comparison has immediate paid preparation.

Check every prefix for the protected cap, every completion/readiness/call count, exact all-budget L and W<=the paired all-cached baseline at B0..n+r. Independently compare the candidate and baseline trees with the unchanged unknown02 operation interpreter. Save all cases, all branch traces and trees. Preserve any mismatch/invalid/timeout and do not retry.

One predetermined control uses the same policy on chain(1,1,10),r0 but removes the second fresh inequality. Prediction: cached first-small mismatch, fresh second-small, cached large mismatch gives L=12 at d=2, exceeding Top2=11. Save the full violating prefix and complete branches even if the prediction fails. This is a deliberate invalid policy, not an upstream defect.

One execution with60s total cap; report remaining roots NOT_EXECUTED on timeout. The generic domination theorem still requires a direct proof for arbitrary finite writer strategies, including harmless writes in the common cheap prefix. No native runs, timing performance claims, independent proof certification, general DAG optimal-W theorem or adoption into the manuscript is implied.

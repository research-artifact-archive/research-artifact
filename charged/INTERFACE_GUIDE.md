# Operation and information contracts

This guide accompanies the current paper's Sections2–5. The full central proofs are in the PDF. It adds no experimental observation or mechanically checked theorem.

| Feature | Whole-kernel operations | Component repair |
|---|---|---|
| Preparation | Full pure kernel, including from an older captured snapshot; arbitrary finite records may be retained | One complete fresh preparation before each counted call; no other preparation retained |
| Observation | Honest unprotected entry inspection and operation returns | Dirty union inside the counted call; repeated footprint writes and their count are hidden |
| Decision timing | Job and operation mode chosen before the environment's comparison gate; record selection uses the preceding store | Job chosen before footprints, then accept/reject after the dirty union is observed within the same call |
| Objective | Protected kernel work L; total kernel work W and API calls Q are separate | Protected repair work, with per-call kappa and per-completion mu only where specified |
| Cap | At most n+r counted calls; local and shared variants are explicit | At most q calls for one job, n+r for a workflow; exactly one outside preparation per call |

Completion stores an exact immutable milestone and remains permanent despite later writes. No direct guard acquisition/release, guard surviving return, cross-job completion or outside publication is admitted by the whole-kernel entrypoint contract. Theorems are relative to these operations, not a completeness claim for arbitrary Java or lock APIs.

## Quantifiers and inspection

For each b, E_b consists of gate strategies with at most b writes along every play. An informed P(B,h) is admissible at B if it completes within the cap against every E in E_B. One unaware P(h) must satisfy its cap for every finite b and every E in E_b. Any fixed finite-write play can be reproduced by an environment capped at that play's write count. A budget-invariant policy needs no estimate of B to attain its entire protection curve. Promising a particular fixed protection ceiling still requires a valid bound on the writes for which that ceiling is asserted.

The retained store and selected handle are separate: a failed cheap call clears selection without erasing copies. Copying cannot retag a result or fabricate kernel work. A legal fresh own-key identity is available after every finite history and invalidates all prepared records for that job, even if record selection occurs within the already-chosen operation. Two environments can share the same concrete prefix and differ at the next gate, subject to their remaining write allowance. The lower-bound adversaries have unconditional finite write bounds. Avoiding completion against one of those adversaries already violates admissibility on that same play; a generic claim about truncating arbitrary infinite environments is unnecessary.

The informed three-mode proof accounts for the write causing a possible (r+1)st failure within r+k<=B. The unaware two-mode proof evaluates an execution with only r failures, then uses a different finite extension to show that another cheap call is inadmissible. The extra write is absent from the evaluated execution. The one-job charged proof separately counts noncompleting calls and actual writes, allowing fewer writes than failures when a stale record is reused.

## Operational interpretation and evidence

Java API calls, monitor acquisitions and protected kernel operations are different counters. Internal map reorganization preserves value references and is not an application invalidation. The fixed-source argument abstracts internal processing around the protected comparison/publication while preserving returned records and completion milestones. Pure, stable, normally terminating key methods and callback restrictions are explicit in the paper. This is not a verified running-JDK binary. Roslyn's stronger rebase operations retain merge costs and have no established exact reduction to either game.

The existing direct games enumerate serial fresh-preparation policies. Their agreement corroborates the equations on their fixed finite inputs; the paper's operation-level proofs cover the broader retained-record/inspection class. Exact-D component games and exported-table checkers use the separate repair history. No old control, timeout, invalid, counterexample or native observation changes with this guide.

## Research lineage

The one-job additive-loss calculation is a capped rent-or-buy specialization, with the cap also changing the informed comparator beyond the allowed retries. See Lotker, Patt-Shamir and Rawitz, *Rent, Lease, or Buy*, SIAM J. Discrete Math.26(2),2012, https://doi.org/10.1137/100794018 .

Algorithms with predictions already compare advice-informed behavior with robust guarantees when error is unknown. The manuscript's narrower question asks for one deterministic no-advice policy equal to a budget-informed minimax curve at every budget, under a universal call cap. It compares this with Purohit, Svitkina and Kumar, *Improving Online Algorithms via ML Predictions*, NeurIPS2018, https://proceedings.neurips.cc/paper/2018/hash/73a427badebe0e32caa2e1fc7530b7f3-Abstract.html ; and Lykouris and Vassilvitskii, *Competitive Caching with Machine Learned Advice*, ICML2018, https://proceedings.mlr.press/v80/lykouris18a.html . This comparison does not establish novelty against all literature.

## Explicit lower-bound accounting in the current paper

Lemma1 uses fresh identities for the chosen job, which invalidate every retained preparation of that job. In Theorem1, f counts noncompleting target comparisons, p counts completed targets, and v counts actual writes. The adversary stops permanently at f=r+1 or p=k. At program nodes after a completed operation, v<=f+p; immediately before another write, v+1<=f+p+1<=r+k<=B. Intermediate gate states need not satisfy the program-node invariant. After permanent stopping, a cheap call can match; admissibility rules out reaching r+1 failures before completing all jobs. For clipped repair histories, min(min(e,E)+c(D),E)=min(e+c(D),E), while accrued cost remains unclipped. These are paper proofs, not additional mechanically checked executions.

## Minimum uniform additive loss for workflow repair

Section4.3 now minimizes the worst additive excess over every budget-specific informed optimum, within the repair interface. For a fixed policy, each reachable terminal history is realizable at its least consistent write count; monotonicity of the informed curve makes that count a worst-regret witness. Shifting every terminal target by delta shifts every threshold by delta, so the optimum is the negative root threshold. Shifted inequalities extract an attaining policy without actual B input. Finite observation alphabets and at most n+r rounds make the minimum attained, before count clipping. Accumulated cost remains unclipped, including histories whose least footprint count exceeds the saturation budget. Common completion charges cancel. This exact workflow-repair result does not solve the distinct retained-record whole-kernel workflow loss problem or calibrate native rebase/merge costs. See WORKFLOW_REGRET.md for the full separate vector comparison and preserved preparation incident.

## Completed-operation Java source refinement

Paper163 Sections2 and5 expand the pinned-source argument. A monotonically extended injective identity map includes live values, pending committed writes, saved results and available handles. The decoded current Java map equals the abstract map after the pending write suffix. Complete operation groups carry exact kernel/call charges; unfinished prefixes are not silently charged as completed kernels. Conditional replace returns a flag while job output remains the prepared value; fresh compute saves its returned value. Stable key hash/equality/comparison, deeply immutable fresh values, fixed writer/kernel tags and normal API progress are explicit conditions. Small fixtures do not cover resizing, tree-bin execution or the validation-only mismatch branch. See [source/cost boundaries](SOURCE_COST_BOUNDARIES.md) for the full derivation. This conditional source proof does not establish native elapsed time, prevalence, mechanical refinement or independent certification.

## Paper172 section map and observation scope

The current whole-kernel model and charging are in Section2; universal protected-work results in Section3; joint-work polynomial cases in Sections4--5; finite-program domination and the output-only boundary in Section6; completed-operation Java refinement in Section7. Historical repair-interface Section4.3 locators above refer to paper163 and its predecessors. Those separate results remain in their supplements. Section8 reports both original2,076 zero-retry native paths and12,224 one-retry paths, including both wrappers and verified TreeBins. Thus the earlier small-fixture tree/validation exclusion above describes that earlier study, not the new native matrix. Resizing and full JMM verification remain outside the native evidence.

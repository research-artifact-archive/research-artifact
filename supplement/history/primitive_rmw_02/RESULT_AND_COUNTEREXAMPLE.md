# Speculative acquisition refutes H-RMW

Exploration02 completed all384 inputs with2,688 root comparisons. There were5 inputs with primitive/H17 value discrepancies, no FAILURE/TIMEOUT/INVALID. The explicit solver's606,200 states and4,514,300 actions passed complete Bellman and selected-policy termination checks. RAW.jsonl SHA-256 is3be77cfbcd3a49fba32dc4dd4a68a729c78f19ca63013453210eed2e444d5040. This is a changed parameter region after exploration01's agreement, not a replacement of that result.

## First recorded counterexample

Input fractional-0040 has jobs(w,alpha)=(12,1),(3,8), with operation cost scale10 and B=2. All-U baseline is170. The corresponding H17 inputs are (p,c,h)=(23,130,10),(42,40,10). Primitive value is242, unrestricted H17 is243. This input is the first mismatch in the predefined sequence; it has not been minimized or selected as a representative population case.

The saved primitive controller initially acquires job0's lock. If that fails, cost10 plus the budget1 all-U continuation210 gives220. If it succeeds, it attempts to acquire job1 while retaining lock0:

- If job1 acquisition succeeds, its cost is11. Prepare job1 for57 and commit for19 while both locks are held; prepare job0 for132 and commit for11. Including the initial acquisition10, the complete all-success branch costs240.
- If job1 acquisition fails, its cost is11 and the budget drops to1. Release lock0 for11 and use the all-U budget1 continuation210. Including the first acquisition10, this branch costs242.

The root worst cost is therefore242. The budget1 continuation210 and all later ordinary actions are in the saved state/action graph. This policy uses successful early acquisition without committing to complete that job before attempting another. If the second acquisition fails, it can abandon the successful protection. Neither H17 original action offers this continuation, since successful protection completes the selected job.

Other discrepant inputs are fractional-0272 (budget2..4), fractional-0289 (4..6), fractional-0304 (3..6), and fractional-0336 (4..6). Their exact inputs and all values remain in RAW.jsonl; all five gaps favor the primitive model. The discrepancy is not a refutation of the abstract H17 theorem and not a measured result for a native implementation.

## Consequence for the research choice

H17 cannot currently be generalized to the complete proposed primitive catalog by the hoped-for normal form. A native application would need to justify why speculative cross-job acquisition is absent, dominated under its actual costs, or explicitly outside its program contract; it cannot be excluded merely to retain the theorem. This adds a concrete operation-level obstacle to the Azure/Hazelcast source gaps. Stop extending the agreement corpus for H-RMW: the hypothesis is refuted.

This counterexample could motivate a new synthesis problem, but no compact algorithm, source-backed native realization or novelty claim for that problem has been established. The next parent focus shifts to a precise mixed-state administrative reduction for FG-DUCS, based on the separate closest-work comparison. H17 remains a valid specialized result, not an automatically chosen main paper.

# Exact competitive policies for the partial-repair interface

A compact compiler now replaces the full expenditure-state Bellman table in the separate partial-repair model. It returns an exact optimal deterministic competitive ratio, a threshold policy that never receives the write budget, and matching upper/adversarial certificates. For general footprints this result is conditional on a correct minimum-cover/maximum-weight profile. For singleton footprints the complete compiler constructs that profile by sorting the weights. The common publication cost is declared, not calibrated from Roslyn.

The mathematical step is monotone threshold feasibility: at any expenditure, choose the smallest-cost dirty observation whose ratio exceeds the target. This path has the least expenditure of every still-unacceptable history. Hence a single path decides feasibility; exact integer-scaled ratio isolation supplies the optimum. For monotone H=G, denominator buckets replace the linear search and give the bound in MONOTONE_PROOF.md. Generic minimax dynamic programming and information-state reduction are inherited techniques; this study does not establish literature-wide novelty.

## Correctness evidence

Version1 matches all20,920 previously observed DP rows over1,957 geometry/unit-scale variants, checks every returned certificate, and matches600 complete small observation trees. Seven changed certificate/profile controls are rejected. An additional108 fixed rational/long-horizon rows agree with a separate dirty-set Bellman implementation, including36 nonmonotone-H rows and72 rows with missing costs. Version2 produces identical certificates on all21,028 rows (316 monotone-accelerated and20,712 fallback), matches1,600 separately fixed threshold decisions, and rejects all10 controls with both checker versions. Known earlier inputs are regression cases, not held-out inputs.

## Complete construction outcomes

| Version and grid | Units | Success | Timeout | Failure/invalid/unstarted |
|---|---:|---:|---:|---:|
| Original compact, large |120|118|2|0|
| Original compact, paired |48|48|0|0|
| Profiled DP, paired |48|44|4|0|
| Monotone compact, large |120|120|0|0|
| Monotone compact, paired |48|48|0|0|

The version1 denominator is216, with210 success and6 timeout. The explicitly post-observation version2 denominator is168, all successful. Version2 changes the algorithm; it is not a rerun of unchanged timed-out code. The original DP was already strengthened to use the H profile, but returns only the root ratio. Compact returns a profile/order, policy ratio and two checked certificates. The48 old DP outcomes were not re-executed.

Large inputs include m=16,256,4096,65536, two weight patterns, q=1,2,3,8,64 and mu=0,2,W. Each has an8second complete-process limit; paired grids use a3second limit. Version2 large process times range0.0345--1.0010seconds; paired times0.0361--0.0405seconds. Maximum observed large RSS is32,980,992bytes, with904,554bytes maximum returned artifact. These are one-process-per-cell local descriptive observations, including startup/generation/sorting/compilation/checking/output in process wall time. RSS is observed, not enforced.

The two formerly timed-out compact inputs, m=65536,q=64,mu=W, finish at0.6119seconds (uniform) and0.5651seconds (mixed). All168 success artifacts are rechecked outside timing with both the unchanged linear checker and bucket checker;166 earlier compact ratios and44 available profiled-DP ratios agree exactly. The other old four timeouts occur at m=512,q=8 in profiled DP. All raw records, source hashes, status partitions and caps remain available in scale01/,scale02/,scale_analysis01/,scale_analysis02/.

## Scope

This is an authored model/algorithm construction study. It proves no prevalence, application response-time guarantee, native additive repair-cost model, human benefit or FSE acceptance. The partial-repair counterexample remains valid: exact simultaneous known-budget optimality need not exist. A competitive ratio solves a different objective and must not be described as restoring that simultaneous optimum.

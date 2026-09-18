# Quick-start reproduction report

Result: **PASS**. Elapsed: **22.978 seconds**. Started (UTC): 2026-09-18T23:16:20.412026+00:00.

These are saved-evidence checks and independent finite-model derivations. No JVM synthesis, network request, or benchmark timing rerun was performed. SKIP establishes no claim; restore the archived assets and/or install Matplotlib to enable the listed optional checks. A source-built JAR is intentionally outside this no-Java check.

| Claim | Expected | Observed | Status | Seconds |
|---|---|---|---|---:|
| Saved RQ1/RQ2 evidence | 92 + 14 jobs; all saved decisions/checks agree | 92 RQ1 + 14 RQ2 jobs; saved decisions, certificates and raw metadata agree | PASS | 0.248 |
| RQ1 independent derivation | 46 models; 18 WIN / 24 LOSS / 4 INVALID | 46 models: 18 WIN / 24 LOSS / 4 INVALID; all derived fields match | PASS | 0.111 |
| RQ2 independent derivation | 14 jobs; 10 WIN / 4 LOSS | 14 jobs: 10 WIN / 4 LOSS; all derived fields match | PASS | 0.032 |
| Paper finite witnesses | fine/bulk separation, branch and boundary witnesses, policy 13/11 | Cell 56/392 vs bulk 10/60; policy 13 states/11 edges; branching and boundary restrictions checked | PASS | 0.041 |
| Figures 1 and 2 | all declared edges/transfers and scoped fixture correspondences | Figure edges, five transfer pairs, mapRelation selections and 13/11 policy match (scoped projections) | PASS | 0.034 |
| Residual-soundness coverage | H 0/273; A 138/138; entry-scoped exact 89/135 | H 0/273; A inclusion 138/138 (equality conditional); entry-scoped exact 89/135; 46 unverified | PASS | 1.306 |
| Monolithic static cross-check | two meta products and uncontrollable spoiling loop | Meta products 33093/257314 and 14763/99676; safety pruning and UC spoiling loop checked | PASS | 0.682 |
| Separate Industry contract variant | 131/131 WIN; original 42 losing entries preserved | 131/131 variant roots WIN; original 42 losing roots retained; all UC responses/ranks checked | PASS | 2.934 |
| Table 3 / Figure 3 and comparisons | 135 cells; FG 25/1/1, DF 14/13, Legacy 9/13/5; saved ratio ranges | 135 cells; FG 25 WIN/1 LOSS/1 TO; DF 14 WIN/13 TO; Legacy 9 WIN/13 OOM/5 N/M; DF/FG completed-pair solver ratio 1.5765–2123.8; full saved summaries match | PASS | 16.845 |
| Preserved inputs | all inspected/copied evidence unchanged | 16000 checked source/evidence files unchanged (SHA-256) | PASS | 0.735 |

Recorded logs: `restored-logs/`. Re-run quickstart for generated evidence. Existing package outputs were not used as write destinations.

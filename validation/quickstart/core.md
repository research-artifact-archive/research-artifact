# Quick-start reproduction report

Result: **PASS with unavailable checks skipped**. Elapsed: **2.711 seconds**. Started (UTC): 2026-09-18T23:13:53.280377+00:00.

These are saved-evidence checks and independent finite-model derivations. No JVM synthesis, network request, or benchmark timing rerun was performed. SKIP establishes no claim; restore the archived assets and/or install Matplotlib to enable the listed optional checks. A source-built JAR is intentionally outside this no-Java check.

| Claim | Expected | Observed | Status | Seconds |
|---|---|---|---|---:|
| Saved RQ1/RQ2 evidence | 92 + 14 jobs; all saved decisions/checks agree | 92 RQ1 + 14 RQ2 jobs; saved decisions, certificates and raw metadata agree | PASS | 0.33 |
| RQ1 independent derivation | 46 models; 18 WIN / 24 LOSS / 4 INVALID | 46 models: 18 WIN / 24 LOSS / 4 INVALID; all derived fields match | PASS | 0.125 |
| RQ2 independent derivation | 14 jobs; 10 WIN / 4 LOSS | 14 jobs: 10 WIN / 4 LOSS; all derived fields match | PASS | 0.034 |
| Paper finite witnesses | fine/bulk separation, branch and boundary witnesses, policy 13/11 | Cell 56/392 vs bulk 10/60; policy 13 states/11 edges; branching and boundary restrictions checked | PASS | 0.044 |
| Figures 1 and 2 | all declared edges/transfers and scoped fixture correspondences | Figure edges, five transfer pairs, mapRelation selections and 13/11 policy match (scoped projections) | PASS | 0.036 |
| Residual-soundness coverage | H 0/273; A 138/138; entry-scoped exact 89/135 | H 0/273; A inclusion 138/138 (equality conditional); entry-scoped exact 89/135; 46 unverified | PASS | 1.222 |
| Monolithic static cross-check | two meta products and uncontrollable spoiling loop | Meta products 33093/257314 and 14763/99676; safety pruning and UC spoiling loop checked | PASS | 0.703 |
| Separate Industry contract variant | 131/131 WIN; original 42 losing entries preserved | 34/34 archived files absent; restore every result asset first | SKIP | 0.012 |
| Table 3 / Figure 3 and comparisons | 135 cells; FG 25/1/1, DF 14/13, Legacy 9/13/5; saved ratio ranges | 15325/15325 archived files absent; restore every result asset first | SKIP | 0.158 |
| Preserved inputs | all inspected/copied evidence unchanged | 620 checked source/evidence files unchanged (SHA-256) | PASS | 0.034 |

Recorded logs: `core-logs/`. Re-run quickstart for generated evidence. Existing package outputs were not used as write destinations.

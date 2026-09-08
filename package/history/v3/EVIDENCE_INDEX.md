# Claim/evidence index

| Paper result | Included source/data | Portable entry point |
|---|---|---|
| Primitive/DAG Bellman correspondence | `src/final_evaluation_dag_01`, `data/semantic` | `reproduce.py semantic` |
| All-budget compiler and checkers | `src/dependency_hybrid_01`, `src/dependency_curves_01`, `src/dependency_hybrid_check_02` | core semantic |
| Final native correspondence and fixed-order comparators | `src/final_evaluation_dag_native_01`, `data/native` | core native |
| Restricted B1 hardness | `src/dag_hardness_01`, `data/extended/dag_hardness_01` | extended hardness |
| Selected four-job/two-failure gap | `data/extended/adaptivity_family_operational_01` | extended family; proof in paper |
| Specified B1 methods | `src/b1_constraint_comparator_01`, corresponding extended data | extended b1; CP optional |
| Specified B2 methods | `src/b2_contingent_comparator_01`, corresponding extended data | extended b2; CP optional |
| Full B1/B2 benchmark records | corresponding `benchmark01`, plus B1 `screened01` | extended bench1/bench2; saved-policy scans |
| Concave point-value oracle | `src/budget_oracle_01`, corresponding extended data | oracle oracle / controls |
| Six-value versus all-budget comparison | `data/extended/budget_oracle_01/benchmark01` | oracle bench; 77 saved certificates, all 96 statuses |
| Price-independent segment bound | `paper/main.tex`, `data/extended/budget_oracle_01/SEGMENT_FPT_PROOF.md` | mathematical proof; no machine certification |
| General recurrence/reflection/scheduling inheritance | `paper/main.tex`, included attribution notes and source receipts | primary citations; article PDFs excluded |

The paper uses the conservative bound proved in `SEGMENT_FPT_PROOF.md`. A later
`ENVELOPE_BOUND_ADDENDUM.md` is an author proof draft and is not an additional
empirical result or a new bound adopted by build36.

Older scale and order searches, the 12,288 adaptivity-search units, independent
PRISM/AND-OR/bounds comparisons, and early positive-cost acquisition
counterexamples are outside this package's executable scope. Their original
inputs, denominators, adverse outcomes, and reports remain in the research
workspace. The paper distinguishes them from the fixed final sample.

Mathematical correctness and accurate scholarly attribution are not established
by finite checks alone. Author-side inspections are not independent blind
certification. Author/rights/AI final attestation and external release remain
separate from local reproduction.

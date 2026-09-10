# Cached observation and unknown budgets on a DAG

Current manuscript216 Section5.2 Proposition8 contains the (5,1,1,2), r=1 result and its compact proof. The complete sufficient-family proof and every fixed outcome remain linked below. This manuscript follows the already published and publicly replayed53-stage evidence commit; it adds no measurements.

The least unknown-budget total-work curve for independent jobs has a policy that ignores cached comparison results. This supplement shows that precedence can change this fact even when the same optimal protected-work curve and call cap are required.

For A→U→V and independent Z, with works (5,1,1,2), r=1 and Q<=5, the exact least whole curves at B=0,...,4 are

| Observation contract | W(0) | W(1) | W(2) | W(3) | W(B>=4) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cached comparison visible | 9 | 14 | 19 | 20 | 20 |
| Entire cached transition strictly erased | 9 | 14 | 19 | 20 | 21 |

One policy under each contract attains its entire curve. Both have the optimal protected curve (0,0,5,7,8,9), constant9 after B=5. Erasure requires every kernel execution to return the same immutable per-job object and permits no surviving compared input, Boolean or comparison-dependent retained state; inspections and old snapshots are still allowed. Hiding the returned flag alone is insufficient.

The [complete proof](evidence/RESUMED_20260910_1617/universal_observation_dag_01/PROOF02.md) covers the sufficient integer family (M,1,1,2), M>=3, r>=1, r(M-2)>=3. It gives both policies, unconditional finite adversaries, forward coupling through arbitrary early preparations/record stores, and distinct computation charges. The [original candidate](evidence/RESUMED_20260910_1617/universal_observation_dag_01/DRAFT01.md) is retained. This is an author mathematical proof; the [general visible-program proof](FULL_PROGRAM_PROOF.md) is not used to assert completeness of erased-policy enumeration.

The [fixed protocol](evidence/RESUMED_20260910_1617/universal_observation_dag_01/PROTOCOL01.md) and [complete result](evidence/RESUMED_20260910_1617/universal_observation_dag_01/SUMMARY01.json) retain28 roots:21 satisfy the sufficient family condition and seven lie outside it. All9,373 interpreted paths are saved. Both deliberate faulty policies are detected: dropping the condition that Z completed cheaply violates protection, while preparing V before its exceptional fresh completion violates the work bound. The erased oracle checks only its declared canonical class; it does not prove the all-program lower bound. Inputs overlap prior visible studies; no independent population or native latency result is claimed.

Replay this stage from the release root:

```sh
python3 -B charged/reproduce.py universal-observation-dag --out work/observation-check --timeout 300
```

The output directory must be new. The stage reruns the fixed checker with the same visible oracle, verifies every stable scientific output byte for byte, and excludes only wall-clock fields from metadata equality. All53 standard stages can be run with `all` in place of the stage name. Previous scientific payload and unfavorable results remain unchanged.

The stored PDF is now manuscript216 and includes this result. Publication and replay do not establish submission readiness.

The [expanded proof](evidence/RESUMED_20260910_1617/universal_observation_dag_01/PROOF03.md) makes the existing publication overwrite x[i]=z_i explicit and gives a concrete trace showing why a post-completion inequality against the old capture does not reconstruct the comparison flag. PROOF02 and all earlier inputs/results remain unchanged.

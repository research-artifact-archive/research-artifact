# Unit guard charges and precedence

The [complete proof](evidence/RESUMED_20260910_1617/guard_dag_unit_01/PROOF02.md) adds a boundary to the same supplied-B=1, Q<=n completion interface. Manuscript197 integrates the representation and this boundary in Section7, with Theorem12 stating the unit-guard result. All preceding scientific payloads and prior manuscript versions remain preserved in their immutable commits.

With free comparisons and zero entry costs, any DAG admits an O(n³) complete body-resource frontier by the inherited Lawler reduction. Charging each guarded entry one unit in BOTH total and protected resources makes joint-cap decision strongly NP-complete even on an endpoint-incidence DAG of height two, with at most two predecessors per job and body works in {1,n+1}. Yet every DAG with a common guard price has at most n²+1 frontier points. Thus the difficulty can be finding a small frontier, rather than its output length. Independent jobs with common entry prices retain the preceding greedy algorithm.

The incidence and prefix construction is inherited from Garey–Johnson1976 Theorem2; the [attribution record](evidence/RESUMED_20260910_1617/guard_dag_unit_01/PRIMARY_ATTRIBUTION01.md) states what was actually verified. The completion-specific proof connects separate worst-case caps to every legal program, through the existing [complete one-write representation](evidence/RESUMED_20260910_1617/charged_comparison_01/FULLY_CHARGED_PROOF05.md). It does not claim new general scheduling hardness. A fixed protected fee on every counted call shifts both resources by the sum of those fees, because every admitted execution has exactly n completing calls. These prices are mathematical contract parameters, not calibrated native times.

## Fixed checks and full outcomes

Stage52, `unit-guard-dag`, replays the fixed check02. All3,208 graph/k cases on3–5 vertices are retained.1,809 have too few edges and map to a declared fixed negative target. The1,399 nontrivial reductions have728 yes and671 no sources; all agree with the unrestricted DAG/mode DP. All8,190 constructive paths satisfy Q=n and respect both caps. For each constructive policy, the separate coordinatewise maxima over its paths attain the two caps; one path need not attain both. The separately implemented recurrence with unit fees on every call translates all1,399 complete frontiers correctly.

A further675 common-guard DAG cases agree with46,998 enumerated order/mask policies, the first-coordinate candidate set and the n²+1 bound. Heterogeneous all-call fees also translate every frontier correctly. Three deliberate alterations are detected: removing precedence, omitting no-write protected load and omitting cheap-suffix fees. Full rows, controls, state counts and timings are in [run02](evidence/RESUMED_20260910_1617/guard_dag_unit_01/run02). The66.616-second original run is a checker runtime, not an application speedup.

The sealed v1 checker was not executed. [Protocol02](evidence/RESUMED_20260910_1617/guard_dag_unit_01/PROTOCOL02.md) and its [preflight correction](evidence/RESUMED_20260910_1617/guard_dag_unit_01/PREFLIGHT02.md) preserve the deadline/accounting correction before any source/cap observation. No failed scientific run is overwritten. The finite checks and author/AI proof criticism do not certify asymptotic proofs, independent reproduction, novelty or acceptance.

## Reproduction

From the repository root with Python3.10+ on a POSIX system and assertions enabled:

```sh
python3 -B tools/verify_release.py
python3 -B charged/reproduce.py unit-guard-dag --out work/unit-guard-dag --timeout 300
python3 -B charged/reproduce.py all --out work/all52 --timeout 300
```

Choose new output directories. The new stage runs the unchanged frozen checker and compares all stable scientific output bytes and result fields. It retains the checker’s900-second internal safety cap; the driver’s per-stage cap is300 seconds unless supplied otherwise. The original research deadline is not imposed on later reproductions. These are author fixed-evidence replays and make no new native timing measurements.

# Resource safety without future job data

For the explicit current-preparation residual game, one policy must keep protected work below the all-cached top-budget curve for every future write allowance. The exact body-work viable region is `ell <= Top_k(completed)`. Every ready cached action is safe from this region; fresh job i is safe exactly when `ell+w_i <= Top_k(completed+i)`. The filter needs no future weights or DAG edges. Its two heaps support a constant-time query and logarithmic completion update.

Read the [complete body proof](evidence/RESUMED_20260911_1123/residual_safety_01/PROOF02.md) and [charged proof](evidence/RESUMED_20260911_1123/charged_residual_01/PROOF03.md). The charged benchmark is the all-cached curve, not a claimed charged optimum. A common mismatch fee cancels; the wider condition `max h_i <= min q_i` preserves an exact completed-state filter. Without this condition, the same full q vector, DAG and visible prefix can require opposite fresh permissions due to the future fee split. This does not forbid a conservative safe filter or prove that every instance outside that condition loses locality.

## Fixed evidence and scope

| Check | Preserved evidence |
|---|---|
| Body residual game |493 roots,158,463 states,303,534 action checks; no discrepancy. The original range includes surplus credit. A labeled reanalysis separates95,514 states/149,472 action checks within `k<=|D|`, including936 strict fresh permissions, from62,949 surplus states and2,598 surplus strict permissions. These states need not all be reachable from a safe initial policy.|
| Two-heap implementation |8,355 valid initial states,58,485 queries,166,372 actions,48,000 stream steps;0 discrepancies. All789 invalid initial states,9,083 rejected fresh requests and14 invalid-argument controls are retained.|
| Whole work curves |16,267 fixed roots and1,565,245 interpreted paths. The new and earlier safe filters have identical worst-W curves in all16,267 roots. More permitted choices therefore do not establish a new performance improvement.|
| Common-fee game |16,263 common-fee roots plus three fixed examples.379,647 physical-credit common-fee states agree with the completed top-k value. Original unrestricted-fee and surplus-credit counterexamples remain.|
| Whole-curve obstruction search |The11 diagnostics and4,457 fixed roots retain1,035,304 paths. A local residual pair has crossing least work curves, but the three forced/unforced initial curves coincide. No general positive-retry DAG least-curve theorem follows.|

The first body population uses all forward DAGs and weights `{1,3,7}` for n<=3, and four declared n=4 vectors. The whole-curve and common-fee populations use all forward DAGs up to n=4 and all corresponding weight vectors. They overlap earlier authored synthetic studies. Counts are not independent software workloads, proofs, native speedups, or evidence of acceptance.

The [whole-curve archive](evidence/RESUMED_20260911_1123/whole_curve_obstruction_01.tar.gz) contains every fixed input, code, protocol, selected policy, outcome, failure record and author report from that investigation. Its [member manifest](evidence/RESUMED_20260911_1123/whole_curve_obstruction_01.members.json) records exact source/public bytes and any author-path projection. Large JSON streams elsewhere use gzip with decoded hashes in the provenance manifest.

## Replay

```sh
python3 -B charged/reproduce.py residual-safety --out work/residual56 --timeout 300
```

The driver reads the fixed scientific code and previous interpreters, creates a new tree and requires stable results to match. Timings and compression headers are not compared as scientific outcomes. It runs no native timing campaign and creates no new independent sample. All55 previous stages remain available; public manuscript216 is unchanged by this supplement-only batch. The new manuscript will cite a verified public evidence commit after its own build and review preparation.

The mechanisms of optimistic fallback/reuse, budgeted top sums and permissive safety control are inherited. The claims concern the stated completion interface. Full-cost correspondence, actual-client demand and native application benefits require separate evidence; the earlier Linux/Roslyn/Valkey adverse results remain in force.

# Mid-body/END updates with tight imported caps: exploratory result

All216 native cells succeeded (37.24s build/run), and all216 traces passed the separate author checker. Five corrupted traces were rejected. The executed schedules contain153 actual cycles and223 inconsistent bodies. All callbacks nevertheless returned normally: **zero native aborted prefixes occurred**. ExpandAll bypasses the leaf-null consistency check while expandingDepthRemaining>0. Mid-body mutation was exercised, but the typed-abort branch remains unobserved in this packet.

The pre-outcome lambda3/cross_stage/curve_fast_tie prediction was realized exactly: K fails once and V fails three times over two split cycles, so FK+FV=4=2q. The six full callbacks charge K4,K4,V104,V104,V104,V104: weighted selected cost=charged cap=424, equal to the imported all-budget model value. No protected body is needed on this fast-tie trace. This is one concrete tight native execution in the restricted model, not a general native minimax equivalence.

| Compiled tie rule / baseline | Lower | Equal | Higher |
|---|---:|---:|---:|
| curve_protected_tie / local_budget | 3 | 33 | 0 |
| curve_protected_tie / upstream2 | 17 | 13 | 6 |
| curve_protected_tie / unknown_budget_threshold | 10 | 22 | 4 |
| curve_protected_tie / always_protected | 25 | 11 | 0 |
| curve_fast_tie / local_budget | 11 | 25 | 0 |
| curve_fast_tie / upstream2 | 18 | 18 | 0 |
| curve_fast_tie / unknown_budget_threshold | 11 | 24 | 1 |
| curve_fast_tie / always_protected | 33 | 3 | 0 |

There are36 matched lambda/script cells per comparison. The default compiler improves only3of36 cells over the stronger same-remaining-B local rule, with33 ties. Those gains are small here: lambda3/cross_stage424vs432, k_full_v_split424vs432, v_two_end_split420vs432. Fast-tie improves11of36 with25 ties. Default protection on equal minimax value can be more expensive on a particular realized script: it loses6of36 to the two-attempt replica and4of36 to the unknown-B threshold. Fast-tie still loses one cell to that threshold (lambda1/cross_stage216vs116). No pointwise dominance or observed average improvement is inferred from minimax optimality.

All fixtures are author-controlled extensions of previously observed inputs. The source proof justifies operation-entry caps W4,104 only for the specified single-range immutable structure and synchronized value updates. Charges exclude CPU operations outside the selected counters, memory allocation, waiting, source construction and policy setup. The actual compiler's208/208/215-byte profiles, their hashes, all-budget Bellman checks and native loads are preserved. Export elapsed costs include the stated per-input compilation/checking/serialization/file-write/query scope, but not the final receipt write or end-to-end source setup.

The baseline named upstream2 is a two-attempt-rule replica under the same strict harness, with native elapsed-time fallback disabled. A reached COMPLETE for an already-drained cycle is explicitly recorded as SKIP_CLOSED_CYCLE. Suppressed/unreached script cuts remain in every trace. Strict harness errors, all old domain corrections, prior artifacts and adverse results remain preserved.

Full216 traces, all36 cost rows, and per-body/decision/clock ledgers are in attempt01 and SUMMARY01.json. Regression results are recorded separately. New native abort experiments require a different, pre-fixed input; this packet will not be rerun to obtain missing aborts.

The four unchanged upstream regressions and six preserved MAX-key repair controls all passed after the strict hook changes (16.08s build/run), with fresh XML receipts in regressions01.

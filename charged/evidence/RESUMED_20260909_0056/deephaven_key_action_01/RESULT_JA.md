# Genuine changing Action through public EventDrivenUpdateGraph — exploratory result

All36 pre-fixed native cells completed successfully in14.92s including build/run; all36 passed the pre-outcome trace checker, and all9 corrupted traces were rejected. There were0 failure/timeout/invalid/unexecuted cells. Every Action mutation was caused by one of33 recorded public requestRefresh calls, each within its caller-owned q bound. No new source/body instrumentation was needed.

Unlike the predecessor same-value Action notifications, node1 actually alternates byte4 Contract and byte3 ExpandAll. The independent DFS oracle checked28 expanded-size31 results and8 expanded-size17 results. The trace-derived successful K/V epoch pairs are {'0,0': 7, '1,1': 6, '0,1': 19, '0,2': 2, '1,2': 2}. In particular two executions retained a contracted K view from epoch1 while returning payloads from epoch2, whose live key Action was ExpandAll again. This checks persistent captured-parent semantics under genuine changing inputs. The two-valued Action is not used to infer a unique epoch; the separate successful-body/clock ledger supplies the captured epoch.

Source proof supplies common K4/V104 prefix caps for this fixed hierarchy and modified-column set; complete Contract V bodies cost89 selected operations. All actual weighted costs remain below charged caps, and every imported-policy charged cap remains below the existing all-budget profile. The inherited profile_3 bytes are unchanged. The32/17 node-visit and64 output-cell counts are selected operations, not all API instructions or a timing metric.

| Script | Curve actual / cap | Local actual | Two-attempt actual | Curve K/V epochs | Curve actual refreshes |
|---|---:|---:|---:|---:|---:|
|none|108 / 108|108|108|0 / 0|0|
|k_dir_full|97 / 112|97|97|1 / 1|1|
|v_parent_full|212 / 212|212|212|0 / 1|1|
|v_node_full|212 / 212|212|212|0 / 1|1|
|v_cell_full|212 / 212|212|212|0 / 1|1|
|v_end_full|212 / 212|212|212|0 / 1|1|
|k_end_split|101 / 116|101|113|1 / 1|1|
|v_end_split|316 / 316|316|628|0 / 1|1|
|v_node_split|316 / 316|316|628|0 / 1|1|
|v_two_end_split|420 / 420|432|628|0 / 0|0|
|cross_stage|424 / 424|432|632|0 / 2|2|
|k_full_v_split|275 / 320|432|542|1 / 2|2|

Across12 fixed scripts, the curve policy uses fewer selected weighted operations than the local rule in3 and the same in9; versus the two-attempt replica it is lower in6 and equal in6. These are policy-conditioned script executions. Protection/termination suppresses some refresh requests, so these comparisons are not equal-realized-writer-workload timing comparisons. The two-stage compiler is still an upper-bound application; the previously observed phase-aware420<424 refutation of native optimality remains. Ordinary Web uses a static key table; this remains an author-built supported-server API composition, not a preexisting deployed workflow.

This changes the application input content and tests returned structure. It does not address the separate lack of nonzero-call-fee calibration, charged-model performance scaling, general production impact or elapsed-time benefit. All prior adverse results and fixed same-action raw bytes remain retained.

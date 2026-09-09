# Public EventDrivenUpdateGraph integration result

All12 fixed native cells succeeded (13.67s build/run), and all12 passed the independent author trace checker. Five deliberately corrupted traces were rejected. Every cycle was caused by one actual public requestRefresh call on an isolated EventDrivenUpdateGraph; no ControlledUpdateGraph start/complete test method was used. A source Runnable latch exposed the interval after native cycle start and before data updates. The writer then used the same requestRefresh call to perform notifications and complete that cycle.

The caller supplied a maximum q of refresh invocations and the trace counted each actual invocation. This supplies an explicit source for the finite update bound in an author-built API composition. It does not establish a naturally finite bound for the usual Periodic graph, a preexisting deployed application, or a bound for hidden/external writers.

| Cell | Selected weighted cost | Charged cap | Abstract cap | Actual refreshes | Failed callbacks |
|---|---:|---:|---:|---:|---:|
| 3_none_curve_fast_tie | 108 | 108 | 108 | 0 | 0 |
| 3_none_local_budget | 108 | 108 | 108 | 0 | 0 |
| 3_none_upstream2 | 108 | 108 | 108 | 0 | 0 |
| 3_v_end_split_curve_fast_tie | 316 | 316 | 316 | 1 | 2 |
| 3_v_end_split_local_budget | 316 | 316 | 316 | 1 | 2 |
| 3_v_end_split_upstream2 | 628 | 628 | 316 | 1 | 2 |
| 3_cross_stage_curve_fast_tie | 424 | 424 | 424 | 2 | 4 |
| 3_cross_stage_local_budget | 432 | 432 | 424 | 0 | 0 |
| 3_cross_stage_upstream2 | 632 | 632 | 424 | 2 | 3 |
| 3_k_full_v_split_curve_fast_tie | 320 | 320 | 424 | 2 | 3 |
| 3_k_full_v_split_local_budget | 432 | 432 | 424 | 0 | 0 |
| 3_k_full_v_split_upstream2 | 632 | 632 | 424 | 2 | 3 |

The exact208-byte lambda3 all-budget profile from prefix_import_02 was loaded unchanged. Native returned row order, immutable structural columns, consistent payload epoch, per-body K4/V104 counters, clock transitions,2q bound and compiled costs were all checked. The source hook bytes are unchanged from the ten successful regression/control tests in that packet.

The ordinary Web tree path constructs a static key table, so its K extraction does not retry. The two-refreshing-stage benefit here is limited to the supported server API configuration exercised by the author fixture; it is not asserted for ordinary Web use. The fixed hierarchy is motivated by an official real-time-tree example, while the finite-refresh mechanism is an existing public API. The conjunction is newly integrated here, not presented as a previously deployed end-to-end scenario. Counts exclude waiting, all source construction, graph setup, API instruction overhead and elapsed time. Script requests may be suppressed by protection/termination, so realized writer activity is also reported.

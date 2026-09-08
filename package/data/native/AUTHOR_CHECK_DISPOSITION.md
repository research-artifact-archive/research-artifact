# Interpretation of controls and implementation checks

The read-only author-side report found no concrete core policy/kernel mismatch.
Its phase-timing issue is already retained in REPORT_JA.md and the paper.

Core native comparison has 19,640 paths; four controls bring the total to19,644.
The hybrid path count4,644 in preparation includes four controls. The397 orders
are candidate model orders, not397 native workloads. COMPARISON_ANALYSIS.json
excludes controls and duplicate layouts, giving192 priced roots.

Controls intentionally execute one all-normal path. Their expected maximum is
the selected-path cost, while the adjacent model_excess field records the full
unmodified model's worst value. In parent-postwrite-ideal, actual/expected control
cost120 differs from the full-model144; this is not an equality claim or native
failure. Keep both original fields and clarify them rather than overwrite results.
The postwrite increments the true write count but does not consume the policy's
failure-based local budget. Thus these controls check captured milestones, not
optimal adaptation given knowledge of every external write. The paper now makes
the separate budget/count interpretation explicit.

The ordered native implementation uses the emitted threshold and a cursor, but
also scans its suffix for an assertion and checks physical readiness. It does not
demonstrate constant-time total selection overhead; no such native timing claim
is made. The source was read only, no native path rerun occurred, and the author
checker is not an independent blind reviewer. Raw code-check findings are saved
in AUTHOR_CHECK_RAW.json without claiming theorem closure.

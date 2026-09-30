# Trace footnotes for integration

以下は各 2 文の脚注用英文。図を bad path 一本だけで unrealizability の証明と扱わないための補足である。

**Policy(2).** “The displayed six-step path starts in the logged old state and executes service, start-audit, stop-audit, stop-role, transfer, and start-role; the unlogged root requires five steps in this returned policy. Each possible first global boundary reaches monitor error, and the losing conclusion is checked with the complete returned 16-state certificate rather than with one displayed failure.”

出典: `explanatory_traces/policy_fine_worst_path.json` の rank6/六辺、`policy_global_boundary_buckets.json` の両初期 root×二 global events、`../policy/v2/validation/certificate_mechanism_audit.json`。Direct-Full の返却 rank5 と矛盾せず、最適性は主張しない。

**Canary(2,1).** “The fine policy retains both transfer outcomes; its worst trace is transfer-1, broken-report-1, recovery-1, transfer-2, broken-report-2, recovery-2, with rank decreasing from six to zero. Under the product transfer, BP/BP is physically broken immediately and the second uncontrollable broken report reaches monitor error before recovery can be guaranteed; the losing result uses the full five-state certificate, not this path alone.”

出典: `explanatory_traces/canary_fine_worst_path.json`、`canary_merged_bad_path.json`、`../canary/v1/tables/certificate_checks.json`。残る UC report があると ordinary controlled restart が必ず disabled になる、とは述べない。BP/BP の physical healthy=0 と、二つ目の report 後の tester error を分ける。この逐次復旧 trace は n2m1 に限定し、族全体の一律順序に一般化しない。

記録時刻: 2026-09-29T19:44:38+09:00。

# Post-run aggregation protocol

This is a result/receipt integrity and coverage summary, not another filter run.
No target or reference module is imported. Freeze this protocol and summarize.py
with all available input freezes/receipts/raw hashes before executing aggregation.
Require attempt02's streams receipt to exist; otherwise report its absence.

Verify every frozen input/code/snapshot hash, every raw/failure hash in each family
receipt, and every predecessor hash in attempt02. Read all raw rows to verify
initial query/action counts, policy prefix/leaf/edge counts and invalid-case rows.
Derive large-stream coverage from explicit terminal records. Combine all 37
completed attempt01 series with the two complete attempt02 series. Preserve the
first attempt's TIMEOUT, partial series, unstarted series, original unexecuted
steps and exact repeated-prefix count. Compare every overlapping stream-step raw
record for equality; no repeated row becomes a second independent observation.

Report constructor counters separately from per-query and per-completion maxima,
grouped by fixed stream input. Derive table/JSON only from existing immutable raw.
Do not interpret resource elapsed seconds as target performance or latency.
Summarization itself has a 60-second watchdog; outputs are exclusive new files.

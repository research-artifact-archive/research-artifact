# Post-matrix sensitivity to the counted operation boundary

This is a descriptive source/ledger reconstruction after fixed matrices02/03B and review180. It creates no new native execution and does not retroactively preregister a new result population. Preserve all384 existing cached/two-cheap pairs, including expected overflow cases. Reuse the global-attribution third run only through its previously verified identity to matrix02; do not pool populations.

Compare three explicit units: (a) one public traversal invocation, always1 per policy execution; (b) the original logical validation/completion block Q; (c) source-level invocations of exactly six named primitives: rcu_read_lock, rcu_read_unlock, read_seqbegin, read_seqretry, read_seqlock_excl, read_sequnlock_excl. Counts(c) refer to these boundaries after expanding the wrapper choice, not internal spin iterations, machine calls or instructions. Instrumentation, gates, oracles and setup sampling are excluded. These choices are sensitivity axes, not alternative measurements of the same quantity.

For both compared source functions, the saved number R of RCU sections equals the number of read_seqbegin and read_seqretry invocations. Their RCU enter/exit counts each equalR. Saved G counts paired guard acquire/release. Hence the six-primitive sum is4R+2G. Cached logical Q=R; two-cheap logical Q=R+G. Confirm these equalities on every saved pair and retain individual counts. Inspected source lines and file hash bind the derivation.

The original theorem's logical cap does not become a bound on public kernel API calls. Do not claim that every reasonable count distinguishes2 from3, or that the source caller requires this grouping. Native body/guard results remain independent vectors.

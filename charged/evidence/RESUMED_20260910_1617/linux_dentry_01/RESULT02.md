# Higher-call-cap source comparator: one fixed execution

Version02 retains all original1540 input rows as regression cases and adds384 same-fixture rows for two cheap validations followed by fresh protected fallback. It also applies the pre-execution sharpened2C+2 body bound and separates KUnit into nine cancellable groups. The original version01 source, protocol and results remain unchanged. The new1924 rows are not an independent disjoint population to pool with the previous1540.

The actual Linux v6.12 guest run at2026-09-11 00:56JST completed successfully in16.934s including the incremental build. All nine KUnit groups pass. All1920 valid rows agree with the full-path/overflow oracle:948 successful paths and972 expected overflows. The four existing deliberate defects are again detected as expected; they remain defects. Offline recomputation checks every row, all2878 body records, and all384 new/cached pairs, without errors or kernel lock/RCU/panic diagnostics. Raw log SHA-256:2ca6e4ed7ab6d130d8b175e14ce82bd86ef5352edc59237fa99c0e5c4eec3b47.

## Decisive paired comparison

| Actual writes at the fixed gates | Pairs | Body T and L_T/output | Cached Q / guards | Two-cheap Q / guards |
|---|---:|---|---|---|
| B=0 |102|Equal|1 /0|1 /0|
| B=1, first invalidation only |138|Equal|2 /1|2 /0|
| B=2, both invalidations |144|Equal|2 /1|3 /1|

The pairs agree on every per-body counter vector, not just the scalar sum. The higher-cap comparator removes the exclusive-reader acquisition on all138 first-invalid/second-valid pairs while preserving body work. On the144 two-invalidations pairs, it needs one more counted validation/completion operation. It therefore has a different universal call cap, Q≤3 versus Q≤2; the result is not dominance at the same Q contract. Nor does it establish a native caller requirement for Q2. The fixed source baseline itself uses at most2 such logical operations, but that is an implementation design, not a demonstrated SLA.

For the short first-write example, upstream, cached, and two-cheap have T41 and respectively L_T12,0,0. Their guard counts are1,1,0. Under the two-write example, cached and two-cheap both have T70 and L_T29; Q changes2→3. This identifies a resource omitted by a body-only protection objective: a matching cached completion still enters the global lock. The motivating historical source change concerned contention including acquisition and hold, so the distinction matters when interpreting practical benefit.

The body-work equality is a result for the common scripted gates. It is not a coupling theorem for arbitrary physical schedules; a successful early lockless validation can return before a writer that would affect the later acquisition in the other policy. Root postambles, RCU, guard instructions, queueing and waits remain outside T. No writer-blocked time or native elapsed speedup is claimed. The source event ceiling is8192 at capacity4096 and remains loose for short paths. No nofault-copy failure or allocation-failure injection was observed/performed. Snapshot64 still has five capacity fallbacks and all separate capture/refcount/allocation costs.

This finding motivates the separate guard_entry_01 theoretical scope extension, where a declared positive cost is added to every guarded completion. It does not estimate a numerical native guard cost, establish native minimax optimality, or transfer the full multi-job/observation contract to Linux.

Records: PROTOCOL02.md, INPUTS02.json, implementation02/, KERNEL_MATRIX_START02.json, KERNEL_MATRIX_COMPLETION02.json, KERNEL_MATRIX02.test.log, MATRIX_VALIDATION02.json, MATRIX_JOINED02.json, MATRIX_COMPARISON02.json. The complete original study remains in its01 files.

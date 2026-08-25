# Ordinary-source construction trace

This directory contains two complementary correctness traces.

`r09-hand-k02-formal-trace.json` is the complete human-hand-checkable
ordinary-source proof fixture. Its exact 598-byte source has two one-state
old/new components and two one-row transfers. The trace lists all 16
`SourceIn` fields; every S0--S4 outcome; the complete four-state/12-bucket
game; four `R_Gamma` and four progress-match rows; both two-state local rank
proofs; full, non-pointer `L` and `Gamma` values; and the correctly numbered
B1--B7, P1--P5/B7, and S1--S7 truth tables. `Lambda=ALL_REACHABLE` and
`b=UNBOUNDED` are explicit proof parameters. The stored native bundle is only
a field-for-field post-hoc code-path match, not an execution receipt or proof
authority. This is not a new evaluation outcome or independent source-to-WIN
replay.

`productioncell-arms2-r2-trace.json` is the complementary machine-checkable,
manifest-bound, field-addressable reconstruction of the already recorded
ProductionCell Arms=2 R2 bytes.  It exposes all 16 `SourceIn` bindings, every
recorded S0--S4 predicate and census, all 10 recorded `Y` fields, and qualified
mappings to S1--S7.  It also binds the separate complete M8p flat-table trace
used for B1--B7.

Run the deterministic checker from the artifact root:

```sh
python3 -I -S -B analysis/check_ordinary_source_construction_trace.py
python3 -I -S -B analysis/check_hand_checkable_ordinary_source_trace.py
```

The ProductionCell checker re-resolves every JSON value reference, reconstructs all
synthetic values by the stated recipe, verifies the exact source and evidence
hash chain, and compares the stored trace with a fresh deterministic
reconstruction.  `tools/verify.py` separately reruns the existing M8t source
and supplied-certificate semantic checkers before checking this trace.  The
hand-checkable checker strictly consumes the complete tiny source, derives
every `SourceIn` value, validates every global/local proof and transport row,
checks S0--S4 and all three correctly numbered theorem maps, and only then
compares the complete stored bundle projection.

Neither trace is a new experimental outcome. The small trace is a same-author
formal correctness proof, and its bundle comparison asserts no run, JAR,
runtime, or timeout provenance; it is not a general/independent frontend or
independent WIN synthesis. The large ProductionCell source, facts, and supplied
historical bundle remain machine-checkable rather than human-hand-checkable.
Its historical Java producer, property/runtime environment, and declared
timeout enforcement are not replayed.  Its recorded
`PRODUCER_VERIFIED_REFINED_WIN` label is not derived or regenerated; the
deterministic checkers validate the semantics of the supplied witness within
the bounded symbolic contract.  There is no independent WIN synthesis,
source-to-WIN replay, materialized mixed global game, general MTSA frontend,
maximum/complete source decomposition, breadth, production, third-party, or
global-LOSS-from-local-failure claim.

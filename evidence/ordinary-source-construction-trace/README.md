# Ordinary-source construction trace

`productioncell-arms2-r2-trace.json` is a machine-checkable,
manifest-bound, field-addressable reconstruction of the already recorded
ProductionCell Arms=2 R2 bytes.  It exposes all 16 `SourceIn` bindings,
every recorded S0--S4 predicate and census used by this reconstruction, all
10 recorded `Y` fields, and qualified mappings to S1--S7.  It also binds the
separate complete M8p flat-table trace used for B1--B7.

Run the deterministic checker from the artifact root:

```sh
python3 -I -S -B analysis/check_ordinary_source_construction_trace.py
```

The checker re-resolves every JSON value reference, reconstructs all
synthetic values by the stated recipe, verifies the exact source and evidence
hash chain, and compares the stored trace with a fresh deterministic
reconstruction.  `tools/verify.py` separately reruns the existing M8t source
and supplied-certificate semantic checkers before checking this trace.

This is not a new experimental outcome and is not a human-hand-checkable
end-to-end source example: the source, facts, and supplied historical bundle
are large.  The historical Java producer, its property/runtime environment,
and the declared timeout enforcement are not replayed.  The recorded
`PRODUCER_VERIFIED_REFINED_WIN` label is not derived or regenerated; the
deterministic checkers validate the semantics of the supplied witness within
the bounded symbolic contract.  There is no independent WIN synthesis,
source-to-WIN replay, materialized mixed global game, general MTSA frontend,
maximum/complete source decomposition, breadth, production, third-party, or
global-LOSS-from-local-failure claim.

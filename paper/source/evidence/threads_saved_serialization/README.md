# Saved Threads merged-policy serialization

This is a new static analysis of ten previously saved merged winning policies: all Threads backpressure instances with n=2–6 and queue capacity B=1,2. No synthesis, winning-policy search, performance measurement, Java execution, or source-file modification is performed. The saturated-offer cases are outside this prespecified cohort; their earlier LOSS results remain unchanged.

## Reproduce

Python 3 standard library only. From this directory, run:

```sh
python3 -B check_saved_serialization.py --output reproduced
```

The default output directory is `output/`. A fresh output path makes the new results easy to compare. The script checks all ten cases and writes every row, including a FAIL row and reason if a case fails. Exit status is nonzero on any verification or negative-control failure. It does not download or load an external solver. The copied inputs are sufficient for this analysis.

## Inputs and provenance

`provenance.json` maps the 40 byte-for-byte copied JSON files to their repository-relative original paths. Each case has `fine.json`, `merged.json`, `certificate.json`, and `saved_result.json`. The policies were saved by the earlier 2026-09-29 Threads campaign under `FSE2027_SUBMISSION_20260914/experiments/witness_20260929/e6/threads/v1/`. The manifest also records the original invocation date and relative job specification. The saved result files contain historical solver timings; this analysis neither measures nor compares performance.

All 40 copied source files were also compared directly with the Git objects at public-release tag `fgducs-c115-20261003`: all 40 are present and byte-identical. Their public-relative paths and individual comparison outcomes are recorded in `provenance.json`, under `results/granularity/e6/threads/v1/`. This script and its derived outputs are new and were not part of that earlier public release. The public input/policy provenance therefore does not imply that this new transformation was checked or published in C115.

## Transformation and checks

The transformer retains every ordinary edge of the saved merged policy. Its one simultaneous transfer edge is replaced by the fixed sequence `rho_1,...,rho_n`. The n−1 added controller states store the saved checkpoint, target, and remaining block members, explicitly representing the finite-memory construction. The verifier is independent of the Java solver and existing checker implementation; transformation and verification are separate functions in the one supplied Python script.

The verifier reconstructs the synchronous local-plant Post relation directly from the copied OLD/NEW component LTSs, including every semantic outcome of each selected action. At every non-goal policy state, every enabled uncontrollable action and every outcome must occur. Selected controllable actions require global UC quiescence, and every handover goal is UC-quiescent. Every edge strictly decreases the supplied natural-number rank, every non-goal has a continuation, and every state is reachable from the complete set of old-endpoint entries. The old and new endpoint plant/controller products and complete projected transition relations are independently reconstructed. Every goal is related to the same unique saved fixed endpoint and its declared loadable target.

The complete ordinary policy graph is unchanged, and contracting each forced serial chain recovers the saved graph. No uncontrollable action is enabled at an inserted phase. Consequently all complete paths correspond under contraction and contain exactly n−1 additional update events. A separate DAG pass checks minimum/maximum complete-path lengths and transfer counts from every entry. This is an event-count statement, not a time or optimality statement.

## Results

All 10 cases passed; no case failed. The 620 entry occurrences belong to related parameter instances. The 630 saved states and 1,982 edges become 660 states and 2,012 edges. Full uncontrollable coverage comprises 1,972 action buckets and 1,972 outcomes; the expanded policies contain 2,012 selected buckets/outcomes in total. Every bucket has one outcome in this cohort.

| n | B | Entries | Saved states/edges | Serial states/edges | Saved/serial max rank | Exact extra events | Status |
|---|---|---:|---:|---:|---:|---:|---|
| 2 | 1 | 8 | 9/13 | 10/14 | 4/5 | 1 | PASS |
| 2 | 2 | 12 | 13/21 | 14/22 | 5/6 | 1 | PASS |
| 3 | 1 | 16 | 17/33 | 19/35 | 5/7 | 2 | PASS |
| 3 | 2 | 24 | 25/53 | 27/55 | 6/8 | 2 | PASS |
| 4 | 1 | 32 | 33/81 | 36/84 | 6/9 | 3 | PASS |
| 4 | 2 | 48 | 49/129 | 52/132 | 7/10 | 3 | PASS |
| 5 | 1 | 64 | 65/193 | 69/197 | 7/11 | 4 | PASS |
| 5 | 2 | 96 | 97/305 | 101/309 | 8/12 | 4 | PASS |
| 6 | 1 | 128 | 129/449 | 134/454 | 8/13 | 5 | PASS |
| 6 | 2 | 192 | 193/705 | 198/710 | 9/14 | 5 | PASS |

`output/summary.csv` retains per-case entry, UC, outcome, rank, endpoint and exact-overhead checks and failure fields. `output/analysis.json` contains complete per-state path bounds and selected endpoint targets. `output/policies/` contains the ten explicit transformed policies. `output/negative_controls.json` retains all 50 corruption tests: per policy, omit an uncontrollable outcome, omit an entry, corrupt a rank, change an identity-transfer outcome, or remove the selected loadable endpoint. All 50 corruptions were rejected, with their observed failure reasons retained.

## Limits

These are ten related finite abstractions, not ten independent applications. OLD and NEW component LTSs are identical, transfer maps are deterministic identities on idle states, and requirements and precedence are empty. No nontrivial environment/transfer interleaving occurs at the inserted phases. Although every action outcome is checked, there are no multi-outcome buckets in this cohort. The construction therefore does not validate the general theorem on nondeterministic transfers, changing local behavior, requirement monitors, initializer boundaries, or nontrivial partial-transfer UC interactions.

The output is a finite model policy, not deployed runtime code. There is no claim of faster synthesis, lower memory use, fewer original application states, or runtime safety. This analysis does not convert the twelve industrial E1 input pairs, extend the generalized-condition applicability counts, or change the earlier WIN/LOSS tables.

The final checker was rerun into a separate output directory; all 14 generated JSON/CSV output files, including the ten policy graphs, were byte-identical across those runs. No original experiment file, public artifact file, or paper source was modified.

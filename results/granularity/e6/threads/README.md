# Threads v1: quiescence controls

This finite family tests an assumption behind a proposed thread-barrier witness. It does not reproduce Kitsune or claim an effect on an operational service. The model and expected outcomes were registered before measurement in DAILY on 2026-09-29 at 17:15:05 JST.

The primary Kitsune article describes per-thread update points and waiting for all threads to reach quiescence. It also explicitly handles progress toward those points: interrupting blocking I/O and waking condition-variable waiters (§3.1–3.1.2, author manuscript pp. 10–12). Thus, that source does not justify treating every whole-thread barrier as losing. The queue, dispatch policy, and arrival regimes below are our finite abstraction, not details attributed to Kitsune. Sources: [TOPLAS publisher DOI](https://doi.org/10.1145/2629460), [author manuscript](https://www.cs.umd.edu/~mwh/papers/kitsune-journal.pdf), and [original OOPSLA DOI](https://doi.org/10.1145/2384616.2384635). The journal manuscript front page contains a placeholder DOI; the real DOI was checked against the publisher.

## Registered model

For every n = 2,…,6 and queue capacity B = 1,2, each worker is idle or busy. Arrival and finish_i are uncontrollable; dispatch_i is controllable. Dispatch consumes one queued request and changes an idle worker to busy; finish_i returns it to idle. Worker 1 carries the queue coordinate to avoid introducing an extra component transfer. An idle worker may transfer to the identical local state in its new version, preserving the queue. Old/new versions share the same scheduling abstraction. Fine transfers affect one worker, whereas the generated all-group action requires every worker to be idle. E1 transfer merging of the fine contract is independently compared to that generated contract.

Two regimes are retained uniformly across all n and B:

- Backpressure: arrival is disabled when the queue is full. Stopping dispatch leaves only finitely many arrivals and finishes before simultaneous quiescence. Both fine and all-group contracts are expected to be WIN; this is a null control, not a separation witness.
- Saturated offers: a full queue still has an uncontrollable arrival/drop self-loop. The environment can sustain that loop without fairness, so both contracts are expected to be LOSS. This is an explicit progress negative control. It does not claim that a real bounded queue always behaves this way.

All reachable states of the old plant with the permissive endpoint controller are initial snapshots; every reachable new endpoint state is loadable. The endpoint product has (B+1)·2^n states. There are no old/new/interval safety testers, no precedence edges, and no additional requirement intended to manufacture a fine/coarse separation. Completion remains the unchanged E1 goal predicate. Expected outcomes are checks, never replacements for measurements.

## Frozen execution

Twenty n/B/regime pairs each have fine Lazy, E1-merged Lazy, generated all-group Lazy, and fine Direct-Full: 80 trials. The fixed order is increasing n, increasing B, backpressure then saturated offers, followed by those four methods within each pair. Each trial uses one JVM, 32g heap, a whole-JVM 1,200 s cap, and no retry. The shared JVM lock excludes concurrent families. New trials stop at 2026-09-30 09:39 JST; unstarted trials remain NOT_RUN_DEADLINE. All errors, timeouts, negative results, preflight outputs, and generated inputs are preserved.

The solver is the read-only E1 JAR, SHA-256 `ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5`. The shared adapter and harness are frozen and unchanged. Grouped inputs retain n physical components and use the documented generated-contract construction helper; no solver source or JAR is changed.

From e6's parent or the repository root, use the shared harness with `threads/v1` at its actual path:

```text
python3 -B e6/tools/run_family.py e6/threads/v1 freeze
python3 -B e6/tools/run_family.py e6/threads/v1 preflight
python3 -B e6/tools/run_family.py e6/threads/v1 run
python3 -B e6/tools/run_family.py e6/threads/v1 analyze
python3 -B e6/tools/run_family.py e6/threads/v1 audit
```

`gen_threads.py` creates the model and fixed schedule. `validate_threads.py` checks component relations and transfer domains, then imports the frozen independent Rolling endpoint checker to reconstruct plant × controller products; the generator uses a separate queue-transition enumeration. It also compares fine/all structures, all endpoint projections/loadable states, and complete controller alphabets. Formal JSON Schema validation is recorded separately and is not claimed when the optional library is unavailable.

## Outputs and interpretation

`tables/results.csv` retains all 80 scheduled rows with variant, expected-check status, measured decision, states, queries, nonempty buckets, successor outcomes, rank/losing-certificate size, elapsed times, budget, SHA values, and raw paths; exact common columns are defined by `tools/analyze_family.py`. Mac times are not Xeon timings. `tables/pairs.csv` has one row per n/B/regime: fine/merged/generated/DF decisions; state and query counts; fine/DF rank; fine/merged losing size; generated full-Post comparison and DF decision checks. `category` distinguishes null (WIN/WIN), witness (WIN/LOSS), both_loss, reversal, and incomplete. No pair is omitted.

`tables/certificate_checks.json` checks every returned WIN strategy edge for strict rank descent and every selected transfer for idle-only, queue-preserving version change. For saturated LOSS it identifies a full-queue initial non-goal state whose physical arrival relation is a self-loop. This is a concrete completion obstruction in the returned certificate, not a claim of a unique cause. E1 independently checks the full returned certificate. `tables/mechanism_reasons.csv` gives one sentence per completed trial. The losing region is the discovered certificate, not the whole game's maximum losing region; rank is a returned completion upper bound, not an optimality claim.

The two family LaTeX fragments are `table_threads_states.tex` and `table_threads_certificates.tex`; the common `results.tex` retains all trial rows. `threads_summary.json` records all categories, failures, and partial status. Aggregation is rerun in a fresh subprocess after each trial and at the end. No main paper or earlier campaign file is edited.

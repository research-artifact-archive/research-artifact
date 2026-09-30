# Quiescent handover: three qualitative checks

These three tiny inputs test a previously uncovered negative boundary: a reached
new-endpoint match can fail the uncontrollable-quiescence condition for loading.
They are separate functional checks, excluded from the original 92 RQ1 jobs,
the application corpus, and all performance statistics. Each input was run once;
all attempts and outcomes are retained. No timing comparison is made.

The old component and its explicit controller have one state `O` with a
controllable `idle` loop. The transfer is `reconfigure_TEST: O -> N0`. The new
controller explicitly follows every new-environment transition, including all
uncontrollables. Every reachable endpoint is safe and deadlock-free. There are
no requirements, monitor initializers, dependencies, or additional components.
`loadable_new_states` selects reachable **new closed-loop state indices**, not
arbitrary component identifiers; the independent endpoint reconstruction checks
their correspondence with `N0` and `N1`.

| Case | New component/controller | Supplied targets | Expected / observed | Reached goals | Handover |
|---|---|---|---|---|---|
| `persistent_uc` | `N0 --spin (UC)--> N0`, plus `idle` | `{N0}` | LOSS / LOSS | none | none |
| `finite_uc_all_targets` | `N0 --step (UC)--> N1`, `idle` at both | `{N0,N1}` | WIN / WIN | `{N1}` | new controller state 1 |
| `finite_uc_nonquiescent_target_only` | same finite-UC input | `{N0}` | LOSS / LOSS | none | none |

In all three cases, `N0` is actually reached after the transfer, has no pending
updates, and matches a supplied load target. Its enabled UC event excludes it
from the goal set. In the finite case with both targets, the returned policy is
`O --reconfigure_TEST (C)--> N0 --step (UC)--> N1`, with ranks `2,1,0`;
the certificate contains three states and two complete event buckets. Only `N1`
has a handover record. Restricting the same input to `{N0}` prevents completion,
even though `N1` remains safe and quiescent: it is outside the supplied target
set. The persistent loop prevents finite completion without a fairness premise.
These outcomes check this contract boundary; they do not measure how often it
matters in the application corpus or the effect of removing non-preemption.

## Saved evidence and independent checks

Each case directory retains `model.lts`, the exact command and attempt result in
`meta.json`, stdout/stderr, the CLI report, and the complete independent Java
game JSON. The WIN case also retains the full FSP policy and handoff JSON, which
includes the complete certificate, all policy outcomes, old-entry map, all new
endpoint states and their transitions, and the sole handover.

`verify_saved.py` reads the restricted FSP syntax of these inputs; it imports no
Java solver or Java game constructor. Before the Java executions, it independently
derived the endpoint products, checked non-suppression of each UC outcome and
endpoint deadlock freedom, built the update game with NP and quiescent goals,
and computed its strong reachability attractor. `independent_oracle.json` saves
these graphs, goal exclusions, ranks and losing closures. The subsequent check
compares every state and complete bucket of the exported Java game and every
WIN certificate/strategy/endpoint/handover record against that reconstruction.
`summary.csv` records the resulting agreement.

The Java CLI separately reports input eligibility, same-semantics certificate
checking and exhaustive independent game checking as passed for all three
attempts; the WIN also passes the atomic Link check. Its standalone LOSS
certificate membership is not serialized by this CLI. For each LOSS we retain
the full game, the independently derived losing closure (all reachable states),
and the CLI's matching losing-certificate state count; this is not a claim to
have compared an unavailable serialized LOSS membership list.

The game exports contain respectively 2/3/3 states, 4/4/5 nonempty buckets, and
4/4/6 candidate queries. The last input queries `step` at `N1` because that event
remains in the new component alphabet; its result is empty. The checker therefore
distinguishes queries from serialized nonempty buckets. All three exports have
exactly one UC bucket and exactly one reached nonquiescent target match.

## Commands and implementation provenance

From the project root, validate the saved results without running Java:

```sh
python3 FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/quiescent_goal_demo/verify_saved.py
```

The one-time execution was:

```sh
python3 FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/quiescent_goal_demo/run_once.py --prepare-only
python3 FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/quiescent_goal_demo/verify_saved.py --inputs-only
python3 FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/quiescent_goal_demo/run_once.py
python3 FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/quiescent_goal_demo/verify_saved.py
```

`run_once.py` refuses to overwrite a saved attempt. A fresh independent
reproduction should copy only the two scripts to a new empty directory at the
same depth and substitute that directory in these commands; preserve the saved
attempts. The script uses the existing Java 17 runtime and the original frozen
JAR at
`FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/bundle/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar`
(SHA-256 `fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07`).
Its exact JVM/CLI arguments are in the script and each `meta.json`: lazy OTF,
endpoint-guided ordering, both preliminary guided limits zero, exhaustive
independent verification, 512 MiB maximum heap, and a 120-second process limit
per case. The two LOSS decisions return the CLI's normal unrealizable exit
code 6; WIN returns 0. These are not crashes or timeouts.

Relevant source under
`Implementation/Source Code/maven-root/mtsa/src/main/java/ltsa/updatingControllers/otf/`:
`FineGrainedSuccessorOracle.java` implements the update guard at lines 202–206;
`FineGrainedUpdateProblem.java` applies physical UC quiescence before target
matching at lines 303–320; `IndependentStrongGameBundleExporter.java` counts
all queries but stores only nonempty results at lines 102–115.

This is a finite model-level functional check. It does not validate monitor
residual correctness, runtime observation/atomicity, real deployment, performance,
or other unexercised features. No original input, JAR, campaign result or paper
was changed. Public packaging must include the two scripts, three input/result
directories and the referenced implementation/JAR, or explicitly document an
equivalent verified layout; this directory alone is not a complete standalone
software distribution.

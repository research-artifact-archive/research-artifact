# Load-target selector functional check

Three independent JVM invocations compile the same one-component LTS and fixed
endpoint controllers through the existing frozen JAR. Only the input clause
`loadable_new_states` changes: `{0,1}`, `{1}`, or `{0}`. The observed decisions
are WIN, WIN, and LOSS. These are qualitative functional checks, not additional
performance samples or additions to the original 27-instance campaign.

The old environment/controller has one idle state `O`. The new environment and
controller both begin at `N0`/`C0`, permit `move` to `N1`/`C1`, and permit idle
at both states; there is no return to `N0`. The direct transfer maps `O` only to
`N1`. The reachable new endpoint product therefore contains both `(N0,C0)` and
`(N1,C1)`, in that BFS order. In particular, index 0 is an eligible new endpoint,
but cannot be reached from the update entry. Restricting the load target to it
leaves only an infinite idle continuation after transfer and gives LOSS.

Both WIN bundles contain the complete two-state new endpoint product and load
controller state 1 at endpoint `new-00000001`. Their winning certificates have
two states, one transfer edge, and maximum rank 1. All three complete reachable
game exports contain two states; the LOSS case has no reachable goal. Goal
states are terminal in this game export, so their post-handoff idle edges occur
in the separate endpoint bundle, not the update-game edge list.

`verify_saved.py` independently reads this fixture's restricted FSP syntax,
constructs endpoint products, evaluates a Python least fixed point, and checks
the exported graph, goal set, physical tuples, empty monitor maps, pending
transfer, rank, and loaded controller state. Its expected result does not come
from Java's claimed decision. Java's separate exhaustive successor/fixed-point
checker also passes, but shares the Java-prepared input. The selected-domain
counts are checked against the logs; BFS index meaning and endpoint eligibility
are checked against the full saved endpoint products. No monitor or initializer,
uncontrollable event, or precedence constraint is present: this check makes no
claim about those features or actual deployment behavior.

From the repository root, inspect/recheck the saved outputs with:

```sh
python3 FSE2027_SUBMISSION_20260914/paper/materials/expression_20260922/evidence/load_target_selector_demo/verify_saved.py
```

`run_once.py` records each command, Java version, input/JAR hashes, all outputs,
and process outcome. It refuses to overwrite any existing attempt. Execute it
only in a fresh copy where these three case result directories do not yet
exist. It uses the existing Java 17 installation and frozen campaign JAR; it
does not build or install software. Process exit code 6 in the third case is
the CLI's explicit UNREALIZABLE result, not an execution failure. No certificate
or handoff is produced for that LOSS case, and its absence is not reported as
a zero-sized winning policy.

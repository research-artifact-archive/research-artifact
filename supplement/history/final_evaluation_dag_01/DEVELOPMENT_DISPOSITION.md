# Development findings before final freeze

PREFLIGHT_RAW.jsonl contains ten SUCCESS outcomes. The author-side reviewer found
no graph-semantic defect in five inspected/checked observed fixtures. The original
preflight runner would classify a validator assertion as INVALID although its
plan requires counterexamples to be FAILURE. No such assertion occurred. Preserve
that implementation, manifest and all ten outcomes; do not relabel or rerun them.
The separate final run.py already catches AssertionError as FAILURE and unexpected
exceptions as INVALID, and retains all unsuccessful units in the denominator.

The first evaluator checked state/action potentials and complete physical Bellman
minima but did not separately enumerate four scalar proof inequalities. Add a new
lemmas.py and evaluate_final.py wrapper for subset monotonicity, cheapest-fast
dominance including ties, all available-subset one-pass inequalities, and cached
fallback bounds. Also check budget monotonicity and discrete concavity over the
fixed finite range. This adds verification obligations without changing the
compiler, graph, scalar recurrence or original evaluator. Keep the read-only
author report as an author check, not independent blind review or proof closure.

The new lemma code is separately frozen and exercised only on the same ten
already-observed preflight inputs before the final manifest. The final 4,232
input values remain unobserved until the final run. Twenty-five checker controls,
including 24 corrupt artifacts, passed; one corrupt profile passes all shape
checks but is rejected by the subsequent Bellman identity check, distinguishing
the two responsibilities.

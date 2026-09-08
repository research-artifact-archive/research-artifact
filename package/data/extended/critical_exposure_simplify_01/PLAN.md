# Selected common-ratio witness simplification

Author-side adaptive exploration, after observing seven strict-gap units in
critical_exposure_02. All seven observed units are seeds; none is relabeled as
held out. The original outcomes remain unchanged. Purpose: find a smaller,
readable counterexample to universal fixed-order optimality under common p/c.

At each iteration consider, in this order, all single-job deletions (both
induced graph and reachability projection through the deleted vertex), all
single-edge deletions, and every strict reduction of one positive work value.
Keep the common lambda fixed within a seed. Canonicalize edge ordering. Compute
the complete scalar adaptive and best-fixed root vectors through the usual
saturation bound, enumerating all topological orders. Among strict-gap neighbors
choose lexicographically least (n, edge count, sum of work, work tuple, edges).
If it strictly improves the same tuple, continue; otherwise stop at a local
minimum. An evaluated case is cached across all seed paths; later encounters
are recorded as references, not rerun observations. Retain every candidate,
rejected move, selected successor and error. No minimality theorem follows.

This search uses the unchanged finite_reference from critical_exposure_02;
it does not provide another independent validation of the discovery code.
Its outputs still need separately fixed all-budget/primitive/native checks.
The selected earliest strict budget and largest relative-gap budget are both
reported. Do not interpret selected gains as application frequencies.

Predeclare 5-second unit cap and300-second campaign cap. Any adverse evaluation
or exhausted cap stops new search and preserves current best and all input
seeds, including unstarted ones. No replacement/retry. All source hashes and
runtime bound before launch. No public release or human evaluation. Stop11JST.

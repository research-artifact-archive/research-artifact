# Independent-block composition: proof boundary

This note records the full boundary behind the paper's independent-block
theorem. It is supplementary explanation, not an extra empirical claim.

Let each finite local game be
`G_j=(Q_j,Q0_j,Sigma_uc,j disjoint-union Sigma_c,j,Post_j,Safe_j,Goal_j,Z_j,~_j)`.
The global game must satisfy all of the following:

1. `Q` is the Cartesian product of the local sets. The nonempty root relation
   `Q0` may be correlated; each local root set is its projection `pi_j(Q0)`.
   Block-changing
   action alphabets are pairwise-disjoint unions, not Cartesian products. A
   separate shared controllable alphabet is permitted only when every such
   action is a pure global self-loop and the composed policy may disable it.
2. An action of block `j` changes exactly coordinate `j`, using exactly
   `Post_j`; every other coordinate is a frame-preserving stutter.
3. Safety is the conjunction of local safety predicates; Goal, load states,
   and the handover relation are coordinatewise products.
4. Components, transfers, monitors (including foreign-action stutter),
   activation observers, residual-soundness inputs, pending actions, and
   precedence are block-local. There is no cross-block nonstuttering
   synchronization or dependency.
5. Every local Goal state is uncontrollable-quiescent: it enables no
   uncontrollable action.

If every local game wins, normalize each local policy to one controllable
action, fix a block priority, wait whenever any uncontrollable action is
enabled, disable shared controllable pure stutters, and otherwise select the first unfinished block's action. The sum of
local ranks strictly decreases on every global step; the handover map is the
product of local maps. Conversely, if a projected local root is losing, an
actual global root carrying that coordinate is retained as a root lift; the
local losing region then lifts to a cylinder preserving the environment
counterstrategy. Root rectangularity is therefore unnecessary, while the
ambient state, Goal, load, and handover product conditions remain necessary.

Condition 5 is essential. With two blocks, let each have a controllable edge
`s_j -> g_j` and an uncontrollable self-loop at `g_j`. Each local game reaches
its Goal, but after one block completes the environment may repeat its loop
forever and starve the other block. Silently terminalizing Goal would change
the paper's no-fairness semantics.

For already supplied local reachable tables, a reverse-edge worklist can check
the factor conditions, solve locally, and emit a succinct priority arbiter,
rank-sum expression, and factored certificate in linear time and space in the
sum of local table sizes. The shipped consumer uses repeated whole-state scans:
it validates conditions and certificates but is not evidence that this linear
implementation bound was realized or benchmarked. The semantic global state
set and any flat FSM remain a Cartesian
product; this artifact never relabels that product as a linear-size state
space. M8o first checks and source-binds the complete restricted one-state
endpoint/update declarations, then emits explicit typed local tables.  A
producer solves those tables and emits local rank/policy/kappa or losing
responses together with the global priority/rank-sum/kappa-product or losing
cylinder.  A separate consumer hashes the reconstructed input, recomputes each
local attractor, checks controllable update typing, monitor and RS projections, complete initial pending
sets, exact update removal and normal-event preservation, update-only local
precedence,
Goal uncontrollable-quiescence, typed handover relation, disjoint alphabets and
the exact asynchronous-product operator, and executes all certified outcomes.
For seven registered inputs and two multistate winning/losing examples it also
constructs and solves the actual flat Cartesian game and compares the complete
winning region and every rank.  The multistate pair exercises nondeterministic
results, an uncontrollable monitor step/error, typed handover, and a serialized
losing counterstrategy; twenty-one single-condition mutations, including update typing, pending
projection faults and unknown or foreign/shared-action monitor and RS changes,
are rejected.

This remains a post-outcome, author-built restricted pipeline.  It does not
discover a partition in an arbitrary flat game, parse arbitrary FG-DUCS LTSs,
validate a native/production loader, or turn the semantic Cartesian state set
into a sum-size set.  The K=20 case is checked only in factored form because
flat enumeration is deliberately bounded.

## Source-native one-way quiet-terminal composition

M8q uses a separate sufficient-result theorem; it is not the converse-bearing
exact-product theorem above. Let an ordinary-LTS contract provide local
abstract games, a finite-memory relation from each concrete source state to a
tuple of local states, and nonempty terminal sets `T_j subset Goal_j`. The
producer must establish all of the following before returning a refined WIN:

1. every concrete old-endpoint root is related to a tuple of projected local
   roots (extra local root combinations are permitted);
2. safety of every related local tuple implies concrete safety, and each
   uncontrollable concrete outcome, or every outcome of the selected
   controllable action, is simulated by the assigned local transition while
   foreign local memories stutter;
3. every local rank/policy strongly reaches its uncontrollable-quiescent
   `T_j`, without treating `Goal_j minus T_j` as terminal;
4. the observer-fibre product of every reached terminal tuple is contained in
   the original global Goal and has a total typed load/handover selector; and
5. the composed finite-memory policy stops immediately on any original global
   Goal, otherwise waits for uncontrollable actions and uses a fixed priority
   among unfinished blocks.

The sum of local ranks then decreases until either the original Goal is reached
early or the terminal product is reached, so the composed policy is a sound
one-way global WIN witness. Failure to find such terminals or a nontrivial
partition is `UNKNOWN`/one-block, never a global loss. This result permits the
correlated ProductionCell roots and Goal states with outgoing uncontrollable
actions while preserving the paper's no-fairness semantics.

The source-native producer runs after parsing and constructing the fixed old
and new endpoint products, but before materializing the mixed-version global
update game. Its dependency closure is conservative and makes no maximum-block
claim. The v4 bundle stores local rank/policy tables, typed Goal payloads,
observer relations, all load selectors, and terminal assemblies. The shipped
Python checker validates their serialized structural consistency without
importing the Java producer, but does not replay ordinary-LTS parsing,
dependency/Post completeness, or tester semantics. Accordingly the public
claim is `PRODUCER_VERIFIED_REFINED_WIN`, with source translation as a TCB, not
an independently source-verified controller or a prevalence result.

## Maximum-block discovery relative to a typed flat table

M8p removes the supplied block boundary but not the semantic types.  Its input
is a complete finite flat table with a total valuation of declared atoms for
every state and load value, complete sparse Post buckets including Goal/unsafe
states (an absent state/action bucket denotes the empty successor set),
action kind/control/typed subjects, Q0/Safe/Goal, handover pairs, and typed
dependency hyperedges.  A dependency hyperedge means that its atoms must remain
in one block; it does not identify which independent hyperedges can be split.
The total atomization and completeness/correctness of these typed dependency
declarations are external input obligations.  The checker validates their use
but does not infer or prove them from arbitrary FG-DUCS syntax.  In each
registered positive, closing both those dependencies and the direct nonshared
action subjects still leaves six units, rather than disclosing the discovered
two-block partition.

The producer first contracts those mandatory hyperedges into support units.
It then enumerates every set partition of the units, from the largest block
count downward.  For each candidate it checks exact Cartesian rectangularity
of Q, Q0, Safe, Goal, Zload, and handover; action-subject locality; foreign
frame preservation; enabledness and the full nondeterministic target set in
every foreign context; controllable global pure stutter; exact pending-action
updates; and local-Goal uncontrollable quiescence.  It counts all maximum-count
candidates and serializes the lexicographically first one.  For each canonical
root cut that exists after mandatory contraction it also returns a checked
PASS or obstruction record.  Exhausting a configured search
budget is explicitly inconclusive, never NON_FACTORABLE.

For a fixed total atomization and exact supplied table, this search is sound
and complete for the theorem's partition class: every accepted candidate
satisfies the listed conditions by direct finite-table checks; conversely,
every admissible partition appears in the finite enumeration.  Thus the
reported maximum block count is exact relative to that input.  This is not, in
general, a claim that the maximum partition is unique, nor a claim of general directed-graph factorization or
automatic recovery of semantic atoms from arbitrary LTS syntax.  With `k`
support units, enumerating all set partitions is exponential (bounded by the
Bell number); the shipped implementation reports its explicit bound instead
of claiming the linear complexity of solving already supplied local tables.

The independently implemented consumer does not import the producer.  It
reparses the table, reconstructs mandatory units, exhaustively enumerates the
same finite search space, and rechecks the maximum count, selected partition,
action assignment, and root-cut obstruction ledger.  For each positive case a
second producer projects the discovered blocks into local games and emits a
rank-sum/priority/kappa witness or a losing cylinder.  A second non-importing
consumer rebuilds those projections, re-solves every local game and the bounded
flat game, and checks the complete transported witness.  The public evaluation has
three non-isomorphic multistate positive tables (two winning, one losing,
including nondeterminism, an uncontrollable progress step, multiple roots,
monitor/RS residuals, precedence, and typed handover) and ten controlled
obstructions.  All are post-outcome author fixtures.

The 43 earlier game bundles are retained only as a diagnostic boundary.  Their
physical vector is a fixed Java string, and they omit action owners/kinds,
complete requirement/RS declarations, precedence, Zload/handover, and
preterminal Goal/unsafe Post.  A conservative coordinate screen therefore
reports co-change components and missing Cartesian tuples but makes zero typed
typed-factorability claims.  It reports 41 C1 variants as ten semantic families,
plus the two author ARDrone adaptations; these are neither 43 independent
applications nor evidence of prevalence.

## Residual-soundness finite product

`analysis/check_residual_soundness.py` implements the paper's finite-product
RS decision procedure for a supplied explicit activation-prefix graph beginning
at the old endpoint's initial state and retaining its history,
deterministic observation transducer, safety monitor, and declared
initialization map. It checks the ordinary/update alphabet partition, exact
observer/monitor alphabet, totality, start-event phase, and the sole
out-of-alphabet hot-swap boundary. Each fixture asserts an exact graph, but the
checker cannot derive or verify that assertion from an FG-DUCS input. It gathers
all history residuals at each activation type and checks the declared
initialization language against each one. On failure it returns both an
activation prefix and a continuation word that is accepted by the declared
initialization but rejected by a reachable history residual.

The three shipped fixtures include a minimal negative case: in the old endpoint,
ordinary event `a` moves the history residual from `m0` to stricter `m1`; after
`hotSwapIn` and before `start_r`, that residual is retained, and
continuation `b` exposes the unsound initialization. A mutation test deletes
the old-history `a` branch and confirms why an underapproximated activation graph can
falsely report the case SOUND. The other two fixtures check a conservative initialization and the
intersection of two histories reaching one activation type. This is a
post-outcome theorem-linked validation of the generic finite-table checker;
it does not build or certify complete activation graphs from the production FG-DUCS input language
and is not prospective or third-party evidence. If an externally supplied
graph is only an overapproximation, SOUND remains sound but a returned
counterexample is only a conservative rejection, not proof that a concrete
FG-DUCS prefix exists.

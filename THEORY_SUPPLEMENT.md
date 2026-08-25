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

For a candidate partition `B=(B_1,...,B_m)`, let `pi_j` restrict the supplied
state valuation to `B_j`, put `Q_j=pi_j[Q]`, and let
`C_j=product_{ℓ!=j} Q_ℓ`.  Rectangularity of `Q` makes each pair
`(x,c) in Q_j x C_j` name one actual row.  If action `a` is assigned to block
`j`, define, for every such row (including rows with an empty bucket),
`T_j,a(x,c)=pi_j[Post((x,c),a)]`.  The exact implemented predicate
`Acc_square(B)` is the conjunction of all of the following finite tests:

1. `B` covers the atoms exactly, every externally complete dependency and
   every nonshared action subject lies in one block, and pending/update typing
   is local;
2. `Q`, `Q0`, `Safe`, `Goal`, and `Zload` are the Cartesian products of their
   block projections;
3. the supplied Goal--load handover relation `H` is the product of the local
   relations `H_j={(pi_j(q),pi_j(z)) | (q,z) in H}`;
4. for every `j,a,x` and **every** `c in C_j`, all targets preserve `c`, and
   `T_j,a(x,c)`---including its emptiness and its full nondeterministic target
   set---is identical across all foreign contexts;
5. every shared action is controllable and has exactly the singleton bucket
   `{q}` at every global row; and
6. every local Goal projection has an empty bucket for every local
   uncontrollable action.

For an accepted partition, `Post_j(x,a)` is this context-independent common
target set.  The local roots, safe states, goals, load states, residual/monitor
data, and handover relation are the corresponding projections.  The checks
therefore imply the exact asynchronous frame product, typed-data locality,
product safety/Goal/load/handover, shared controllable pure stutters, and local
Goal uncontrollable quiescence required by the composition theorem.

The `Q0` product check is deliberately stronger than that theorem: the theorem
also permits a correlated nonempty `Q0` with local roots `pi_j[Q0]`.  M8p v1 is
therefore sound for evidence transport after local witnesses are checked, but
complete only for this stricter **root-product acceptance class**.  In
particular, `ROOT_NONRECTANGULAR` is a procedure-relative obstruction, not a
proof that no partition allowed by the broader composition theorem exists.
The reported maximum is the maximum satisfying `Acc_square`, relative to the
supplied atoms, complete preterminal table, and externally complete dependency
declarations; no broader correlated-root maximum is claimed.

The producer contracts mandatory hyperedges into units and enumerates every
set partition in descending block count.  It counts the first accepted layer
and serializes its lexicographically first member; every canonical two-block
cut receives a PASS or first-obstruction record.  The one-block candidate is
checked for table eligibility.  A configured resource bound raises an
inconclusive outcome and is never converted to NON_FACTORABLE.  With `k` units,
this exhaustive search is bounded by the Bell number and makes no linear-time
discovery claim.

`analysis/trace_typed_partition_predicate.py` exposes the predicate without
short-circuiting for a complete two-unit correctness table.  Its saved trace
enumerates both unit partitions, every Cartesian source/action context,
Booleans for all conjuncts, the empty and nonempty local Post buckets, projected
roots/safety/goals/load/residual data/handover, the first accepted layer, and
the composition-premise mapping.  Deterministic `--check` recomputes the exact
JSON, and mutations establish that foreign-context enabledness, foreign-frame
changes, and correlated roots cannot be silently omitted.  This trace is a
finite correctness witness, not a new application or performance result.

The independently implemented consumer does not import the producer.  It
reparses the table, reconstructs mandatory units, exhaustively enumerates the
same root-product search space, and rechecks the maximum count, selected
partition, action assignment, and root-cut obstruction ledger.  For each
positive case a second producer projects the discovered blocks into local
games and emits a rank-sum/priority/kappa witness or a losing cylinder.  A
second non-importing consumer rebuilds those projections, re-solves every local
game and the bounded flat game, and checks the complete transported witness.
The public evaluation has three non-isomorphic multistate positive tables (two
winning, one losing, including nondeterminism, an uncontrollable progress step,
multiple roots, monitor/RS residuals, precedence, and typed handover) and ten
controlled obstructions, including one correlated-root case rejected only by
the stricter root-product predicate.  All are post-outcome author fixtures.

The 43 earlier game bundles are retained only as a diagnostic boundary.  Their
physical vector is a fixed Java string, and they omit action owners/kinds,
complete requirement/RS declarations, precedence, Zload/handover, and
preterminal Goal/unsafe Post.  A conservative coordinate screen therefore
reports co-change components and missing Cartesian tuples but makes zero typed
typed-factorability claims.  It reports 41 C1 variants as ten semantic families,
plus the two author ARDrone adaptations; these are neither 43 independent
applications nor evidence of prevalence.

## Complete hand-checkable ordinary-source construction trace

`analysis/check_hand_checkable_ordinary_source_trace.py` checks the exact
598-byte `inputs/correctness/r09-hand-k02.lts` proof fixture. A strict,
fixture-specific grammar consumes all 15 noncomment declarations and rejects
unconsumed syntax. The source has two one-state old components, two one-state
new components, and two one-row transfer relations. Its complete `SourceIn`
therefore has two component records; one-state/one-edge old and new endpoint
controllers; two transfers; empty old/new/update requirement, observer, and
activation domains; two update progress actions with no precedence; the exact
three-action controllable set; and explicit proof invocation parameters
`Lambda=ALL_REACHABLE` and `b=UNBOUNDED`. Every one of the 16 fields is
materialized rather than summarized.

S0 checks the exact bytes and all one-state declarations. S1 obtains two
singleton dependency receipts and partition `[[0],[1]]`; shared `idle` is a
pure self-loop. S2 has, per block, precisely an all-old root at rank 1 and an
all-new quiet Goal at rank 0, one complete candidate bucket, one outcome, and
one strategy bucket. Thus the complete totals are two roots, four ranked
states, two candidates/outcomes/strategies, and two full/quiet Goals. S3 has
the complete four-state/12-bucket mathematical game, all four `R_Gamma`
pairs, all four progress matches, the three fixed-priority policy cases, an
empty activation domain (so its condition is vacuous), two explicit
empty-vector observer relations, one load selector, and one terminal fibre.
S4 derives the one-way WIN conclusion from the checked premise vector and
serializes the full `Y`: `L` contains both complete games/certificates and
`Gamma` contains actual relation, match, observer, activation, selector, and
terminal rows. The maps are Theorem 5.3 B1--B7, Theorem 5.4 P1--P5 with B7 as
a separate transport gate, and Theorem 5.5 S1--S7.

The stored native bundle is checked field-for-field against this construction
only as a post-hoc code-path match; no run, JAR, timeout, or execution receipt
is asserted, and its literal producer tag is not premise authority. This is a
same-author correctness proof, not a new scientific outcome. The input is
synthetic and adds no application/cluster/denominator, held-out, third-party,
production, breadth, independent source-to-WIN, or global-LOSS evidence.

## Manifest-bound large ordinary-source construction trace

`analysis/check_ordinary_source_construction_trace.py` gives a field-addressable
consistency replay for the already recorded ProductionCell Arms=2 R2 source.
The raw 35,136-byte source (SHA-256
`117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43`)
is the `SourceIn.bytes` value; path, byte count, and digest are manifest
metadata. The other fifteen values are resolved from exact RFC-6901 pointers.
Typed `IDENTITY`, `ARRAY_PROJECT`, and `OBJECT` constructions are executed by
the checker before their canonical hashes are accepted. The recorded outer
bound is 180 seconds; Java, heap, JAR, and elapsed-time fields remain runtime
provenance and timeout enforcement is not replayed.

The trace records both independently reconstructed 81-state/216-edge endpoint
controllers, the two components and transfers, 12 old plus 12 new safety
machines, 24 transition requirements, 22 observers/registry rows, 12
activation sources, 39 controllable actions, and the load rule. S0--S4 then
bind the exact 126/137 fixed endpoints, 114 dependency receipts, partition
`[[0],[1]]`, two supplied proofs, 24 roots, 116 ranked states, 2,560 candidate
buckets/1,424 outcomes, 124 strategy buckets, 24 full and eight quiet Goals,
two Goal payloads, 16 quiet-terminal tuples, 1,010 observer pairs, 218
activation pairs, 137 selector signatures/endpoints, and one checked terminal
fibre. The historical solver censuses 127,174 states, 831,356 successor
queries, and 294,632 outcomes are explicitly recorded as producer census, not
theorem premises.

All ten historical `Y` fields are reconstructed. In particular,
`s=PRODUCER_VERIFIED_REFINED_WIN` remains a recorded producer label. The
separate M8t/M8s check validates the semantics of the supplied symbolic
witness and transport, but does not derive `s`, synthesize WIN, or replay a
source-to-WIN execution. Accordingly S1--S7 are marked as mappings checked
within that supplied symbolic contract, not unconditional theorem-premise
PASS results. The M8p flat fixture and its exact two-partition trace are
manifest-bound and separately recomputed for B1--B7.

This complementary large trace is machine-checkable rather than
human-hand-checkable. It is
not a new outcome, a materialized mixed global game, general-source support,
independent/held-out/third-party/production evidence, a maximum or complete
ordinary-source decomposition, or evidence for global LOSS after local
failure.

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

# Rich native observations and the retained-refresh model

Author-side theorem draft, 2026-09-10. This supersedes neither the old full-repreparation experiment nor its proof record. It states explicit conditions for the retained-refresh action class. Finite source executions corroborate the mapping; they do not by themselves prove optimality over all programs using Valkey.

## Abstract interface and objective

Let a fixed finite component set have positive transform weights w_i and a fixed family Γ of nonempty writer footprints whose union covers every component. The attainable masks are unions of finite Γ-words. Let c(D) be the shortest word length producing D, including c(empty)=0, and h(D)=sum_{i in D} w_i. P=sum_i w_i. The writer budget B is a nonnegative integer upper bound, not a promised number of writes or a distribution. Policies are deterministic, do not know B, and may remember their complete permitted observation history.

The operation either completes directly, for S=(alpha+beta)P+rho, or pays I=beta P+rho for an initial full preparation and uses at most q validation calls. Each call reveals D. Acceptance costs rho+(alpha+beta)h(D) and completes. Rejection costs rho+beta h(D), refreshes precisely the dirty transforms, and leaves a logically fresh full preparation for the next call. A last call must accept. Here alpha,beta,rho are nonnegative supplied resource coefficients. The objective is alpha L+beta W+rho Q_wire, where L is transform work inside the accepting atomic call, W is total foreground transform work, and Q_wire is foreground commands. It is not a model of elapsed time or bytes on the wire.

For X in {abstract,native}, write C_X(P,B) for the supremum operation cost of policy P against permitted environments with at most B writes, K_X(B)=inf_P C_X(P,B) for the budget-informed benchmark, and delta_X=inf_P sup_B(C_X(P,B)-K_X(B)). The informed infimum can choose a policy separately for each B. The unknown-budget infimum must choose one policy for all B. Completion and the call cap are part of admissibility, including costs before completion.

## Two sufficient conditions

**U: an upper-bound implementation for every abstract policy.** Every abstract policy has a native implementation such that every permitted native run projects to a legal abstract run, preserving actions, the completion contract, and the cap, with native cost at most its abstract cost. If native run intervals yield D_1,...,D_k, require

    sum_j c(D_j) <= committed writer calls <= B.

This is a statement about every permitted native execution. Existence of a canonical c(D)-write realization alone does not imply U.

**N: one budget-independent canonical simulation.** Fix one prefix-consistent, causal native response generator N for all abstract histories and actions. For every abstract legal run with at most B writes, N realizes the same action/mask history through actual permitted native API calls with at most B writes and native cost at least the abstract cost, preserving completion and the cap. N supplies every native observation allowed to influence the selector, at its real observation point. Its initial state, writer values, least-word tie-breaking, and response construction must not depend on B. Responses before the next adversarial mask is chosen cannot depend on that future mask. Extension is required from canonical reachable states; it is not required from every possible native state.

Consequently, for each native policy P_N, running its private state against N defines one abstract policy Phi_N(P_N), shared across all B. The relevant quantifier order is

    exists N; for every P_N exists Phi_N(P_N);
    for every B and every legal abstract environment E_A(B)
    exists a legal native environment E_N(B)

whose induced run has the stated correspondence. The native environment must remain budget-legal off its intended path as well; stopping all writes on an unexpected branch suffices for the deterministic realization argument. No future B-dependent behavior is supplied to P_N.

## Consequence and proof

N gives C_native(P_N,B) >= C_abstract(Phi_N(P_N),B) simultaneously for all B. U gives the reverse inequality for the implementation of every abstract policy. Taking informed infima yields K_native(B)=K_abstract(B) first. Subtract this common K(B), take the supremum over B, and then the unknown-budget infimum: both inequalities yield delta_native=delta_abstract. Thus arbitrary extra observations do not invalidate this lower bound when N can realize them consistently. This does not assert that an arbitrary rich history has minimum write budget sum c(D_j).

For example, a visible version jump 10→13 may require three writes although its dirty mask has c(D)=1. U uses the lower bound 1<=3. N may choose the distinct legal jump 10→11 and simulate the native policy on that history. Replacing the actual three-write minimum by one for the original rich history would be incorrect and is unnecessary.

## Instantiation in the pinned author API

Sources are valkey_manifest_01/writer.lua, valkey_refresh_02/step.lua, full_server.lua, and run01.py, bound to their exact hashes in run01/INPUT_MANIFEST.json. The unmodified Valkey source/build pin is in valkey_manifest_01/SOURCE_FETCH.json and BUILD02_RESULT.json. The later RESP timing scripts use a different reply encoding; they are separate byte-bound sources.

The operation class fixes these commands and the initial/full and dirty-only outside transforms. The selector may inspect the history of returned versions, payloads, digests, status and action state where the interface makes those values available. Allowing these observations does not allow extra data access, a different transform algorithm, skipping prescribed transforms, preparing only a subset initially, or changing the publication contract. The concrete compiled selector currently uses only masks and its finite state. The following argument applies to other deterministic selectors in this same operation class; it is not a claim that the current source implements an arbitrary selector supplied by the caller.

The trusted writer uses only Γ footprints, keeps payload lengths fixed, and performs each footprint in one normally completed writer.lua invocation. The script increments canonical decimal strings without numeric conversion, computes fields before its final HSET, and commits exactly the specified footprint. Γ membership is a caller contract: writer.lua does not enforce it. The admitted executions exclude expiry, deletion, version reset/reuse, alternative writers, malformed input, script errors, reply loss, resource exhaustion and connection recovery. Atomicity is used for successful calls and is not treated as error rollback. Ordinary command progress and sufficient finite representation/memory for the admitted run are assumptions, not wall-clock bounds.

For U, the initial HMGET supplies all immutable version/payload copies from one atomic capture. On rejection, step.lua reads all current versions and each dirty payload during the same atomic invocation. A clean component retains a correct digest because unchanged versions imply no admitted writer changed its payload. A dirty component is recomputed outside from the captured bytes. Therefore the retained clean digests and refreshed dirty digests collectively form a correct full preparation at the rejection's capture point, even if later writes race with outside hashing. The next logical interval starts at that capture point. These successive intervals are disjoint. Monotone versions imply that each interval's D is exactly the union of its committed Γ footprints. Thus c(D) is at most its actual writer calls, and their sum is at most B. Writes before the initial capture can be ignored for this inequality; writes after publication cannot affect the historical completion result.

At acceptance, all version checks, dirty transforms, result encoding and SET occur within one successful atomic script. The returned and published vector equals current versions and payload digests at SET. Subsequent writes do not invalidate this historical linearization result. A rejection performs no SET. The direct script produces that same kind of completed publication from its own current state; sameness of the completion contract does not require two alternative executions to publish the identical value at different times.

For N, fix initial canonical versions and fixed-length payload strings. For each attainable D fix the lexicographically first shortest Γ-word. After each logical capture and before the following validation, execute that word in order. Each update may write the same payload bytes again while incrementing its version; invalidation depends on version identity, so this is a legal realization. Do not insert other writes. Initial replies and later pre-mask replies are determined by the canonical past. Version strings, payloads, digests, and actual response encodings are then determined by that past and the next mask at the appropriate observation point. Rejected logical captures extend the same native state, establishing prefix consistency. This construction needs at most q*max_D c(D) writer calls on any operation path; it does not need unbounded version growth merely because B ranges over all integers. Every abstract play is therefore realizable at its own sum of least counts with the same prescribed transform and command resources. A direct root action can be realized without intervening writes.

The SHA1 compression-call measure follows fixed payload lengths: w_i=floor((length_i+72)/64). The instrumented and unmodified source computations were paired, and padding boundaries were checked independently against digests. The source mapping concerns prescribed transform work and foreground command count. It does not charge all version processing, Lua table parsing, copies, encoding, GC, SET, or scheduler delays. In particular decimal strings and JSON/RESP lengths vary; total wire bytes are not a constant rho per command. Clocks, timing, random coins, connection state and uncontrolled external information are not selector observations in this theorem.

## Limits retained

The proof is conditional on the exact operation class, trusted writer restriction and successful API domain above. It does not establish an optimality result for all Valkey clients, writers that maintain digests, optional initial subsets, user-specific applications, SLA guarantees, or arbitrary rich observations beyond those simulated. The all-budget lower bound uses canonical executions; arbitrary rich histories retain their actual information. Source mapping, generic minimax equivalence, and finite compiler/native checks are different evidence layers and are not additive claims of independent scientific novelty.

# Bounded implementation inspection

This is author-side implementation reasoning, separate from the other helper's theorem proof audit. Target: attempt01/target_filter01.py, SHA256 fa76651995aef1a1edba06412b57236d3fa05b8097d0bfdc6eb220216a90c325. The tested code is the unmodified root snapshot.

## Information interface

The constructor parameters are future_fees, completed_q, k=0, incurred=0. Each current query takes job and body; completion also takes mode and its observed outcome. The implementation contains no graph, ready-set computation, future body/q array, supplied write budget, external service or native latency data. The caller must supply an actually ready job and its truthful fixed current cost; readiness and source/cost conformance are outside this filter. inspect() explicitly exposes author-checking internals, not a proposed scheduler observation interface.

The larger synthetic drivers possess materialized future body arrays to define their inputs, but deliver only the current scalar body to ChargedFilter. The oracle keeps dictionary state independent of the heap representation and calculates literal sorted Top_k(X), Top_k(X+[q])-p; it neither imports the theorem DP nor restates the tau/sigma query simplification.

## Update bound accounting

_up walks toward the root by replacing at with (at-1)//2, and _down replaces it with a child. Neither performs a scan over all jobs. Each walk has at most L=ceil(log2(n+1)) iterations; _up makes at most L heap comparisons and _down at most 2L, with at most L swaps per walk. Edge cases n=0 use L=1 for the conservative measured bounds.

A successful completion performs one repair for the increased entry. A boundary exchange, if necessary, performs two pops and two pushes; a cached mismatch performs one more pop and push. Thus there are at most seven repairs, three pops, and three pushes. The resulting conservative direct bounds are at most 11L heap comparisons and 7L swaps, plus a fixed amount of surrounding arithmetic/index work. The frozen executable checks allow 12L+12 comparisons and 8L+8 swaps, so the measured tests are deliberately conservative rather than fitted to observed maxima. A query uses fixed dictionary/arithmetic work and at most the two heap roots, with no heap repairs. Trace line-event limits are a supplementary executable sanity check, not a statement that one Python line is one machine instruction.

This establishes the structural O(log(n+1)) abstract update bound and O(1) abstract query bound for this source. Comparisons, additions/subtractions and array accesses are treated as abstract operations; Python integer bit complexity, allocation of integer objects, native memory management and scheduling latency are not covered. Finite stream tests can refute a claimed bound within their domain but do not alone prove asymptotics.

## Initialization and storage are separate

Construction validates the partition, allocates the arrays, builds the low max-heap bottom-up, and transfers k entries to the high min-heap. Bottom-up binary heap construction costs O(n); the k transfers cost O(k log(n+1)). Set/dictionary membership uses Python's usual expected constant-time key model. There are six n-slot persistent arrays: values, done, side, pos and two heap arrays. The heap arrays keep their capacity throughout all tested completions. The input maps and temporary constructor sets/range conversions are additional O(n) transient/input storage; six n-slot arrays is not a byte-memory estimate. Constructor tracing/comparisons/swaps are logged separately for every larger stream.

## Interface boundaries

The declared implementation domain is plain Python integers, p>0, h>=0, completed q>0, incurred>=0 and 0<=k<=|D|. The physical k condition is a domain condition, not proof that an arbitrary imported incurred value is reachable from an empty history. The suite separates all domain-valid initial states from exhaustive reachable policy prefixes. Surplus algebraic k>|D| is deliberately rejected. k=n is physically possible only when no jobs remain; the stream family reaches this by taking a mismatch on every cached completion.

Heap ordering within each side uses (value, job ID). At a tied boundary the high/low membership may be arbitrary among equal values; invariants therefore compare boundary values, not require a globally canonical ID tie order. Unconditional own-heap ordering, reciprocal handles, unique active membership, inactive -1 slots, capacities, top size and top sum are still required after every successful tested transition.

Invalid/unsafe calls have all validation before mutation in this source. The executable suite compares the entire copied object dictionary, including heap arrays, handles, done/value arrays and comparison/swap counters, before and after rejected calls. Constructor inputs and valid query state are likewise checked unchanged.

No conclusion here establishes theorem correctness, benchmark optimality, practical demand, software-runtime savings, reviewer independence, FSE merit, or submission readiness.

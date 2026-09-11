# Bounded charged-filter implementation verification

2026-09-11, author-side delegated verification; **not a blind review or theorem proof audit**. Route LOCAL. Root's filter, proof, paper and public artifact were not edited. Work stayed inside charged_general_filter_check_01. No Claude, credit, reset, paid API or human evaluation was used.

**No implementation mismatch was found in the frozen domains. All planned coverage is now complete, with the original large-stream TIMEOUT preserved.** There was one corrected verification-harness attempt covering only the two unfinished series. No target patch was needed or applied. These are author-generated semantic checks, not software workloads or latency evidence.

## Exact target and freeze

The tested file is the unmodified charged_general_01/filter01.py snapshot:

`fa76651995aef1a1edba06412b57236d3fa05b8097d0bfdc6eb220216a90c325`

Attempt01 froze the complete materialized input, protocol, reference, checker, runner and snapshots at **13:32:57 JST**, before importing/executing the target. Its FREEZE.json SHA256 is `aee4a0a90c9dc58da4bf97bb166f7cfe73bb26f71fce79117ecabd15ee2146b5`. The first family began at 13:33:06 JST. PROOF01.md and FILTER_DERIVATION01.md are the frozen specification sources; later PROOF02 and THREE_COSTS_HYPOTHESIS03 are outside this verification.

Attempt02 froze its new protocol, two unchanged input records and revised checker at **13:39:00 JST**, before executing that checker. Its FREEZE.json SHA256 is `dc850dcaa2ce53e9deffc833dd069e60ee33dea0bc32af5eef525b3d6f33776d`. The target and sorting reference hashes are unchanged. It completed at 13:39:59 JST. Frozen and predecessor hashes were all verified again during final aggregation.

## Reference and coverage

The reference stores separate future-h and completed-q dictionaries. For the current job i, it explicitly forms `X = completed_q values + other future fees`, sorts X, and computes `Top_k(X)` and `Top_k(X+[h_i+p_i])-p_i`. Viability uses a separate sort of all current entries. It does not use the draft's tau/sigma query algebra, import the theorem DP, or rerun the old 130,832 games. Future body values held by a synthetic driver are supplied to the filter only one current scalar at a time; no future p/q array, edge or write budget reaches the filter.

| Family | Fixed coverage | Result |
|---|---|---|
| Initial-state enumeration | n=0..4; every assignment of unfinished h in {0,1,3} / completed q in {1,2,4}; every k=0..\|D\|; incurred=0..sum(entries)+1 | 42,260 states; 18,977 viable, 23,283 unsafe; PASS |
| Every current-job query and mode/outcome from those states | Current p in {1,2,5}; fresh, cached match and cached mismatch, each on its own copy | 192,540 query pairs; 577,620 actions: 199,647 completed and 377,973 rejected unchanged; PASS |
| Reachable policy prefixes | n=0..3; all (h,p) in {0,1,3}×{1,2}; every next job and every allowed mode/outcome | 259 initial worlds; 20,655 prefixes, 20,396 edges, 13,341 terminal leaves; PASS |
| Named boundaries | Empty future/all, k=0, terminal k=n, zero/tied fees, unsafe states, required A path, integers through 2^1024 | 12 fixtures; PASS |
| Invalid data/actions | IDs/partition, invalid h/q/k/incurred domains, job/body/mode/outcome errors and unsafe actions | 31 invalid constructors and 52 invalid actions; all ValueError with unchanged inputs/state; PASS |
| Deterministic larger streams | 13 sizes n=1..4096, three profiles per size | 39/39 complete series; 20,478 distinct steps covered across the two attempts |

All domain-valid initial states have physical `k<=|D|`; arbitrary imported incurred values are not claimed history-reachable. Reachable-prefix tests start from an empty completed set and use all next-job orders (an edgeless readiness setting). The caller remains responsible for selecting a ready job in an actual DAG; this filter does not inspect edges. Policy-prefix counts are mutation coverage, not an additional independent safety-game theorem check.

At construction and every successful transition, the checker verifies unique active membership, heap capacities and inactive sentinels, reciprocal side/position handles, each heap's (value,ID) order, high/low boundary values, top size k, maintained sum versus sorted Top_k, done/value vectors, incurred, k and viability. Boundary ties permit arbitrary membership among equal-valued entries. Query and rejected-action checks compare the entire copied object dictionary, including all arrays, handles and counters.

## Required reachable unsafe-cache state

Start with fees `(1,1,3)` and bodies `(1,1,1)`, k=0 and incurred=0. Complete job0 by cached mismatch, then job1 by fresh. This reaches completed q=`(2,2)`, k=1, incurred=3, remaining p=1,h=3.

The independently sorted limits are cached=2 and fresh=3. Both attempted cached outcomes are rejected without mutation; fresh is permitted and terminates with incurred=4=Top_1(2,2,4). A hypothetical cached mismatch would incur 7>Top_2(2,2,4)=6. The single-completed variant is also retained as a separate named fixture.

## Preserved timeout, diagnosis and exact missing denominator

Attempt01 streams **remains TIMEOUT** at its frozen 270-second watchdog. It completed 37 series, started 38, and logged 16,972 fully checked steps. One series was partial and one was unstarted: `streams-000037` had 2,638 of its 4,096 steps, while `streams-000038` had none of its 2,048 steps. The original unexecuted denominator is therefore **3,506 steps in two unfinished series**. The receipt, traceback, raw and unexecuted denominator are unchanged.

The captured timeout stack is in the checker's recursive `copy.deepcopy(obj.__dict__)` before the next query, not a failed target assertion. The verifier additionally scans full heap/handle state and repeatedly sorts n entries at every step; those are at least linear / O(n log n) checking operations beside the target's logarithmic update. No time profiler was run and no fraction of runtime is asserted. This is an identified verification-overhead issue, not a target latency result.

Attempt02 changed only the construction of mutation-check snapshots: copy the known flat integer/boolean arrays and the two heap arrays using list copies, while retaining every dictionary field and counter. The sorting oracle, full structural checks, measured target operations, limits, policies, inputs and numerical bounds are unchanged. It executed **only the two unfinished series**, 6,144 steps in total. The 2,638 repeated prefix records are exactly equal to attempt01, including query/mode results and target operation counters. They are not counted twice. Thus `16,972 + 6,144 - 2,638 = 20,478` distinct stream steps, with **zero currently missing planned steps**. No successful earlier population was rerun.

The old TIMEOUT is not relabeled PASS. The overall coverage status is `COVERAGE_COMPLETE_WITH_PRESERVED_ATTEMPT01_TIMEOUT`. All five original family receipts and the new stream receipt are available separately.

## Abstract operation bounds and constructor cost

For `L=max(1,ceil(log2(n+1)))`, every measured completion met the pre-frozen bounds of `12L+12` heap comparisons, `8L+8` swaps, at most three pops, three pushes and seven repairs. Across complete stream coverage the observed maxima were **103 comparisons, 70 swaps and seven repairs**. Paired limits/permissions queries had zero heap comparisons, swaps or repairs and at most 32 traced target source-line events. Completion source-line events peaked at 1,097, below the frozen `256L+128` bound.

The source has a constant number of up/down heap repairs, each bounded by heap height; the separate SOURCE_INSPECTION.md explains the O(log(n+1)) abstract update / O(1) query accounting. Finite observations do not prove asymptotics by themselves. Arithmetic, comparison and array operations are abstract: Python integer bit complexity, native object management and scheduling are excluded.

Construction is charged separately as O(n+k log(n+1)), including validation, bottom-up heap construction and initial k transfers. Selected constructor records at n=4096 are:

| Initial state | Initial k | Heap comparisons | Swaps | Traced source-line events |
|---|---:|---:|---:|---:|
| Empty completed set, either reachable profile | 0 | 7,780 | 3,135 | 94,655 |
| Half completed, fresh-preferring profile | 1,024 | 37,852 | 21,966 | 400,514 |

All constructor bounds passed. The six persistent n-slot arrays occupy 24,576 slots at n=4096; temporary/input O(n) storage and integer objects are additional. This is an abstract storage count, not measured byte memory. STREAM_OPERATIONS.csv retains constructor and per-step maxima for every series. Elapsed times in receipts account for command resource limits only and support no timing-benefit claim.

## Evidence and reproduction

- `attempt01/PROTOCOL.md`, `FREEZE.json`, `inputs.jsonl`, `reference.py`, `checker.py`, `run_family.py`, target snapshots, and all five families' `*_START.json`, `*_RAW.jsonl`, `*_FAILURES.jsonl`, `*_RECEIPT.json` preserve the first attempt.
- `attempt02/PROTOCOL.md`, `FREEZE.json`, the two unchanged input records, revised checker, snapshots and stream raw/receipt preserve the justified follow-up. `prepare_attempt02.py` records the exact transformation.
- `SUMMARY_PROTOCOL.md`, `SUMMARY_FREEZE.json`, `summarize.py`, `SUMMARY.json`, `SUMMARY_RECEIPT.json` verify hashes, raw counts and overlap without executing the target again. `ENVIRONMENT.json` records the Python environment; only the standard library is needed.
- Family commands are recorded exactly in their start/finish receipts. They used `python3 -B .../run_family.py FAMILY`. The archived launcher refuses overwrites and has the original September11 13:58 JST cutoff. A later authorized reproduction must use a fresh directory/protocol with an appropriate explicit deadline; preserve these original inputs, code and raw. The sorting reference and checker are standalone reusable Python code.

There is no counterexample to minimize or target patch to request. This evidence supports the bounded implementation comparison against the stated closed form. It does not certify the theorem's quantifiers, benchmark optimality, real-use-case cost mapping, practical importance, FSE acceptance or submission readiness. No paper/public adoption was performed by this sidecar.

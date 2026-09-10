# Joint guards and the counted completion resource

Manuscript197 integrates these results in Sections4.4 and7.1. Section7.2 adds the unit-guard precedence boundary. The tight2^n-1 heterogeneous output proof remains here in the supplement. The parent scientific release f626c4c412f422b975e5c21d7251090e4a5b9fec passed all52 stages; this manuscript/guide publication adds no samples.

This extension adds three standard stages49--51. The complete prior48-stage release, corrected proof05 and fixed manuscript187 remain unchanged. The populations overlap earlier studies. These are author proofs and bounded corroborations, without mechanical proof certification, independent reproduction or a native latency claim.

## What changes

The [comparison-free proof](evidence/RESUMED_20260910_1617/guard_only_both_01/PROOF02.md) assumes independent jobs, supplied B=1 and Q<=n, with c_i=0. Both total and protected resource count each guarded-entry fee g_i. Its all-program starting point is the preceding [fully charged one-write representation](evidence/RESUMED_20260910_1617/charged_comparison_01/FULLY_CHARGED_PROOF05.md), not finite order enumeration alone.

Every cached subset has one dominating order: cached jobs first, by descending body work. Joint-cap decision is NP-complete, with a pseudopolynomial weighted-deadline DP. The deadline and profit are linked; the explicit SUBSET SUM construction establishes hardness in that restriction. Common guard prices admit a descending-work greedy decision and O(n^3) complete frontier with at most n^2+1 points. Heterogeneous prices permit exactly2^n-1 distinct frontier points, the class maximum. Protected cost alone remains Lawler-solvable on any DAG. These claims concern entry fees in BOTH coordinates; the earlier body-only-total frontier is not contradicted. The scheduling algorithms are inherited, not new general scheduling algorithms.

The [alternative call proof](evidence/RESUMED_20260910_1617/split_call_count_01/PROOF01.md) keeps the cached completion atomic, but charges its mismatch two call units. Under Q-prime<=n+r, the supplied B>r frontier is only(Omega,Omega), B=0 has(Omega,0), and0<B<=r retains the sufficient-retry body frontier. The least unaware protected-work curve is0 for B<r andOmega for B>=r. The one-budget and all-budget policy classes have different boundary cases. This is a changed resource weight, not two separately interleavable API calls, and it does not claim equivalence with any particular native call count. See the previous [native count reconstruction](CHARGED_COMPARISON.md).

## Fixed populations and full outcomes

| Stage | Fixed comparisons | Outcome |
|---|---|---|
| guard-only-joint |764 independent inputs;390,378 order/mask pairs;26,254 cap queries.836 common-guard inputs;43,565 cap queries;7,692 count-DP thresholds.55 subset-sum lists;420 targets(339 yes/81 no);26,092 masks. Eight output families n2..9;1,012 frontier points;5,116 interpreted paths. |All declared comparisons agree; seven deliberate alterations detected. |
| uniform-guard |New greedy algorithm, explicitly using the same836 input population and43,565 stored cap queries;3,780 reduced thresholds. |All values and witnesses agree; omitted-baseline control detected. |
| double-counted-mismatch |1,098 DAG/weight inputs;13,176 supplied roots.74 small inputs;222 unaware roots/curves. |All agree with the new boundary formulas;6,552 supplied frontiers differ from the original call model. |

Inputs/protocols precede their recorded runs. The new greedy study follows the earlier count-DP results and is not a held-out population. The original and revised algorithms already include a baseline threshold; its deliberate removal is a control, not a discovered defect in the old algorithm. All raw ledgers, controls, results and fixed bindings are in [guard_only_both_01](evidence/RESUMED_20260910_1617/guard_only_both_01) and [split_call_count_01](evidence/RESUMED_20260910_1617/split_call_count_01). Timings in the original receipts are checker runtimes, not kernel performance.

## Reproduction

From the repository root, assertions enabled:

```sh
python3 charged/reproduce.py verify
python3 charged/reproduce.py guard-only-joint --out replay-guard-joint
python3 charged/reproduce.py uniform-guard --out replay-uniform-guard
python3 charged/reproduce.py double-counted-mismatch --out replay-call-weight
python3 charged/reproduce.py all --out replay-all51
```

Use a new output directory for every command. Each stage copies its exact frozen checker and already-public dependencies, executes them, and compares all stable scientific output bytes and result fields. It makes no new native measurement. All51 stages preserve earlier failures and timeouts as recorded evidence; replay agreement does not turn those original outcomes favorable.

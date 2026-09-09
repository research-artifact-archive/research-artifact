# Actual all-budget compiler import: exploratory result

Three all-budget certificates were emitted by exact copies of the paper compiler, serialized, reparsed, and verified by its separate Bellman checker. Java loaded the bound208/208/215-byte profile resources and made all decisions by finite-profile queries, without a budget-sized DP. Each resource has3states and6pieces. Both Python and Java checked the constant tail at budgets10^6,10^12,10^18. Native execution did not simulate those huge budgets.

All63 native cells succeeded and passed the separate author trace checker, including the actually loaded profile byte hashes, returned rows, cycle budget, decisions and charged-cap guarantee. Five deliberately corrupted traces were rejected. Build/run took16.28seconds. Compile/check calls and profile loading were timed, but serialization/file-I/O timing is incomplete: see EXPORT_ACCOUNTING_NOTE.md. No total-runtime speedup is claimed.

| Controller | Lower than local-B rule | Equal | Higher |
|---|---:|---:|---:|
| curve_protected_tie | 2 | 19 | 0 |
| curve_fast_tie | 6 | 15 | 0 |

The local rule receives the same remainingB and selects fast iff B<=lambda. It does not load or query curves. Both compiler tie rules have the same optimal abstract guarantee. The existing compiler default chooses protection on a tie; the optional fast-tie choice matches the prior scalar-Java protocol, which was fixed before its84 outcomes.

The default compiled rule differs in realized cost from the local rule in only2of21 paired cells here. At lambda3 with up to two splitV cycles, it costs420 against432; with a fullK cycle plus a splitV cycle, it costs424 against432. Thus the stronger same-information baseline materially reduces the apparent incremental benefit compared with upstream2 or the unknown-budget threshold. This finding remains in the result.

The fast-tie rule improves6of21 cells against the same baseline. For lambda1/k_full, the default protected-tie compiler and local rule cost216, while the fast-tie compiler costs112; their certified initial cap is the same360. This shows that finite-schedule cost advantages cannot be inferred from the optimal minimax value alone, and that tie policy must be reported.

All fixtures are previously observed author-controlled inputs. This is an integration and comparator extension, not new held-out application evidence. The checkout includes the preserved MAX-key repair, whose added branch is unreachable for row keys0..30. The first84-cell packet retains its pre-repair hashes and results.

The normal-domain and synchronization limitations in ../deephaven_policy_01/DOMAIN_CORRECTION_01.md apply. In particular, these updates finish at the BEGIN hook before actual function processing; body-internal interleavings and abort-prefix traces are still outstanding. No general native minimax equality, production prevalence, or unrestricted exposed-guard result is inferred.

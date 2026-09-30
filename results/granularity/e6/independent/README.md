# Independent finite-game audit

`check_games_v3.py` is a read-only validation implementation. It constructs synchronous products, atomic transfer products, active-tester updates, simultaneous stop/start behavior, activation languages, the update-event UC blocker, and exact quiescent endpoint goals directly from JSON. It computes the strong reachability attractor in synchronous layers without a fairness assumption. It does not import a generator or invoke Java. It is not used to produce experimental measurements or replace the fixed E1 solver.

`attempt03_strict_original.json` checks 182 canonical trial certificates across 148 distinct input/merge games: Rolling v1 (100), Canary v1 (60), Policy v2 (6), DB-Rolling v2 (8), Rolling+Audit v1 (8). It also checks all Direct-Full discovered/expanded state counts, enabled buckets, and materialized outcomes against independently enumerated terminalized games. Source/input hashes and duration are in the report. All checks passed.

Every supplied WIN strategy bucket must equal its full independent Post set; every enabled UC bucket must be present; all strategy edges lower rank, and all roots must be covered. For LOSS, the stored region must contain a losing root, exclude the independent winning region, and retain an adversarial UC response or a losing response in every controllable bucket. All states' canonical, safety, goal, and initial flags are checked. The checked losing region is allowed to be smaller than the whole losing game.

The extra `minimum_worst_root_rank` is the independent finite-game optimal strong-completion bound for this abstraction. It is validation output, not a replacement for the originally reported solver certificate rank. In particular, a Lazy certificate may have a larger valid bound than this optimum.

`test_certificate_rejections_v3.py` creates twelve corrupt certificates in memory and requires rejection. All original certificates are accepted first. It never edits raw. `mutation_controls_v3.json` records rejection of missing transfer outcomes, missing UC reports, invalid root rank, false safe/goal flags, and incomplete losing certificates.

Replay the audit into a new file, preserving earlier reports:

```sh
python3 -B independent/check_games_v3.py --output independent/audit-new.json
```

Run from e6 or pass an absolute script path. Add `--families FAMILY/VERSION ...` to validate newly completed compatible JSON families. Full JSON-game coverage is capped at one million states as a validation resource limit; exceeding it is a validation limitation, not a measured solver timeout. This audit does not parse the FSP application route or prove a correspondence with an operational system. Independent endpoint products and E1 Link checks remain separate obligations.

## Preserved audit corrections

The original audit accepted some intentionally malformed certificates (goal outgoing edges, unreachable rank-domain states, and extra controlled choices) and underchecked explicit residual commutation or original-alphabet activation languages. v2 tightened strategy/domain and commutation checks; v3 additionally validates the original activation language before the merged view. All three core audit outputs remain preserved. These are validation-tool corrections: no model, raw result, E1 solver or compiled adapter changed. The measured core has no explicit residual automata, but the stricter cases are covered by rejection controls. Canonical v3 SHA-256: `f7f155357699e15aeae6657b6f02849ade82da14c6015ffa8c674ce49d15b0f8`.

These scripts were developed with AI assistance, as were the generators and adapter. Independence denotes a separately implemented semantic path without importing generator or Java transition code. It does not denote an external human audit, and agreement does not establish correctness for untested input features. See the methods-disclosure proposal in `../EVIDENCE_LEDGER_APPEND.md`.

## Explanatory adversarial response graphs

`extract_counterstrategies_v2.py` reads preserved LOSS certificates, reconstructs independent Post/strong-attractor sets, and exports a response for the environment inside the checked losing region. The six fixed illustrative cases in `counterstrategies_v2/` include Canary product/no-recovery, Policy global boundaries, DB joint/no-slack, and saturated Threads. They are postprocessing artifacts, not a new solver implementation used for experimental measurements. `certificate_states` is the original region size; `responses` counts selected UC responses plus one response for every enabled controller bucket at non-UC states; `reachable_states` counts states reached in this extracted graph from losing roots. `safe_goal_avoidance_states` counts response-reachable safe states from which no unsafe state is reachable in this particular graph. Zero does not rule out a different safe progress-failure path in the original loss region. All exported states exclude goal; absence of fairness is essential to interpreting infinite safe executions as failure to complete.

The canonical extractor is v2. Its response graphs and metrics are identical to the preserved v1 outputs; only two explanatory phrases were narrowed after `common/independent_checks/loss_quantifier_review.md`. Existential reachability of an unsafe state does not show that the controller must encounter it. The quantifier review also checks that ordinary controllables remain in Post during UC activity, that WIN covers all roots, and that LOSS need cover only one possible initial root. Six abstract quantifier fixtures passed. `counterstrategy_wording_correction.json` records graph/count equality after sorting the set-valued losing-root list; the initial comparison's ordering-only rejection is retained.

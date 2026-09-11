# Minimum-ready order can lose under the same protection guarantee

This supplement follows the stored manuscript216; it is not an additional theorem in that PDF. The independent-job least-curve policy in its Theorem3 is unchanged. General positive-retry DAGs require more care about ordering and information.

For jobs0,...,5 with distinct works(62,83,15,84,30,31), edges1->2 and3->4->5, require a single write-budget-unaware policy with Q<=9 and the optimal protected-work curve at every finite write budget. At B=7:

| Policy scope | Worst total work |
|---|---:|
| Any admitted program whose every call targets a minimum-work ready job | at least766 |
| Explicit short policy with a different guarded order | exactly752 |
| Fixed alteration allowing premature fresh completion in its special chain | exactly766 |

The [complete proof](evidence/RESUMED_20260910_1617/general_DAG_short_policy_01/PROOF01.md) supplies a seven-write adversary for arbitrary retained-record programs under the target restriction, and an eight-case analytic upper proof for the short unrestricted policy. Its cheap phase remains minimum-ready. After the third failure at job1, it cached-completes chain3,4,5 before jobs1,2; the chain's flags determine whether those later jobs can finish fresh. It preserves cached5 even when fresh5 fits the current protection cap, because that comparison can change the later resource decision.

The [fixed check](evidence/RESUMED_20260910_1617/general_DAG_short_policy_01/PROTOCOL01.md) retains all427 candidate paths and421 control paths. Both satisfy the call/protection contracts; the control loses only the total-work bound at B=7. An unchanged, separately implemented operation interpreter agrees. The short policy's whole W curve matches the previously recorded large tree, but no unrestricted all-program optimum752 or general DAG least-curve theorem is claimed.

This was adaptive development on one already-observed root. The [original fixed one-root outcome](evidence/RESUMED_20260910_1617/general_DAG_followup_01/RESULT07.json), [earlier nine equality perturbations](evidence/RESUMED_20260910_1617/general_DAG_followup_01/RESULT06.json), exploratory03--05 inputs/outcomes, original large witnesses and [earlier lower proof](evidence/RESUMED_20260910_1617/general_DAG_followup_01/PROOF08.md) remain available. The chain-first idea and the warning about premature fresh5 came from an ordinary-model technical critique of the tied predecessor; [source lineage](evidence/RESUMED_20260910_1617/general_DAG_short_policy_01/SOURCE_LINEAGE01.json) distinguishes the subsequent explicit policy and proof. Private correspondence is not redistributed. These are author AI-assisted mathematical checks, not independent certification, a new empirical population or native latency evidence.

Replay the fixed one-root07 and short-policy01 checks from the release root:

```sh
python3 -B charged/reproduce.py short-order-policy --out work/short-order-check --timeout 300
```

The output directory must be new. The stage verifies all stable scientific result/tree/path bytes and excludes only wall-clock metadata. It does not rerun the larger exploratory03--06 campaign or count its historical rows as new evaluation data. Use `all` for the complete54-stage standard replay. All prior scientific payload and unfavorable results remain unchanged.

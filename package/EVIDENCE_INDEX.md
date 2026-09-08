# Version 5 evidence map

| Claim or question | Source and retained evidence | Portable replay |
|---|---|---|
| Arbitrary prescribed serial order, exact all-budget suffixes | `fixed_order_profile_01/PROOF_DRAFT.md`; `fixed_order_profile_02` source and `semantic01` | `fixed`, `fixed_controls` |
| Shared-subtree checker soundness and generated-class complexity | `fixed_order_profile_03/PROOF_DRAFT.md`, `GENERATED_CLASS_ADDENDUM.md`, `semantic01` | `shared` |
| Construction/checking costs on 60 chains, every outcome | both `fixed_order_profile_02/scale01` and `fixed_order_profile_03/scale01`; 180 outcome rows | `scale` inspects all outcomes and 60 exact construction artifacts, checks 54 saved successes |
| Correct dispatch and semantic scope; slow valid non-generated certificates | `dispatch_integration_01` and `fixed_order_profile_03/dispatch.py` | `integration` |
| Two-job-component PARTITION reduction and exact unit gap | `paired_chain_hardness_01/PROOF_DRAFT.md`, `EXACT_VALUE_ADDENDUM.md`, source-reading receipt, all 19,786 outcomes | `paired` |
| Later checker in the same 48-input general pipeline | `sweep_pipeline_01`, including three unchanged construction timeouts | `pipeline` checks 45 saved successes, preserves all 48 statuses |
| Public application-source fit remains open | `source_fit_0812`, `source_fit_0842`, `fg_encoding_check_01` source receipts and author dispositions; assistant raw excluded | Source analysis, no runtime/application-performance claim |
| Earlier fixed evaluations, comparators and common-price studies | Preserved version-4 tree and `history/v4/EVIDENCE_INDEX.md` | Earlier four entry points |

Executable Python is under `src/`; other included material is under `data/extended/`, with explicit path-sanitized derivatives under `provenance-projections/`. Resolve repeated shared-checker inputs/artifacts with `ALIASES.json`. `MANIFEST.json` covers every physical package file except itself. SHA-256 identifies byte equality; it is not a scientific correctness proof.

The linear_slope_bound_01 extension contains PROOF_DRAFT.md, ADDENDUM.md, the source-comparison receipt and all 22,077 results with exact copied input artifacts. Use reproduce_basis.py all for the supporting-line property, tightness and integer-domain controls. These are not replacement full Bellman checks.

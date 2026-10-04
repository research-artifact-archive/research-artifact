# Evidence by question

Start with the question or figure from the paper, then open a small result table before the raw data. [Detailed outcomes and metric definitions](../docs/RESULTS.md) · [Claim-to-evidence map](../docs/CLAIMS.md) · [Paper and supplement](../paper/README.md).

## Main-paper evidence

| Paper item / question | Browse first | Deeper records |
|---|---|---|
| **RQ1, Table 3:** where does granularity change feasibility? | [55-pair index](granularity/e6/results_index.csv) | [Constructed family models, versions and certificates](granularity/e6/); [TA D / S4.1](../paper/supplementary_material.pdf#page=12) |
| **RQ1 null result:** did inherited Base/R1 contracts change decisions? | [54-comparison ablation records](ablation/) | E1 results and scripts; no decision changes. E2 is a separate construction/pruning comparison |
| **§5:** what was checked for the local serialization condition? | [Inherited-input inspection](serial-transfer-inputs/summary.csv) · [bounded finite check](serial-transfer/summary.csv) | [Current theorem and scope](../docs/CLAIMS.md#granularity-and-serialization); original alphabet-preserving tests are retained |
| **Table 2 / RQ2:** which correctness populations were checked? | [Guarantee population table](../paper/supplementary_material.pdf#page=40) | [Correctness jobs](correctness/) · [formal witnesses](formal-witnesses/) · [initializer records](initialization/) · [supplement checks](supplement-checks/) |
| **Figure 2:** how are Railcab outcomes, obligations and endpoints connected? | [Saved-activation analysis](../paper/source/evidence/railcab_saved_activation/analysis.json) | [Copied policies and inputs](../paper/source/evidence/railcab_saved_activation/inputs/) · [TA F.3](../paper/supplementary_material.pdf#page=24) |
| **PC2 saved history and active suffix:** what holds before and after each start? | [All thirteen active obligations](pc2-all-active-obligations.json) · [all 126 history rows](pc2-activation-histories.json) | [Selected active suffix](pc2-active-suffix.json) · [TA K](../paper/supplementary_material.pdf#page=33) |
| **RQ3, Table 4 / Figure 3:** what did every method return? | [All 135 saved cells](../paper/source/build/generated/rq3-cells.csv) | [Fixed/scaling analyses](performance/analysis/) · [configurations](performance/configs/) · [S4.3–S4.4](../paper/supplementary_material.pdf#page=56) |
| **RQ3 preparation:** what happens before lazy exploration? | [Preparation and closure CSV](../paper/source/build/generated/rq3-preparation.csv) | 405 completed runs, missing cells retained; [S4.3](../paper/supplementary_material.pdf#page=56) |
| **Extended budgets:** what remained unresolved? | [Condition-level ext1–5 table](../paper/source/build/generated/ext-budget.csv) | [ext1–7 raw results](performance/raw/) · [S4.6–S4.9](../paper/supplementary_material.pdf#page=76) |
| **Model sizes:** what are the 27 supplied contracts? | [Contract sizes](contract-sizes/) | [TA M](../paper/supplementary_material.pdf#page=38); input counts differ from reachable-game counts |

## Three saved-evidence analyses

These directories are the **same files included in the manuscript source ZIP**, rather than a second maintained copy.

| Analysis | Results and inputs | Scope |
|---|---|---|
| Command observation, TA F.2 | [analysis.json](../paper/source/evidence/command_observation/analysis.json) · [inputs](../paper/source/evidence/command_observation/inputs/) · [negative controls](../paper/source/evidence/command_observation/negative_controls.json) | 1,587 lookup cells, including 900 non-error cells and all 687 error cells; 357 error-to-safe reset projections are table cases, not observed starts or actual erroneous rejections |
| Railcab, TA F.3 / Figure 2 | [analysis.json](../paper/source/evidence/railcab_saved_activation/analysis.json) · [inputs](../paper/source/evidence/railcab_saved_activation/inputs/) · [negative controls](../paper/source/evidence/railcab_saved_activation/negative_controls.json) | Two saved policies; 22 supplied old-entry vectors per policy, all 21 NEW starts, one shared post graph of 70 states and 116 edges |
| Threads, TA R | [10-row summary](../paper/source/evidence/threads_saved_serialization/output/summary.csv) · [expanded policies](../paper/source/evidence/threads_saved_serialization/output/policies/) · [50 negative controls](../paper/source/evidence/threads_saved_serialization/output/negative_controls.json) · [full explanation](../paper/source/evidence/threads_saved_serialization/README.md) | Ten related identity-transfer, monitor-free backpressure cases; all entries/outcomes, ranks, endpoints and the exact n−1 additional events are checked |

Recompute all three with Python's standard library, from the repository root and into a fresh directory:

```sh
python3 -B reproduce/check_added_analyses.py --output work/added-analyses
```

These are analyses of saved objects, not new solver timings or runtime deployments. [Individual commands](../paper/source/evidence/README.txt) and [guarantee boundaries](../docs/CLAIMS.md#rq2-initialization-and-saved-policies) are available.

## Separate and historical records

- [Legacy fidelity](legacy-fidelity/) and [monolithic Industry comparison](legacy-industry/) concern a different subsequent-control objective.
- [Industry contract repair](contract-repair/) preserves the original losing contract and a separate 131-root winning variant.
- [Granularity development](granularity/) retains corrected-model predecessors, invalid inputs, restricted-transfer null results and deadline-unexecuted jobs.
- [Inventory](inventory/) and [supplementary performance](supplement-performance/) retain development context.
- [Raw archives](archives/) contain the large original records. [Restore them](../docs/REPRODUCTION.md#why-a-compatibility-workspace-exists) before running archived scripts that use the historical path layout.

WIN, LOSS, INVALID, timeout, OOM, unmeasured and skipped are distinct outcomes. Use final indexes and the paper's stated denominators; counting every historical folder would count repeated or superseded cases more than once. New runs belong in fresh `work/` directories.

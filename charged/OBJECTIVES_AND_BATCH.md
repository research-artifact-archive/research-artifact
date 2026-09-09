# Objective extensions and batch rebase

The two added portable stages recompute additive-excess and per-call-toll results, and check every saved batch-rebase native outcome. Run from the repository root with Python 3.10 or later and assertions enabled:

```sh
python3 -B charged/reproduce.py partial-objectives --out work/partial-objectives --timeout 300
python3 -B charged/reproduce.py roslyn-batch --out work/roslyn-batch --timeout 300
```

The [additive study](evidence/RESUMED_20260910_0343/partial_repair_regret_01/REPORT.md) evaluates 4,220 retained constructed geometry/cap inputs. Common completion cost cancels from additive excess. Exact ratio and additive objectives can prefer different policies; the report retains the example where an additive-optimal policy has infinite relative ratio at zero common cost.

The [per-call study](evidence/RESUMED_20260910_0343/partial_repair_call_toll_01/REPORT.md) covers 16,844 profile/cap/toll inputs, 143,226 known-budget values and 33,688 competitive rows. Its [proof](evidence/RESUMED_20260910_0343/partial_repair_call_toll_01/PROOF.md) gives a capped order-statistic curve and exact threshold compiler. With q>=2 and 0<kappa<W*, no budget-unaware policy is optimal for every budget. If kappa>=W*, accepting first is optimal for all budgets. A common mu does not change this boundary. This extension materializes O(qm) curve entries; the earlier singleton compiler's smaller memory bound is not inherited. Profiles must match the supplied footprints; the replay regenerates them independently.

The [batch rebase study](evidence/RESUMED_20260910_0343/roslyn_rebase_batch_01/REPORT.md) uses Roslyn's existing multi-document content-copy operation after the same guards as the earlier sequential rebase. Fresh native source builds passed 236 semantics cases, 23 reentry controls and 96 compiler cases. The separate 36-process arrival study retains all 1,728 batches (288 warmup, 1,440 measurement). Batch/sequential timing ratios are mixed, with no consistent improvement. Its observed protected spans exclude lock acquisition/release and are not a calibrated additive repair cost.

For an optional fresh native conformance execution, use the same pinned SDK/source acquisition instructions as [the earlier native helper](SOURCE_SEMANTICS_AND_PARTIAL_REPAIR.md), substituting `charged/roslyn_batch_native.py` and adding `--compiler-projections`. The output directory must be new and contain no shell glob metacharacters. The helper rebuilds source and runs conformance cases; it does not regenerate the arrival timing campaign. Source archive, SDK and restored package dependencies remain required. The original helper and all earlier evidence remain unchanged.

The [source/resource assessment](evidence/RESUMED_20260910_0343/SOURCE_CONTRACT_ASSESSMENT.md) distinguishes bounded native semantics, source cost-contract gaps, mathematical extensions and timing results. None certifies literature novelty, production benefit or acceptance.

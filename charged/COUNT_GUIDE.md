# Evaluation denominators

This guide clarifies the current paper's evaluation table without changing inputs, outcomes, or scientific sample counts. A zero mismatch count concerns the stated finite comparison, not a mechanically verified theorem over arbitrary programs.

| Study | Count and unit | What is compared |
|---|---|---|
| Shared frontier | 5,421 DAG/weight inputs from 75 graph shapes; 265,629 cells | 5,421 inputs x7 budgets x7 call allowances |
| Local/shared caps | 4,464 conditions; 35,796 game roots | Formula and direct game values; 8,928 known-local inner comparisons |
| Whole-kernel toll | 5,688 conditions; 42,084 game roots | The stated resource/loss bounds, not equality of every cost coordinate |
| Partial repair | 3,495 inputs; 160,080 cells | Exact dirty-set DP, damage-profile DP, and formula |
| Repair toll | 16,844 profiles; 143,226 informed values; 33,688 competitive values | Informed and competitive comparisons have separate denominators |
| Shared repair workflow | 8,960 conditions; 61,246 informed values; 6,208 existence searches | Known-budget value equations and common-policy existence are separate checks |
| Toll workflow | 37,248 conditions =31,104 two-job +6,144 three-job; 216,282 known-budget values | Value enumeration is distinct from the 37,248 threshold/existence checks |
| Informed native frontier | 9,314 records =8,800 replay +512 concurrent +2 controls | 1,024 replay groups; coordinatewise maxima and intended control outcomes |
| Unaware native frontier | 17,714 records =17,200 replay +512 concurrent +2 controls | 1,280 replay groups; coordinatewise maxima and intended control outcomes |

The two native studies each contain one live-parent mutant that must be rejected. “Expected outcomes agree” therefore does not mean every record is accepted. Different resource maxima need not occur on the same play. The informed and unaware replay groups use different budget ranges.

The Roslyn236 suite contains four modes x58 cases plus four unmodified zero-write controls. Its 2,190 queued event records are counted once, rather than again as immediate observations; the suite also has 1,253 publications and 2,653 retained snapshots. Reentry processes, compiler-projection cases, and timing samples are separate studies. The document-state guard has 96 compiler cases, 288 common snapshot comparisons and 2,552 project projections; the predecessor has 2,556 projections because its 195 warm snapshots exceed the document-state guard's 194 by one, with four project projections per snapshot (444 retained snapshots in each version). No document-guard timing experiment is implied.

## Exact saved entry points

- [Informed native summary](evidence/RESUMED_20260909_0056/charged_resource_frontier_native_01/attempt01/SUMMARY.json)
- [Unaware native summary](evidence/RESUMED_20260909_0056/charged_budget_blind_native_01/attempt01/SUMMARY.json)
- [Local/shared cap summary](evidence/RESUMED_20260910_0343/local_shared_caps_01/run01/SUMMARY.json)
- [Whole-kernel toll summary](evidence/RESUMED_20260910_0343/full_kernel_toll_01/run01/SUMMARY.json)
- [Workflow summary](evidence/RESUMED_20260910_0343/partial_repair_dag_01/run01/SUMMARY.json)
- [Toll workflow summary](evidence/RESUMED_20260910_0343/partial_repair_toll_dag_01/run02/SUMMARY.json)
- [Toll workflow threshold validation](evidence/RESUMED_20260910_0343/partial_repair_toll_dag_01/threshold_validation01/SUMMARY.json)

The complete mappings and adverse observations remain in the existing supplement guides and provenance ledger. Standard replay commands inspect archived timing observations; they do not obtain fresh timing measurements. All evaluation inputs are authored.

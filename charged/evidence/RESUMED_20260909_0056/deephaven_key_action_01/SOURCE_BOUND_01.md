## Source-derived changing Action result

The exact source has EXPAND_ALL=3 and CONTRACT=4. With directive keys implicit-root, ID0, ID1, ID2 in the retained order, fixed ID/Parent/rowset, ID0/ID2 expand-all and only ID1 toggled, complete bodies have:

| Captured ID1 Action | ExpandedSize | K_DIR | V_PARENT | V_LINK | V_UNLINK | V_NODE | V_CELL | V total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ExpandAll |31|4|4|4|0|32|64|104|
| Contract |17|4|4|4|0|17|64|89|

Contract retains ID1 and hides its14 proper descendants, avoiding15 recursive node visits including the call at ID1. No new ancestor or unlink is introduced by changing the Action alone. The exact source's KeyTableDirective has final captured action fields. V constructs fresh linked directives from the captured collection; later live key-table updates cannot mutate that successful collection. Thus the output oracle must use the successful K view, not latest Action or V payload epoch. Two-valued Action alone does not identify a unique epoch; root's oracle reconstructs the successful-body epoch from the separately recorded cycle sequence under the synchronized-notification contract.

Expected first16 IDs: ExpandAll=[0,1,3,7,15,16,8,17,18,4,9,19,20,10,21,22]; Contract=[0,1,2,5,11,23,24,12,25,26,6,13,27,28,14,29]. The common K<=4,V<=104 prefix caps persist for legal physical clock progression/current-prev mixtures because rowsets, ID/Parent, traversal branch structure and requested SingleRange do not change. Successful captured Contract allows the stronger V<=89 cap, but the preexisting common104 profile is intentionally reused for this first comparison. Sentinel payload values do not determine traversal.

Relevant original source locators: HierarchicalTableImpl.java KeyTableDirective~799, K capture/pass~1031, linking~1156 and contraction loop~1366; API HierarchicalTable.java constants123/129. Sources are fixed in the new namespace before native output.

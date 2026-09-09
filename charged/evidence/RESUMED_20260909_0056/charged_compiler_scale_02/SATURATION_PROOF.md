# Saturation leaf for charged retry values

Let P_i=p_i+delta_i, c_i=w_i+min(v_i,g_i+r_i)>0 and s_i=w_i+p_i. For a nonempty reachable unfinished set S, put A=sum(P_i), k=|S|, cmin=min(c_i). Define T(S)=0 when A=0, otherwise k-1+ceil(A/cmin); T(empty)=0. Then F(S,b)=A for every b>=T(S).

Upper bound: complete every ready job protected, accumulating exactly A. Lower bound: the abstract adversary fails every cheap/cached attempt while budget remains. If all jobs complete before the budget is exhausted, every completed job used protected or cached failure, costing P_i or delta_i+s_i=P_i+w_i>=P_i. If the budget is exhausted while an unfinished job remains, at most k-1 cached failures occurred; at least b-k+1 cheap failures each cost at least cmin. Thus the cost is at least A under the threshold. Zero-premium cases follow from nonnegativity and the protected upper bound. The argument respects any acyclic precedence relation but does not assert physical realizability of the all-failure adversary in a native application.

The saturated certificate leaf recomputes A,T from the raw input and mask. It does not replace the original requested budget. Every unsaturated peak node keeps its original formula c*(b-peak) and original child b/b-1 values. Only the binary search interval is capped at min(b,T(child)); after child saturation its forward differences are zero, so no larger peak can improve f_child(t)-c*t. The independent point checker retains both neighboring peak inequalities and validates all raw input types/DAG reachability before using any leaf.

Author-side proof review: CHARGED_PRICE_REGION_SATURATION_AUTHOR_REPORT_25.md. This theorem strengthens the comparison algorithm; it does not alter scale01 outcomes.

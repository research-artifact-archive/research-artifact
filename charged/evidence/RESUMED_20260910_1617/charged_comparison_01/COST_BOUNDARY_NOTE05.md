# A comparison-cost boundary within the same one-write embedded family

This analytic consequence follows after the fixed04 run; it is not a pre-registered prediction of that run. It changes no input or result. Keep the fully charged, supplied B=1,r=0 contract and the same works and guard charges from the final-dummy construction. Let the original jobs have arbitrary nonnegative comparison charges c_i, while the dummy retains w_z=c_z=1 and g_z=G>=max original w_i. All original g_i are nonnegative. Let base=S+Gamma.

The proof in FULLY_CHARGED_CANDIDATE04 applies unchanged: placing the dummy fresh last makes no-write costs dominate every cached mismatch, and extracting the no-write subset from any program followed by removing a cached dummy gives the matching lower bound. Consequently the entire frontier is

    nondom{(base+sum_C c_i, base-sum_C(w_i-c_i)): C subset original jobs}.

This statement does not require c_i=a_i or w_i=a_i+v_i; those are choices used by the reduction. In particular, hold every w_i,g_i and the dummy's costs fixed and set only the original c_i to zero. Caching every original job gives the unique nondominated point (base,Gamma+1). Each omitted positive-work job increases protected cost without reducing total cost. Adding the heterogeneous positive original comparison charges of the reduction produces the knapsack frontier in the SAME supplied-one-write family. Thus a c-only transition is valid for this restricted family. It does not prove that every general g-only one-write instance is polynomial.

With a common positive original comparison charge, omit jobs with w_i<=c and sort remaining profits w_i-c; each cardinality's best choice uses its largest profits, giving at most n_original+1 points. With d distinct positive original charges, the group-cardinality proof in PROOF03 applies verbatim, with at most product_v(n_v+1) candidates and polynomial construction for fixed d. The dummy is fixed fresh in the attaining policy and does not create an extra enumeration dimension. Zero-cost original jobs can all be cached, subtracting their work from the protected baseline, before grouping positive charges.

These are standard subset-selection consequences of the completion-program equivalence. They help state which added charge causes the boundary in the constructed family, without claiming a new knapsack algorithm, general strong/weak classification, measured guard prices or native performance.

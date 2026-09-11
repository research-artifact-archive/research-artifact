# Generalization candidate following the uniform-fee calculation

The uniform-fee necessity proof only needs the lost benchmark amount for t avoided mismatches to exceed the fees saved on those t fresh targets. Therefore a sufficient structural assumption is

    max_i h_i < min_i q_i, where q_i=p_i+h_i and p_i>0.

For k<=|D| use the same sorted-union cut m. On a completed target play, c targets mismatch and t=m-c are fresh. Their charged protection is at least ell+Top_m(q_S)-sum_(fresh H)h_i. The difference G_(k+m)-G_(k+c) is a sum of t weights each at least min q, whereas saved fees are at most t max h. It follows that ell>Top_k(q_D) still contradicts the bound at the capped actual write count c. For t0 the strict initial excess is enough. The weaker non-strict maxh<=minq also suffices, because ell>Top_k(D) supplies the strict contradiction. Thus it appears the correct easy-to-state sufficient assumption is maxh<=minq.

Consequently the completed-only exact filter may survive some heterogeneous fee models too. Uniform h is automatically inside this class because every p_i>0. The A/B counterpair lies outside it in A (maxh10>minq2) and inside it in B (maxh1<minq2). Do not say every nonuniform fee destroys locality.

This is an author proof extension after check01 (which tested uniform fees and fixed nonuniform fixtures), not a newly tested general empirical conclusion. A library may enforce global bounds h_i<=H<=q_i at job admission without knowing future exact weights. Future data are then unnecessary to run the guard under that contract. If no such bound is guaranteed, the two-future counterexample rules out an exact completed/current-only filter over the entire unrestricted class.

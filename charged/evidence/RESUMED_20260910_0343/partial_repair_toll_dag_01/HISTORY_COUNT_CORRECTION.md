# Correction to the proof note, after run02

The final paragraph of PROOF.md incorrectly states that every observed history's minimum consistent write count is at most E=Sigma+r max sigma_i. This E is a sufficient saturation budget for the comparator K, not a bound on every possible observation history. Example: three components with footprints {1,2,7}; the full union has sigma=1, but observing dirty mask3 takes at least two writes. Such nonsaturating observations can use more than sigma writes.

The executed run02 existence search already uses curve[min(e,ceiling)] and does not prune histories exceeding the ceiling. Thus no recorded 37,248 outcomes depend on the incorrect sentence. Its finite horizon n+r and finite observations ensure termination. Preserve the original proof and raw outcomes; interpret the affected sentence through this correction.

For a subsequent threshold certificate use the clipped information state e'=min(e+c(D),E). Since K(b)=M for every b>=E, and all continuations only increase the least-consistent count, clipping loses no comparator information. This is an explicit correction before implementing that compiler, not a claim that E bounds actual writes or every history. No native count statement changes.

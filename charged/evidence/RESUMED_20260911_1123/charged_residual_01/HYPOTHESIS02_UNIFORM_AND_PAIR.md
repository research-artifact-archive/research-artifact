# Refined candidate before new computation / Claude response

Root derivation 2026-09-11 after HYPOTHESIS01. Contrary to the earlier suspicion, a UNIFORM positive mismatch-only surcharge h may preserve the exact completed-state characterization at every physically reachable count k<=|D|. Nonuniform fees have a short reachable separating pair. Neither has yet been checked numerically or against Claude's reply.

## Uniform fee candidate

Take q_i=p_i+h, p_i>0, common h>=0, and0<=k<=|D|. The local obligation is the fixed all-cache benchmark ell+Lfuture<=Top_(k+b)(q_J) for every future b. This benchmark is not presumed the globally optimal protection curve in the charged model.

Conjecture: viability iff ell<=Top_k(q_D), with safe fresh iff ell+p_i<=Top_k(q_(D+i)); all cached actions safe. Sufficiency uses the same invariant, since fresh p_i<=q_i. For necessity choose m,H from the sorted-union identity so G_(k+m)=Top_k(q_D)+Top_m(q_S), with k+m<=|J|. The m-slot target writer spends once only at cached H targets. On its finite completed play let c be the number of such writes, t=m-c fresh H targets. The target protection is at least ell+Top_m(q_S)-h t. Cap that concrete writer at c writes; the finite completed play is preserved (even though c was not known beforehand), giving a genuinely unconditional c-write environment. The common all-budget contract requires its protection<=G_(k+c). But

    G_(k+m)-G_(k+c) = sum of t positive q weights, each >h,

so if ell>Top_k(q_D), its target protection exceeds G_(k+c). Contradiction. This uses actual realized c and its capped replay, not the weaker bound b=m. For k0 choose m0, and ell<=0 is necessary from no-write continuation.

If ell=L_body+h k (only mismatch incurs the extra fee), then Top_k(q_D)=Top_k(p_D)+h k because k<=|D|. The invariant and the fresh guard exactly reduce to the body-only predicate. Common guard fees for every completion can likewise be subtracted as a fixed whole-job baseline, if truly identical across modes and not retained. Thus not every positive fee destroys the compact result. Arbitrary k>|D| states are excluded from this necessity argument, and arise only as a different residual-credit contract.

## Nonuniform reachable separating pair

Three chain jobs0->1->2, r0. Jobs0 and1 both have (p,h,q)=(1,1,2). Job2 has q2=1000 in BOTH instances:

    A: (p2,h2,q2)=(990,10,1000)
    B: (p2,h2,q2)=(999,1,1000).

Use the same initial cached job0. A mismatch is one write, yielding D={0},k1,ell2. Job1 is ready with p1=1,q1=2. Every completed/current field is identical between instances; the difference concerns only the future job's fee split.

In A choose fresh1 then fresh2. Protected cost is2+1+990=993<=G1=1000, with no further comparison/writes required. Since G is nondecreasing this suffix satisfies every b>=0. A full universally safe policy exists: if cached0 matches, cached1; if cached1 also matches then cached2, otherwise fresh2. Its branches have protected cost0/1000 at one cached2 write, or2+990=992 at one cached1 write. Thus the shared prefix is reachable from a universally safe initial policy.

In B the proposed fresh1 leaves ell3,k1,D={0,1}. The only remaining job2 cannot be fresh (3+999=1002>G1=1000). Cached2 has a mismatch branch using one further write and costing3+1000=1003>G2=1002. Hence no continuation after fresh1 is safe. The shared prefix is nevertheless reachable under the initial all-cached policy, which obeys the fixed benchmark. This proves a future-blind maximally permissive mode filter cannot handle the whole NONUNIFORM class using only completed/current p,q,k,ell fields. It does not show that no safe conservative filter exists.

The general conservative predicate ell+p_i<=Top_k(q_(D+i)) remains sufficient and refuses fresh1 in BOTH examples. Thus its strict conservatism in A is deliberate. The pair changes the protected-work contract from the body-only benchmark to the all-cache charged benchmark; it is not a counterexample to the original body-only theorem.

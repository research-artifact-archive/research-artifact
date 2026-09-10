# Universal-curve scope: early DAG budgets and a later counterexample

Use the positive whole-kernel works, complete-program model and global charging lemma of PROOF02/INDEPENDENT_PROOF07, and the universal optimal-protection class V_r(G) of UNIVERSAL_INDEPENDENT_PROOF10. Write W_P(B)=sup over globally B-bounded environments. These are author mathematical results; the fixed36-root check is corroboration only.

## Per-play and prefix capping

For P in V_r(G), every complete finite-write play with d actual writes satisfies L<=Top_(d-r)+. An unconditionally d-capped copy of its environment preserves that complete play: induction preserves the history and each realized write through the d-th write; thereafter the original play has no further write to remove. Equivalently one may hardwire the *gate-indexed* realized trace, not merely an unordered list of writes. A finite prefix with d writes also has Lprefix<=Top_(d-r)+, because its no-more-write continuation completes by admissibility and protected work is nondecreasing. This is a constraint on programs' guarantees, not a requirement that the program observes actuald.

## Theorem: every DAG has the same early-budget optimum

For every finite DAG G and retry allowance r>=0,

    for B=0,...,r+1: inf_{P in V_r(G)} W_P(B)=Omega+B*wmax.

One fixed topological policy attains all these coordinates while belonging to V_r(G) at *every* finite budget: prepare immediately before each cheap call until r cheap failures, then prepare immediately before each cached completion. Its order need not depend onB. Each failure/mismatch needs a distinct invalidating capture-to-comparison interval. AtB<=r there is no cached mismatch and at mostB duplicate preparations, each costing at mostwmax. AtB=r+1 there are at mostr failed preparations and one cached duplicate. Q<=n+r holds on every finite-write execution, and L<=Top_(B-r)+ holds at everyB.

For the lower bound target one maximum-work job using proof10's unconditional(r+1)-bounded target adversary. Its argument does not use independence: capping at the realized count and optimal protection force exactlyr useful cheap failures and one useful cached mismatch at that target. Global charging gives Omega+(r+1)wmax. Truncating this witness after its firstB<=r writes invalidatesB distinct paid preparations of that still-unfinished target; eventual completion supplies another distinct kernel. Thus W>=Omega+B*wmax. Arbitrary retained records, prepayment after readiness, inspections, data-dependent order and wasted calls remain in the lower-bound class.

The upper policy ignores the cached Boolean. Since the lower class allows it, the same values hold under full cached-observation erasure for these early budgets. At r0 the earlier all-DAG theorem covers everyB, giving Omega+Top_B.

## Counterexample beyond the early range

Let G be the chain10->1->1, r1, B3, Omega12. Every P in V_1(G) has W_P(3)>=33. Targeting the weight10 job with two writes forces one useful cheap failure and one useful cached mismatch, for three distinct weight10 kernels, total30 and protected10. The remaining jobs cannot have been prepared before their predecessors completed. On the no-more-write continuation after those two writes, protected work must remain at mostTop_1=10. Therefore the next light job cannot complete fresh or with a stale cached record. The retry allowance is exhausted; another cheap call can be made to fail by one further own-key fresh write and would violateQ<=4 in a globally3-bounded environment. Completion therefore requires a matching cached comparison. Apply the third write at that comparison: its prepared unit and protected recomputation cost2. The last job costs at least1, so W>=30+2+1=33. Free actions cannot avoid this indefinitely because admissibility requires completion in every finite-write environment.

Conversely, the topological cheap-then-cached policy has duplicate work at most one failed preparation of10 plus at most the two largest cached mismatch works,11. Thus W<=12+10+11=33 atB3 and the value is exact. The independently sorted works(1,1,10) have F_1(3)=12+max(20,12)=32, so independence cannot be removed from proof10 at all budgets.

This same counterexample satisfies the sufficient independent saturation inequality a_(n-1)<=r*a_n/(r+n-1), namely1<=10/3. Hence independent saturation does not imply DAG-independence at later budgets. The36 fixed scope roots corroborate the early equalities and this33-versus32 witness, with every result retained. They do not establish existence of a least entire curve on every positive-r DAG.

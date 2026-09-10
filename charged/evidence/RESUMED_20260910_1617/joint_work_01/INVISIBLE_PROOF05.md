# Exact output-only frontier and a linear number of candidate partitions

This author theorem incorporates the independent symbolic feedback in AUTHOR_GODEL_INVISIBLE05 and the subsequent fixed2367-case corroboration. Neither is a blind acceptance verdict. PROOF03's explicit-Boolean contract and all earlier drafts/results remain.

## Observation contract

Take the whole-kernel model, r0, with a common start before computed records and all whole-kernel preparation/initialization charged. Fixed positive work is mandatory and outputs cannot be fabricated, even when a kernel's result is a constant object. For this weaker interface, every job's kernel returns its canonical immutable zi. Completing publication overwrites the compared live own-key identity with zi. The cached primitive's entire controller-visible transition exposes only the completed output/event, and erases comparison-dependent information: no callback-current-input reference, comparison Boolean, selected-record difference or local side effect is retained or returned. No kernel-internal execution, clock, resource counter or numeric allocation identity is observable. Old snapshots remain immutable. Free outside inspections and arbitrary causal local computation are allowed.

The complete information-erasure condition matters. Merely returning a constant result does not preclude a caller-written callback from saving the current-input reference in another local variable. Such a callback adds an observation and belongs to the stronger interface. Actual output-only native controls fix the record before the gate and keep comparison diagnostics outside the policy.

## Partition domination

For B>=1, follow an arbitrary admissible program P's no-write execution. It terminates with n completing calls. Cheap cannot occur: a single fresh write at that gate would fail and make Q=n impossible. Let F contain fresh calls and calls already stale without writes; let C contain matching cached calls. These sets partition jobs even when P prepared from stale raw snapshots. A stale call already protects wi; its extra preparation is harmless for a lower bound.

For any H subsetC with |H|<=B, write once with a fresh identity exactly at each target comparison. Define the adversary to write at most once per target and nowhere else, so its cap holds unconditionally. Before each target call every outside-inspected live value agrees with the no-write run: untouched unfinished keys have their original identities, completed keys have their canonical zi. At a target call the new identity invalidates all prior records, but completion again publishes zi and restores the same complete visible state. The erasure condition covers record selection and callback locals as well as the return. By induction, inspections, retained-snapshot comparisons, local computations and future selections are identical on this restricted family. This does not imply that P is data-independent under arbitrary environments.

Global per-job charging, from before all preparation, gives on that same restricted execution

    W(P,E_H)>=Omega+sum_(i in H)wi,
    L(P,E_H)>=sum_(i in F)wi+sum_(i in H)wi.

Choose H to be the min(B,|C|) heaviest cached jobs. A fixed partition program in any topological order, fresh on F and immediate prepare/cached on C, attains exactly

    (Omega+Top_B(C), sum_F wi+Top_B(C)).

Its mismatch intervals are disjoint, and target-gate writes attain both maxima together. Thus the Pareto frontier over arbitrary programs is exactly the nondominated union of these partition pairs, on any DAG. No arbitrary residual continuation state or common free computed record is permitted.

For B0, immediate prepare/cached gives the dominating pair(Omega,0), also achievable with cheap. ForB>=n, every partition's protected maximum isOmega and allfresh(Omega,Omega) dominates.

## Prefix simplification

Sort a1<=...<=an and let Ak=sum_(j<=k)aj, A0=0. For1<=B<n, the frontier is the nondominated subset of

    {(Omega,Omega)} union
    {(Omega+Ak-A_(k-B), Omega-A_(k-B)): k=B+1,...,n}.

Each candidate caches the k lightest jobs, regardless of their execution order; choose any topological order. For an arbitrary cached set with sorted indices c1<...<cm, ifm<=B then L=Omega and allfresh dominates. Otherwise t=c_(m-B+1), k=t+B-1. There are B cached indices at leastt, so k<=n. The prefix C'={1,...,k} has top-B sum sum_(j=0..B-1)a_(t+j), no greater than C's top-B sum, because its selected indices are componentwise no larger. Its protected-work saving is A_(t-1), at least the sum over C's m-B smaller indices, all belowt. Thus it weakly improves both W and L. This proves the finite-prefix reduction. There are at most n-B+1 candidates; W is nondecreasing and L strictly decreasing withk, so equal-W candidates retain the laterk. Sorting and linear scanning givesO(nlogn) arithmetic/comparison construction, plus choosing a topological order. No claim that the program executes jobs in weight order is made.

## The optimal-protection corner and observation price

If0<=B<n, any nonempty F gives sum_F wi+Top_B(C)>Top_B(J). When|C|<=B the left side isOmega. Otherwise it includes the B largest global jobs and at least one further positive contribution (or the B largest cached jobs already sum toTop_B and F adds positive work). Consequently allcached is necessary in the extracted partition at that cap, and the exact minimum worst W on everyDAG isOmega+Top_B. ForB>=n it isOmega. This only forces that classification in the restricted witness family; an arbitrary attaining program need not literally run allcached on all environments.

Comparing this corner to PROOF03 B for independent jobs, the value of the Boolean iswmax-w_(B+1) forB<n and0 forB>=n. AtB0 or tied relevant weights it iszero. The cost of A's simultaneous-L contract in this invisible model is instead0 forB<n andOmega forB>=n. These two comparisons must not be conflated.

The full visible-state erasure is an explicit boundary condition. With a returned Boolean, PROOF03 D branches and may exploit precedence. Without it, its binary join would improperly allow two different continuations from the same observation. The visible DP indexes achievable suffix-bound sets, not a quotient of all original histories. The emitted policy can retain its selected Pareto witness node; no claim that all optimal policies are memoryless in(S,b) alone is needed.

## Corroboration

INVISIBLE_PROTOCOL05 was fixed before the one execution. Every one of2367vector/budget cases from363positive weight vectors agreed among direct operation-path interpretation of all partitions/bad subsets, the Top partition formula and the sorted-prefix frontier. The optimal-L corners and their visible/invisible differences also agreed, with950strict-positive Boolean-value cases. The remaining cases, including ties/B0/saturation, are retained. This corroborates finite formulas and the exchange; it does not enumerate the arbitrary-program lower-bound class.

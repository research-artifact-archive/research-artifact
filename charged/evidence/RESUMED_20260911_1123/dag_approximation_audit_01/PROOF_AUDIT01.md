# Author audit: the all-program DAG lower bound, arbitrary callers, and the uniform factor

2026-09-11. Narrow SCIENTIFIC author audit. This is not blind review, a formal proof-assistant certificate, source/runtime validation or paper adoption. No new finite experiment is used. Source bytes are bound in INPUT_RECEIPT01.json and INPUT_RECEIPT02.json; the relevant manuscript is inputs01/current_main.tex, not repository-root main.tex.

**Verdict.** The existing Theorem3 lower-bound argument extends to every finite DAG under the manuscript's full interface. No analytic obstruction was found in readiness, retained/precomputed/stale records, inspections, late record selection or unconditional writer caps. The stronger HYPOTHESIS02_INTERFACE statement also follows: every caller in its explicitly restricted immediate-operation class has approximation factor alpha_r=(3r+2)/(2r+2) against the full all-budget class. The geometric family proves that coefficient is the smallest uniform coefficient for ALL callers in that class, for each fixed r>=1. It does not prove the factor is tight for the minimum-ready algorithm, which is exact on that family. These are body-work guarantees under the stipulated contract, not latency or general CPU-overhead guarantees.

## 1. The two policy classes and the quantifiers must stay separate

Fix a finite DAG J with n>=1, positive whole-kernel works w_i, Omega=sum_J w_i, M=max_J w_i, and integer r>=0. Let Top_j(J) sum the largest min(j,n) works, with Top_0=0. Sort the same multiset ascending as a_1<=...<=a_n. A completed job's output is persistent, and each job has a job-specific opaque whole kernel. We retain the exact transition interface in the frozen manuscript, including the common start before all computed initialization.

The benchmark class V_r(J) is the FULL class in current_main.tex line206: one deterministic causal program P, not receiving a write bound, must complete every job after finitely many actions and satisfy

    Q(P,E)<=n+r,
    L(P,E)<=Top_((b-r)+)(J)

for every integer b>=0 and every environment E whose writes are unconditionally <=b on every play. Programs in this class may use free inspections, finite retained record/raw-snapshot stores, copies, late selection from the existing store, and paid early preparation after readiness. Define

    W_P(B)=sup_(E in E_B) W(P,E),
    F_DAG(B)=inf_(P in V_r(J)) W_P(B).

The infimum is pointwise in B over this SAME all-budget class. It does not mean P is supplied B, and it does not assert that one program attains the infimum at every B. A policy can have infinite worst W despite terminating on each play; that only makes the lower inequality trivial for that policy. The caller constructions below ensure F_DAG(B) is finite, and mandatory work gives F_DAG(B)>=Omega>0.

The smaller caller class A_r(J) in HYPOTHESIS02_INTERFACE contains only the following calls. Use one immediate current preparation for each cheap attempt until either all jobs complete or exactly r cheap failures have occurred. Then use only fresh or immediately prepared cached completing calls permitted by the exact body residual filter. Fresh calls execute their one body directly, WITHOUT an unnecessary preceding preparation. There are no redundant preparations, extra completion calls, retained guards or partial kernels. Every chosen job is ready, and each choice is made in finite time. Choices and order may depend on arbitrary allowed observed history, but not a supplied B. Free inspections/local selection do not charge a body in this model.

Thus A_r is a subclass of the full program interface. Its work upper bound is not claimed for arbitrary P in V_r, which may perform arbitrarily much unnecessary paid work. The final quantified statement is

    forall finite J, forall r>=0, forall A in A_r(J), forall B>=0:
        W_A(B)<=alpha_r F_DAG(B).

This proves the guarantee for one fixed caller simultaneously at every B, and for every allowed caller. It uses neither a budget-specific protection policy nor an interchange of infimum and supremum.

## 2. A globally bounded target writer on any DAG

Choose an integer s with 1<=s<=min(B-r,n), so B>r, and fix a set T of the s heaviest jobs; ties may be selected arbitrarily. Define a writer E_T against an arbitrary full-interface program P as follows.

It writes only at selected cheap or cached comparison gates for unfinished jobs in T, and only if the zero-write continuation of that SAME chosen call would publish a matching record. Its write chooses a fresh own-input identity, absent from all prior target identities, records and raw snapshots. At all other gates—including inspections, preparations, nontarget calls and fresh-mode calls—it does not write. Let f count the useful cheap failures it creates, c count its useful cached mismatches, and t count ALL completed targets, including fresh and stale-cached completions. It stops writing permanently at f=r+1 or t=s.

This is causal in the declared adversary model. Job and mode are fixed before the gate. P is deterministic and the adversary knows the prior store, so it can evaluate the no-write continuation's record selection. The actual fresh-write branch can select a different retained record, but every record already in that store has an older captured identity. New preparation cannot occur inside the same comparison gate. Hence the actual branch still fails cheaply or recomputes under cached protection. The writer does not need to predict an unbounded future program execution.

At operation boundaries its actual write count is

    d=f+c,       c<=t.

Before another write the strategy is active, so f<=r and t<=s-1. Therefore

    d+1=f+c+1<=f+t+1<=r+s.

Each emitted write creates one of the counted outcomes. A cheap write increments f; a cached write increments c and t. A fresh or already-stale cached target completion increments t without a write. This proves the bound on EVERY play, including a program that violates the call cap, terminates early, loops or wastes calls. On the last allowed cheap failure f may become r+1, but the strategy stops at that point; it does not need to emit an (r+s+1)st write first. Thus E_T belongs to E_(r+s), and hence to E_B. It is not an unbounded adversary later truncated by wishful reasoning.

Readiness causes no gap. T need not be ready, an ideal, an antichain or a suffix. The writer simply remains silent while nontarget predecessors complete and while targets are not selected. P can prepare a target as soon as its predecessors complete, but a later selected comparison still has its own gate. Target completions can unlock further target jobs; all their saved predecessor outputs persist. Because E_T is already unconditionally bounded, P in V_r must eventually finish every job against it. A program that avoids a target forever with inspections, repeated stale failures or other free actions is inadmissible. No common ordering of different program histories is required, and no topological order is prescribed to P.

## 3. Why the all-budget protection contract forces all the useful events

Against E_T, a program P in V_r cannot reach f=r+1: these are r+1 genuinely noncompleting counted calls, in addition to the n completions eventually required. Every target nevertheless completes, so t=s is reached in finite time.

Before that happens, no target comparison can match. If its zero-write continuation would match, the writer invalidates it. If that continuation would already be stale, the writer stays silent and the call still fails cheaply or recomputes protectively. The only possible target completions are consequently fresh or mismatching cached, each protecting the full positive w_i. Hence on the complete realized execution

    L>=Top_s(J).

The writer's declared cap r+s does NOT by itself force f=r or exclude fresh completions. The necessary step is capping at the realized actual write count d. The frozen manuscript's capping lemma (lines208–214) applies to arbitrary histories: continue a finite prefix with no further writes, then impose a physical d-write cap on every play of that causal writer. Induction preserves the selected concrete prefix and no-write completion. The capped writer belongs to E_d, irrespective of larger off-path behavior in the original strategy. Since P belongs to the SAME all-budget class,

    Top_s(J)<=L<=Top_((d-r)+)(J),      d=f+c<=r+s.

Positive weights make Top_j(J) strictly increasing for j=0,...,n. As s<=n, this inequality requires d>=r+s. Therefore d=r+s, and the bounds f<=r and c<=t=s force

    f=r,       c=s,       t=s.

All target completions are useful cached mismatches; none is fresh or already stale. Exactly r useful target cheap failures occurred. These are consequences of the all-budget contract, not a restricted-program normal form assumed at the outset. Any extra already-stale cheap failure or nontarget failure would also exhaust the call slack once these r failures are forced. Extra protected work outside T would contradict the same equality L=Top_s(J), though that additional observation is not needed for the work lower bound.

The step fails for programs required to optimize protection only at the supplied evaluation B: the smaller realized-count contract cannot then be invoked. A policy may learn many concrete facts from inspections; no attempt is made to erase them. The actual cap lemma applies to that exact realized history, so such observations do not invalidate it.

## 4. Global charging covers retained, early and stale records

Each completed kernel invocation since the common charged start has a proof-only creator identity. Copies of its record retain that creator; their job, captured input and saved predecessor tuple cannot be retagged without a new computation. For a useful invalidation e, take the record rho_e selected by the counterfactual zero-write continuation of its chosen call. That record was in the prior store, so its creator phi(e) already executed and was charged on the ACTUAL run, even if the fresh-write branch selects another record.

For different jobs, creators are distinct. At a fixed job, the restricted writer uses never-reused fresh identities. After invalidation, no unfinished foreground action restores an earlier identity; only completion can publish a new one, and then the job is done. A later useful comparison must therefore match a later input and have a different creator. Thus phi is injective across all useful failures and mismatches, including arbitrarily many copies of old records.

For every completed job choose the invocation psi(i) furnishing its final saved output: its fresh/protected recomputation or the creator of its finally matching published record. These n mandatory invocations are distinct by job and distinct from all invalidated creators. In a useful cached mismatch its original preparation and protected recomputation are two distinct charged invocations. A preparation performed much earlier after readiness is still charged when it was made, not granted for free at a suffix boundary. A computation on an old raw snapshot is likewise paid; an already-stale failure merely consumes a call and contributes no fictitious extra creator charge.

This establishes the frozen global charging lemma directly for the target execution:

    W >= Omega
          + sum_(useful cheap failures e) w_(job(e))
          + sum_(useful cached mismatches i) w_i.

The DAG changes when a creator can be made, not its job tag, charge or uniqueness. Persistent saved parent outputs ensure that a parent need not be rerun and cannot be used as an uncharged substitute for a target kernel. Free inspections reveal live state but compute no certified whole-kernel output. This is precisely why common-start charging, opaque whole kernels, no external completion, prior-store-only late selection and fresh-identity supply are substantive premises rather than cosmetic restrictions.

Combining Section3's forced counts with this injection gives, for EVERY P in full V_r on EVERY DAG,

    W_P(B)>=Omega+r a_(n-s+1)+Top_s(J).

The witness is allowed to depend on P and s, and uses at most r+s<=B writes on every play. Taking the supremum over environments for a fixed P, then the maximum over s, and only then the infimum over P gives

    F_DAG(B)>=Omega+H_m,
    H_m=max_(1<=s<=m) {r a_(n-s+1)+Top_s(J)},
    m=min(B-r,n).

No independent-job hypothesis was used in this lower proof. Independence is needed for the theorem's matching ascending-order upper equality, not for this bound. In particular H_m>=(r+1)M (take s=1), and H_m>=Top_m(J) (take s=m and discard its nonnegative first term). For r>0 the second inequality is actually strict, but the weaker form suffices below.

## 5. Early budgets and r=0 remain exact for the full class

For B<=r, use the same single maximum-weight target witness at its declared cap r+1. Section3 forces r useful cheap failures there before its useful cached mismatch. No positive protection can have occurred at any realized count d<=r, by the actual-count capping lemma. Stop this witness immediately after the completed call containing its Bth write, and never write again. A physical B-write cap makes the new strategy unconditional, and determinism preserves that entire prefix. Those B invalidations destroyed distinct paid maximum-job preparations. Since the target remains unfinished, its eventual completion supplies a distinct mandatory invocation. Global charging yields

    W_P(B)>=Omega+B M,        0<=B<=r.

For B=0 this is just mandatory work. Although the longer witness was constructed using r+1 as an adversarial bound, P was never supplied it; the capped B-write execution is a valid member of E_B. This truncation is therefore legitimate, unlike substituting a known-B policy class.

For B=r+1 the s=1 lower is Omega+(r+1)M. When r=0 and B>0, choose s=min(B,n): the lower becomes Omega+Top_B(J). These statements cover arbitrary full programs on arbitrary DAGs.

The smaller caller class below has precisely matching upper bounds in all three cases. Consequently EVERY A in A_r is exact at B<=r and B=r+1, and EVERY A in A_0 is exact for every B. This exactness follows from the full lower and the caller upper; it does not claim that their worst-case executions are identical.

## 6. Upper bound for every immediate, filtered, adaptive caller

For one concrete execution of A in A_r, charge one mandatory body to each eventually completed job. A successful cheap or matching cached call uses its one immediate preparation; fresh completion uses its one protected body; a mismatching cached call uses a preparation and a protected body. All unsuccessful cheap preparations are additional. With no redundant preparation, this is the exact identity

    W=Omega+sum_(failed cheap calls) w_i
             +sum_(cached mismatches) w_i.                 (U1)

Cheap failures and cached mismatches each need an own-key write in that particular fresh-capture/comparison interval. The intervals are disjoint across sequential calls. Before the switch there are at most r cheap failures. If the switch occurs there are exactly r, and at most B-r subsequent cached mismatches on distinct jobs. Extra harmless writes or writes observed by inspections can only reduce this count; they are not equated with failures.

For B>r put m=min(B-r,n), T_m=Top_m(J). Equation(U1) gives

    W_A(B)<=Omega+rM+T_m.                                  (U2)

If all jobs finish before r failures, there is no cached suffix and W<=Omega+rM already. For B<=r, the switch either does not occur or (when B=r) occurs with no remaining write that could cause a cached mismatch. Therefore W_A(B)<=Omega+BM. At r=0 there are no cheap failures and W_A(B)<=Omega+Top_B(J). No fixed order or minimum-ready choice enters these counts.

The body filter proves A in V_r. At the switch all cheaply completed jobs remain in D, with k=ell=0. Its invariant ell<=Top_k(D), and its permitted completing modes, hold for every finite history and each ready choice. Each cheap failure and cached mismatch certifies a distinct write, so r+k<=B on switched plays. Thus L=ell<=Top_k(D)<=Top_((B-r)+)(J), and Q<=n+r. Before the switch L=0. The finite DAG, at most r failed calls and finite per-choice action sequences guarantee completion. This uses sufficiency of the exact local residual filter; it does not assert that arbitrary informative global histories have no additional safe choices.

Arbitrary priorities, readiness-order changes after failures, cached-outcome branching and allowed inspections therefore preserve(U2) when the caller obeys this interface. The old minimum-ready fixed-order theorem remains an inherited optimization within one subfamily. It is unnecessary for the coarse approximation guarantee, and no new minimum-ready result is claimed here.

## 7. The ratio algebra and its exact quantifiers

Assume r>=1 and B>r. By Section4 and(U2),

    W_A(B)/F_DAG(B)
       <= (Omega+rM+T_m)/(Omega+max((r+1)M,T_m)).

Let x=T_m/M and z=Omega/M. Since m>=1 and all weights are positive, z>=x>=1. The relaxed ratio is

    R(z,x)=(z+r+x)/(z+max(r+1,x)).

Its numerator exceeds its denominator by x-1 when x<=r+1, and by r when x>=r+1. Both are nonnegative. Thus for fixed x, R is nonincreasing in z, and replacing z by the smaller x is a valid UPPER relaxation. For 1<=x<=r+1,

    R(x,x)=(2x+r)/(x+r+1),
    derivative=(r+2)/(x+r+1)^2>0.

For x>=r+1,

    R(x,x)=1+r/(2x),

which is decreasing. Both branches attain their maximum at x=r+1:

    alpha_r=(3r+2)/(2r+2)=3/2-1/(2(r+1)).

For r=0 the separate exact result gives alpha_0=1 without a limiting argument. Boundary B<=r and B=r+1 values are exact by Section5. Ties do not affect any multiset sum, and B-r>=n simply saturates m at n. The proof did not assume a finite maximum-attaining environment for a general policy: pointwise execution upper bounds imply a supremum bound, while the explicit finite capped witnesses give the required lower bound for each program.

It follows that EVERY caller A in A_r has ONE simultaneous alpha_r guarantee against pointwise F_DAG(B) over full V_r. Neither the existence of a least entire curve for general DAGs nor attainment of the infimum is needed. If an empty instance is additionally admitted, set W=L=Q=F=0 and let A return immediately; the multiplicative inequality is 0<=0, while M-normalized ratios are not defined. The current manuscript already assumes n>=1.

## 8. Geometric sharpness for the uniform caller class

Fix an integer r>=1 and q=r/(r+1). On n independent jobs use DESCENDING weights w_j=q^(j-1), j=1,...,n. Then M=1 and

    Omega=(r+1)(1-q^n).

Consider the allowed caller that processes jobs descending, repeatedly attempts its current job cheaply until r global failures, then immediately prepares and caches every remaining job. All-cached is always permitted by the body filter, so this caller belongs to A_r at every write budget. At B>=r+n, r useful cheap failures at the first weight1 job followed by one useful cached mismatch at every job realize

    U=Omega+r+Omega=2Omega+r.

There are exactly r+n writes and n+r calls. A physical cap r+n and the finite fixed sequence make this an unconditional environment; it uses no supplied-budget policy decisions. Equation(U2) is also this value, so this is the caller's EXACT worst work at the selected B, not merely a lower witness.

For independent jobs the inherited Theorem3 gives the full-class optimum. For every 1<=s<=n, the sth-largest job is w_s and

    r w_s+Top_s(J)
      =r q^(s-1)+(r+1)(1-q^s)
      =(r+1)q^s+(r+1)(1-q^s)
      =r+1.

Hence its exact full V_r benchmark at B>=r+n is

    F=Omega+r+1,
    U/F=(2Omega+r)/(Omega+r+1) -> (3r+2)/(2r+2).

For every finite n the ratio is below the limit; its positive gap is

    alpha_r-U/F = (r+2)q^n / [2(r+1)(2-q^n)].

Thus for every proposed smaller coefficient beta<alpha_r, a sufficiently large FINITE n and this allowed caller violate beta. Together with Section7 this proves alpha_r is the smallest uniform coefficient for ALL finite instances and ALL callers in A_r, for each fixed r. It is a supremal sharpness statement, not a claim of a finite instance attaining equality.

If integer works are required, multiply every job by (r+1)^(n-1). The resulting exact positive integers are

    w'_j=r^(j-1)(r+1)^(n-j),
    M'=(r+1)^(n-1),
    Omega'=(r+1)^n-r^n,
    U'=2Omega'+rM',
    F'=Omega'+(r+1)M'.

Ratios are unchanged. No zero weights or rounding enter. For r=0, q=0 would not give positive weights for n>1 and is not used; exactness already proves the uniform coefficient1.

Minimum-ready chooses ASCENDING order on this independent family and attains Theorem3's exact curve. Therefore this sharpness witness does not lower-bound the approximation ratio of the minimum-ready algorithm, nor of the best caller, on DAGs. Its force is precisely the forall-caller interface guarantee. This also explains why sharpness does not imply the coarse proof's relaxed inequalities are simultaneously tight on a single equal-weight finite instance.

## 9. The old adaptive chain counterexample remains adverse evidence

The supplied RESULT_INTERPRETATION_JA.md and preserved chain6-241121-r1 policy record concern the chain (2,4,1,1,2,1), r=1. Their saved universal-policy curve is (11,15,19,21,22,22,23,24), while the two simple rules give (11,15,19,21,22,23,23,24). In particular the saved adaptive policy has W(5)=22 versus23. The old record does not establish optimality among all retained-record/inspection programs, and we do not promote it to that claim.

For explanatory arithmetic only, on this existing input at B=5, Omega=11, M=4, m=4, and Top_m=9. The inherited full-program lower's four H terms are 8,8,10,10, so it supplies F_DAG(5)>=21. The saved admissible policy supplies F_DAG(5)<=22; 22 is not asserted to be the full optimum. The coarse caller upper is24 and the actual fixed-chain caller's recorded23 is compatible with alpha_1=5/4. This is a re-interpretation of existing data plus arithmetic, not a new experiment or denominator.

The same interpretation records a reachable residual-state tradeoff in a seven-job chain. That remains a warning against claiming simultaneous optimum continuations at every state. The approximation proof above does not use such an induction, a full-program normal form, or existence of a least DAG work curve. It therefore leaves both unfavorable observations intact.

## 10. Scope boundaries and audit outcome

No obstruction to either frozen hypothesis was found WITHIN the declared interface. The proof's essential limits should accompany any adoption:

- V_r uses one all-budget optimal-L and universal-Q program. A known-B protection problem is a different benchmark. For the manuscript's independent (8,16), r=0, B=1 example, a supplied-B policy has worst W=32 while the simultaneous class requires40; substituting the former would already destroy the r=0 factor1 claim.
- Whole positive body costs, job-specific certified records, common-start charging, persistent predecessor outputs and no external completion support the creator injection. This is not a partial-kernel or native-runtime lower bound.
- A fresh identity outside every finite pre-gate record/raw-snapshot history must be available, and a later selection cannot create a newly computed matching record inside that same gate. Inspections do not make the gate disappear.
- The upper identity(U1) requires exactly the stated immediate caller discipline. A program that performs extra paid preparation can obey the protection filter while violating this upper bound. For example, even one unit job, r=B=0, can redundantly prepare twice and then cached-match, giving W=2 although the valid no-redundancy class has F=1. This is an out-of-class boundary witness, not a counterexample to HYPOTHESIS02, which explicitly excludes redundant preparation.
- The factor is sharp for all caller choices; no new fixed-order solver, minimum-ready tightness, general DAG optimality, latency improvement, source demand or submission readiness follows.

New finite experiments, retries, population exclusions, timeout trials, agents and external model calls in this assignment: zero. The analytic proof and explicit boundary witnesses are the audit result. Root alone decides whether and how to adopt it into the paper or public artifact.

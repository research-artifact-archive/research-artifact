# Extension candidate: fixed charges for both cached outcomes

Author derivation AFTER PROOF02 logical audit; not yet independently checked or paper-adopted. Motivation: a native protected comparison is often paid on both cached outcomes, whereas the preceding theorem sets match cost to zero. A translation must change all mode increments and the benchmark; it cannot erase cached-only cost while leaving body quantities unchanged.

Keep the fixed finite residual completion interface, current preparation, visible mismatch and all-write-budget quantifiers. Let fixed nonnegative protected charges be a_i for cached match, f_i for fresh, and b_i for cached mismatch. Assume b_i>=max(a_i,f_i). The all-cached benchmark is

    sum_J a_i + Top_j(q_J),  q_i=b_i-a_i>=0.

Write p_i=f_i-a_i (possibly negative), d_i=max(-p_i,0), and t_i=b_i-max(a_i,f_i)=min(q_i,b_i-f_i)>=0. At a state with completed D, future S and already incurred actual charge lambda, define ell=lambda-sum_D a_i. The normalized fresh/match/bad increments are p_i/0/q_i; ell may be negative. The residual safety requirement is equivalent to ell+normalized_future<=Top_(k+c)(q_J) on every complete abstract leaf with c mismatches.

Candidate exact threshold for normalized ell:

    V(D,k) = sum_(i in S) d_i + Top_k(q_D union t_S).       (A)

For a proposed i, set X=q_D union t_(S\{i}) and R=sum_(j in S\{i})d_j. Exact mode thresholds would be

    cached: ell <= R+Top_k(X),
    fresh:  ell <= R+Top_k(X union{q_i})-p_i.              (B)

Proof candidate. Terminal agrees with Top_k(q_J). The same completed-policy-tree argument as PROOF02 yields the same recurrence, now allowing signed p. For q>=0, min(Top_k(X+q),Top_(k+1)(X+q)-q)=Top_k(X), including q=0. If p>=0, let h=q-p=b-f>=0; the old local identity holds also at p=0 and gives Top_k(X+h), with d=0 and t=h. If p<0, the fresh threshold dominates the cached threshold because Top_k(X+q)-p>=Top_k(X). Its maximum is (-p)+Top_k(X+q), with d=-p and t=q. Hence in both cases the local maximum is d+Top_k(X+t). Adding R gives (A), independently of the ready job and thus of the DAG. Sufficiency uses actual nonnegative a,f,b and c<=actualwrites; signed normalization does not imply negative native cost.

Useful common source-shaped instance: guard cost g_i>=0, comparison cost c_i>=0, whole protected body w_i>0. Then a_i=g_i+c_i, f_i=g_i+w_i, b_i=g_i+c_i+w_i, so q_i=w_i, p_i=w_i-c_i, d_i=(c_i-w_i)_+, t_i=min(c_i,w_i). The exact candidate becomes

    lambda <= sum_D(g_i+c_i) + sum_S(c_i-w_i)_+
              + Top_k(w_D union min(c_i,w_i)_S),

against the full benchmark sum_J(g_i+c_i)+Top_(k+bwrite)(w_J). This keeps comparison and guard costs in the actual total. If every w_i>c_i, d=0 and the previous positive-p theorem applies after substitution p=w-c, h=c. Equal c smaller than each w gives a completed-only threshold, but incurred normalized ell=lambda-sum_D(g+c) generally differs from body-only protection, so the body-only predicate is not automatically unchanged.

If c>w, fresh may be cheaper than a cached match. This is a legitimate fixed-price case; it is outside filter01.py's positive-p and nonnegative-incurred API. The present implementation and old validation counts do not cover it. The condition b>=max(a,f) also excludes mode-priced systems where a mismatch is cheaper than fresh or a match; those require another analysis. History-dependent costs, waiting, partial work, retries, unequal guards retained across jobs and input-version-dependent kernel cost remain outside this fixed-charge result.

This is a proposed extension of the residual protection characterization. It neither solves the earlier supplied-one-write joint(W,L) frontier nor contradicts its NP-completeness: it fixes a particular all-cached benchmark and one scalar safety objective, and supplies no optimal-W claim. The common (w,g,c) symbols correspond to supplied prices in FULLY_CHARGED_PROOF05.md, not measured native constants. Actual cost fitting and client demand remain separate.

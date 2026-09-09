# State-local third-mode criterion and an open price region (author derivation)

Not yet independently checked. Derived from the current charged Bellman equation, not from benchmark outcomes. For b>0, ready i, write A=F(S-i,b), C=F(S-i,b-1), X=F(S,b-1), Delta=A-C>=0, H=X-C>=0, c=w+m, delta=k-m, s=w+p and P=p+delta. The three choices, after subtracting C, are:

- cached: delta+max(Delta,s)
- protected: P+Delta
- cheap: max(Delta,c+H).

Thus cached is strictly better than both alternative modes of *this job* iff

    p>0, Delta>w, and c+H>delta+max(Delta,s).

Proof: delta+max(Delta,w+p)<delta+p+Delta is equivalent to p>0 and w<Delta. Since cached cost is at least Delta, strict superiority to the cheap max can only use its c+H branch, yielding the final inequality. This is a local characterization with optimal continuation values; it is not by itself a necessary-and-sufficient condition for a global root gap against the two-mode-restricted solver (which changes continuation values).

An explicit sufficient root-gap region at B=1: two independent jobs (w,p,v,k)=(w,p,v,k),(W,P,v,k) with common m=min(v,k), delta=k-m, h=m-delta=2m-k. Assume W>=w>0, 0<p<h, and w<P+delta<w+h. One-job values at budget1 are min(p+delta,w+m) and min(P+delta,W+m). The assumptions give p+delta<m and P+delta<w+m<=W+m, so these are p+delta and P+delta. At budget0 all excesses vanish. The exact two-mode excess is

    T2=min(P+p+2delta,w+m).

The cached-small-job action has excess

    Q=delta+max(P+delta,w+p).

Both summands of this max are strictly below each two-mode alternative: Q<P+p+2delta uses p>0 and P+delta>w; Q<w+m uses P+delta<w+h and p<h. Therefore F3<=Q<T2. The larger job's cached action may lower F3 further and is not required for this strict-gap claim. This is an open region, not a single knife-edge example. Baseline common unavoidable cost W+w+2m must be added to both excesses when reporting total cost.

For common validation/callback fee v=k=kappa, delta0. Example W=2,w=1,P=2,p=1,kappa=2 gives T2=3, Q=2, baseline7, hence three-mode total9 and two-mode total10 (other cached branch=4, so exactthree9). A common protected-work price lambda1 has P=lambdaW and p=lambdaw, so the gap is possible even with one multiplier shared by both jobs. The numerical example is a derived algebraic case, not measured API input.

The interval h>0 requires k<2min(v,k) for this B=1 sufficient family; it is not claimed necessary for all jobs/budgets. Any fitted average API prices must be checked against the full fixed sensitivity grid, with negative premiums/model residuals retained. Average-time calibration does not produce a fixed-cost or worst-case timing proof.

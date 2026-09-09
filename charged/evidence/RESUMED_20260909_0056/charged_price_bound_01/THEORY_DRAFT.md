# Author-side derivation before fixed semantic falsification

Received from the mathematical helper and reconstructed by root. A separate author-side mathematical audit is pending. This is not a claim of literature priority or independent blind proof certification.

Let c_i=κ+w_i, p_i=λw_i, t_i=w_i+min(κ,p_i), and A=Σc_i. The existing independent two-fee theorem and mixed-price reduction give F2 by sorted R_{c_i,p_i} composition and F3 by sorted R_{t_i,p_i} composition. Both orders are increasing w, so the following compares unrestricted adaptive optima. When λ=0 or κ=0, the two values coincide. Assume both positive below.

For a nonnegative concave curve f with zero origin and eventual constant tail, I_s inserts one marginal s: I_s f(b)=max(f(b),s+f(b-1)) for b>0. If p<=t, the deficit formula gives

R_{t,p}f(b)-f(b)=min(p,Σ_{l<=b}(t-Δf(l))_+) >= (p-Δf(b))_+ = I_p f(b)-f(b).

For a reverse-sorted suffix whose positive marginals except possibly the last are >=c and p<=c, R_{c,p}f<=I_cf. Before that last partial marginal the fill is zero. At it, the increase is at most c-Δf(b); beyond the tail it is at most p<=c. The same argument applies to a singleton seed followed by reverse-sorted fills; each fill preserves the required invariant for the next smaller threshold. The R and I operators are pointwise monotone.

First consider light jobs L={i:p_i<κ}. They satisfy p_i<t_i and p_i<c_i. Replacing all R operators by the corresponding insertion operators gives, for any integer b>=0,

x=F2(b)<=min(P,Q_b), y=F3(b)>=T_b,

where P=Σp_i, Q_b sums the largest min(b,|L|) costs c_i and T_b the largest min(b,|L|) premiums p_i. Both sorts coincide because c_i=κ+p_i/λ. The fraction p_i/c_i increases with p_i, so the cost-weighted average fraction among the largest b items is at least the overall fraction: T_b/Q_b>=P/A_L (the b=0 inequality holds separately). Therefore

x²<=P Q_b<=A_L T_b<=A_L y.

For every baseline C>=A_L, with u=x/C, this implies

(C+x)/(C+y)<=(1+u)/(1+u²)<=(1+sqrt(2))/2.

The derivative numerator 1-2u-u² vanishes at u=sqrt(2)-1, the global maximizer for u>=0.

For the remaining heavy jobs H={i:p_i>=κ}, t_i=c_i, so their common sorted suffix is identical under the two methods. If H is empty use the light argument; if L is empty the values coincide. All positive heavy marginals except possibly the final singleton d are >=min_H c_i>max_L c_i. Every light fill leaves this prefix unchanged. A budget within it gives equal values. Otherwise remove its length from the budget coordinate and add its mass D to the common baseline C=A+D.

If the final heavy marginal d is also >=max_L c_i, remove it too. The residual problem is the light problem. Otherwise the residual seed is the singleton [d]. The preceding insertion bounds then give

x<=min(P_L+d, top_b({c_i:i∈L}∪{d})), y>=top_b({p_i:i∈L}∪{d})).

Introduce an algebraic item p_*=d, c_*=κ+d/λ. It is not a newly executed job. We have c_*>=d: immediate if λ<=1; for λ>1 use d<max_L c_i<κ(1+1/λ), so κ-d(1-1/λ)>0. Replacing the upper-bound entry d by c_* can only enlarge that bound and restores the common affine relation for every item. Consequently x²<=(A_L+c_*)y. Also d<=P_H, so A_H=|H|κ+P_H/λ>=κ+d/λ=c_*. The actual C=A+D is large enough for the same ratio inequality. Arbitrarily large heavy premiums are covered, without assuming p_i<=c_i for them.

Tightness: for integers M→∞, take κ=M, each w=1, λ=floor((sqrt(2)-1)M), n=M² and B=ceil(nλ/(M+1)). The equal-threshold packing profiles are min(nλ,b(M+1)) and min(nλ,b(λ+1)). Thus F2(B)=nλ, F2/A→α=sqrt(2)-1 and F3/A→α². The total-cost ratio approaches (1+sqrt(2))/2. Relative to the two-mode optimum, the maximal reduction is 1-2/(1+sqrt(2))=3-2sqrt(2), approximately17.16%.

The scope is common fees and a common proportional premium with independent jobs. Compatible DAGs inherit the same values when both sorted orders are legal; arbitrary dependencies or arbitrary heterogeneous price relations are not covered by this argument. This bound gives a best-possible declared-resource benefit in that class, not evidence that any real API attains its price conditions.

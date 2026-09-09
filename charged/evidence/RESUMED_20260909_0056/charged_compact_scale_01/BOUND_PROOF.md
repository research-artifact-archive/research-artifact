# Elementary input bounds for the charged model

Use effective c_i=w_i+min(v_i,g_i+r_i)>0 and P_i=p_i+delta_i, delta_i=g_i+r_i-min(v_i,g_i+r_i). For every reachable unfinished S and b>=0:

L(S,b)=max_{integer b_i>=0,sum b_i<=b} sum_i min(P_i,b_i*c_i) <= F(S,b)

and F(S,b) <= U(S,b)=min_{t in {0} union {c_i:i in S}} (sum_{c_i>t} P_i+b*t).

Lower bound: give each job its private adversarial failure budget b_i. Fail cheap/cached when that private budget remains; otherwise allow success. No more than b total failures occur. A job completed protected or by a cached failure incurs P_i or P_i+w_i, at least min(P_i,b_i*c_i). Any job completed cheaply or by cached success after consuming its private budget must first have suffered b_i cheap failures, also at least that amount. For b_i=0 the lower bound is0. Sum over jobs; arbitrary precedence does not invalidate this adversary.

The increments of min(P_i,c_i*b_i) are floor(P_i/c_i) copies of c_i followed by P_i mod c_i if nonzero. They are nonincreasing. Merge these compressed runs in descending increment order and take the first b units. This solves the separable concave allocation exactly with no loop up to b or numeric price magnitude.

Upper bound: for a chosen t, use protected on jobs with c_i>t and cheap on all others in any available topological order. Every failure costs at most t; protected jobs contribute the displayed premiums. t=0 is all-protected. Hence equality L=U certifies a value without visiting child states. In particular, F(S,b)=sum P_i once b>=T_alloc(S)=sum ceil(P_i/c_i). The zero-total and empty cases have threshold0. This strengthens the earlier uniform-cmin saturation bound.

PEAK may cap its child-peak search at min(b,T_alloc(child)); it keeps the original query b and the original Bellman expression and right-neighbor check. The point checker recomputes L and U from raw prices in a separate implementation with no bounds/solver import. The proof remains conditional on the charged abstract game; it does not turn an abstract adversary into a native witness.

Author analytical audit: CHARGED_PRICE_AND_SATURATED_CHECKER_AUTHOR_REPORT_27.md. Do not transplant the older zero-fee ordered/packed exact-value rules: cached prices are not determined by(c_i,P_i) alone.

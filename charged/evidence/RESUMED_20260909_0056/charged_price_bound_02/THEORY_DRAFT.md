# Proposed sharp bound for all independent charged jobs

Let c_i=w_i+min(v_i,k_i)>0, delta_i=k_i-min(v_i,k_i), P_i=p_i+delta_i, and A=Σc_i. X=F2(B) is the independent protected/cheap optimum; Y=F3(B) additionally permits cached completion. The earlier private-budget lower bound gives D(B)=max_{Σb_i<=B}Σmin(P_i,b_i c_i)<=Y: protected completion costs P_i excess, mismatching cached completion costs P_i+w_i>=P_i, and otherwise an allocated budget exhausted in cheap failures has paid b_i c_i. This argument does not require delta_i=0. The two-mode subsystem is always exactly a two-fee game(P_i,c_i).

Pack the two-mode premiums in reverse nondecreasing-c order. Label each portion of a marginal column by its contributing job. Every final column containing job i's mass has height h<=c_i: the first contribution is limited by c_i, and later contributions have no greater threshold. A partial final column can be raised only toward a later, lower threshold. Let x_i be i's mass in the first B unit columns. Then Σx_i=X,0<=x_i<=P_i, and Σx_i/c_i<=B, since each selected column satisfiesΣ a_i/c_i<=Σ a_i/h=1.

Let φ_i(z) linearly interpolate the integer samples min(P_i,b c_i). Its unit-width marginal slopes are nonincreasing. MaximizingΣφ_i(z_i) subject to z_i>=0 andΣz_i<=B has an integral optimum for integer B: choose the B largest unit marginal segments, preserving each tied prefix. Thus this optimum equals D(B). The feasible z_i=x_i/c_i=m_i+r_i,0<=r_i<1, satisfies P_i/c_i>=z_i. Its first m_i segments have slope c_i and its next has slope at least r_i c_i, so φ_i(z_i)>=c_i(m_i+r_i²).

Put α=sqrt(2)-1. For every integer m>=0 and0<=r<1,

m+r²−2α(m+r)+α²=m(1−2α)+(r−α)²>=0.

It follows that Y>=D>=2αX−α²A. Since1−α²=2α, A+Y>=2α(A+X), giving

(A+F2)/(A+F3)<=(1+sqrt(2))/2.

The common-price family from study01, w=1,k=v=M,p=floor(αM),n=M²,B=ceil(np/(M+1)), already proves sharpness in this broader class. The supremum of the reduction relative to the two-mode total is3−2sqrt(2). The proof relies on independent two-mode sorted packing. It does not assert the same ratio for arbitrary dependency DAGs, and does not need a compact three-mode reduction or a shared order between the two methods. It is a declared-resource approximation statement, not an empirical prevalence or latency theorem. The source of the packing/allocation proof is the author mathematical helper; root proposed removing the unnecessary delta=0 hypothesis. Separate mathematical audit is pending.

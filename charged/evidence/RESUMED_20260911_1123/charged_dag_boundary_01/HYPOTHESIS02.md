# Post-stage01 algebraic candidate: for author inspection only

Stage01 returned0 DAG/value/action differences in13104 games. This is a finite result only. The following was derived AFTER that result and BEFORE stage02/03; it is not preregistered stage01 content. The assigned scope explicitly forbids promoting a no-witness search to a general DAG-independence theorem. Accordingly this is an unadopted proof candidate for root inspection, not a manuscript theorem or claimed general result of this task.

Candidate expression: with multiset A(D)=q_D union h_(J\D), perhaps V(D,k)=Top_k(A(D)). This specializes to C for common fees because k<=|D| and every completed q exceeds the common h. It also specializes to C under the pointwise fee condition h_future<=tau, without asserting this condition is invariant after bad outcomes. This candidate permits dependence on future h but not future precedence.

Local algebra to inspect separately from finite results: let X be any finite multiset of nonnegative values, q=p+h with p>0,h>=0. Write B_k=Top_k(X union{q}), C_k=Top_k(X). The identity proposed is

    max(B_k-p, min(B_k,B_(k+1)-q)) = Top_k(X union{h}). (A)

For k=0, B0=0, B1>=q, so LHS0=RHS. For1<=k<=|X|, let tau be the kth largest X element. If q<=tau, B_k=C_k and B_(k+1)-q>=C_k; cached branch is C_k, fresh is smaller, and h<q<=tau makes RHS C_k. If q>tau, B_k=C_k+q-tau while B_(k+1)-q=C_k; LHS=C_k+max(0,h-tau), equal to RHS. If k>|X|, B_k=B_(k+1)=sum(X)+q, so LHS=sum(X)+h=RHS. Ties are included.

Proposed backward-induction step: for a ready i, use X=q_D union h_(S\{i}). If the proposed expression applies to BOTH child thresholds at k and k+1, their common multiset is X union{q_i}. Applying(A) yields Top_k(X union{h_i})=Top_k(q_D union h_S) for each ready i separately. Terminal S empty matches G_k. The dependency readiness constraints do not appear in(A). This is a candidate full induction, not an inference from zero differences; semantic exactness and quantifiers still require explicit review. The current task will not elevate it to a general theorem.

Potential derived action formulas, also unadopted: cached threshold Top_k(q_D union h_(S\{i})); fresh threshold Top_k(q_D union{q_i} union h_(S\{i}))-p_i. Thus arbitrary-fee viable states outside C need not permit every cached action. This does not contradict the established result that cached is safe from C. No global work-optimality, benchmark optimality, online unknown-future guarantee or native client effect is inferred.

The independent checker must avoid this formula and the backward-threshold recurrence. It will enumerate entire causal policy trees and their leaves and compute the minimum of G_(k+c)-futurecost over ALL leaves. This explicitly keeps the same tree across all write budgets. A violating leaf is realizable by a writer that follows its cached outcomes with one fresh-identity write per bad gate, stops writing after c, and never exceeds c on any play. Extra harmless writes cannot tighten a nondecreasing Top benchmark. Root may review(A), the induction, and this abstraction/quantifier link independently; this file itself does not authorize paper adoption.

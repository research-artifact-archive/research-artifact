# Exact charged residual safety on every finite DAG

Author proof, 2026-09-11 13:20 JST. SCIENTIFIC. This is a new derivation after charged_dag_boundary_01/HYPOTHESIS02.md, not a reinterpretation of its finite searches as a proof. The fixed219 paper and its Reject review remain unchanged. The following generalizes charged_residual_01/PROOF03.md within the same residual action class.

## Definitions and claimed result

Fix a finite DAG J, a completed ideal D and S=J\D. Job i has fixed p_i>0, h_i>=0 and q_i=p_i+h_i. Each remaining job completes once: fresh incurs p_i; immediate-current-preparation cached incurs 0 on match and q_i on mismatch. The scheduler chooses a ready job and a mode in finite time. No further cheap calls, early preparation, partial work, retained guards or fixed comparison fees are introduced. Calls are sequential. Every cached mismatch requires an own-key write in its disjoint current-capture/comparison interval, and one fresh-identity write realizes any chosen mismatch. The fixed costs do not change with the chosen identity. Waiting and other native costs are outside these quantities.

Let Top_k(A) be the sum of the largest min(k,|A|) multiset entries, with Top_0=0. Let G_j=Top_j(q_J). A residual state carries integer k>=0 and incurred cost ell>=0. Operationally 0<=k<=|D| counts cached mismatches; the algebra below also holds for surplus k, without interpreting it as actual writes.

Safety means that ONE completing policy, supplied no future write bound, satisfies ell+L_future<=G_(k+b) for EVERY b>=0 and EVERY environment whose writes are unconditionally bounded by b on all its plays. This is a residual interface contract, not a claim that k equals total past writes or that an informative global history has no weaker obligation.

Define A(D)=q_D union h_S. The exact viability threshold is

    V(D,k) = Top_k(A(D)).                                  (1)

For each ready i, put X_i=q_D union h_(S\{i}). Its exact mode permissions are

    cached i: ell <= Top_k(X_i);                           (2)
    fresh i:  ell+p_i <= Top_k(X_i union{q_i}).             (3)

From a viable state at least one of these modes is safe for EACH ready i. Thus every readiness order has a safe mode selection; future edges and future p/q values do not enter (1)--(3), although future h values do. This is not a work-optimality or latency theorem.

## All-write-budget quantifiers and a finite completion game

The following argument establishes the recurrence rather than assuming a DP comparison establishes the model. Consider a fixed causal deterministic policy. It makes exactly |S| completion calls, with finite intervening choices. Restrict writers to choosing no write at a fresh call and, at each cached call, either no write (match) or one own-key fresh-identity write (mismatch). Fix any admissible fresh-identity selection rule, so policies that inspect the actual values also induce a finite binary branching completion tree under these writers. The policy receives no b. A leaf with c mismatches and future cost t can be realized using exactly c writes. After deriving that finite play, define a writer that follows its selected writes, stops on any history departure, and suppresses writes after c. This writer has an unconditional c-write cap and reproduces that play against the fixed policy. Thus safety requires ell+t<=G_(k+c) at every such leaf.

For an upper bound it suffices to construct a policy using only the abstract outcomes. Any actual execution then corresponds to a leaf with c mismatches. Because mismatch intervals are disjoint, c<=b for any b-write environment, including extra harmless writes. A leaf inequality at k+c therefore implies the required inequality at k+b by monotonicity of G. This does not identify all writes with mismatches.

These observations justify backward induction over remaining jobs. At a terminal state safety is exactly ell<=G_k. At a fresh i, the successor incurs p_i and retains k; hence its threshold is V(D+i,k)-p_i. At a cached i, both match and mismatch continuations must be safe, with thresholds V(D+i,k) and V(D+i,k+1)-q_i. The continuations may differ by the observed outcome but each is itself one policy valid for all remaining write bounds. Consequently

    V(D,k) = max_ready_i max(V(D+i,k)-p_i,
                         min(V(D+i,k),V(D+i,k+1)-q_i)).    (4)

For necessity, this induction can be strengthened to arbitrary admissible prefix histories with the same numerical state: if ell exceeds the threshold, the policy's selected action has at least one child above that child's threshold. Select it and continue the induction. Fresh identities still exist after every such history. A terminal violating play yields the capped writer above. No merging of two histories or supplied-budget policies is used. For sufficiency, pick a threshold-preserving action and continue; every step finishes a job, and all abstract leaves satisfy their terminal bound. Maxima are attained since each ready set is finite. An arbitrary scheduler may choose the next ready i because the algebra below makes each ready i's maximum identical.

## The local algebra, including ties and saturation

Let X be any finite multiset of nonnegative entries, C_k=Top_k(X), B_k=Top_k(X union{q}), and q=p+h, p>0,h>=0. First,

    min(B_k,B_(k+1)-q) = C_k.                             (5)

For k=0 the first argument is 0 and the second is nonnegative. For 1<=k<=|X| let tau be the kth largest entry. If q<=tau, B_k=C_k and B_(k+1)>=C_k+q. If q>tau, B_(k+1)=C_k+q and B_k=C_k+q-tau. Both cases establish (5), including ties. If k>|X|, B_k=B_(k+1)=sum(X)+q and (5) again holds.

For 1<=k<=|X|, B_k=C_k+max(0,q-tau); hence

    max(B_k-p,C_k)
      = C_k+max(0,max(0,q-tau)-p)
      = C_k+max(0,h-tau)
      = Top_k(X union{h}).                               (6)

The middle equality uses p>0 and q=p+h. For k=0 both sides of (6) are 0. For k>|X| the left side is max(sum(X)+h,sum(X))=sum(X)+h, which is the right side. This is an exact identity over nonnegative real costs, not an integer-grid assertion.

## Backward solution and exact permissions

When S is empty, (1) is G_k. Assuming (1) at all states with fewer remaining jobs, both children for ready i have multiset X_i union{q_i}; their k and k+1 thresholds are B_k and B_(k+1). Equations (5)--(6) turn the cached threshold into Top_k(X_i) and the maximum over its two modes into Top_k(X_i union{h_i})=Top_k(q_D union h_S), independently of i. This proves (1)--(3) by induction for every finite DAG and every k>=0.

## Relation to the completed-only region and previous boundaries

All-cached completion still has exact threshold C=Top_k(q_D) for physical k<=|D|, as proved by the old sorted-union lemma. It is generally smaller than V. For k=0 both are 0. For 1<=k<=|D| let tau_D be the kth largest completed q. Then

    V=C iff every future h_i<=tau_D.                      (7)

Indeed a future h above tau_D strictly improves the top-k sum; if none is above, completed entries already attain it. Equality at one state need not be invariant after a mismatch. The previously saved noninvariance example remains valid. Nor does (7) say every current fresh decision differs whenever V>C.

The global admission contract max_J h<=min_J q implies (7) at every physical state with k>0. A common fee h satisfies it because p>0 gives every completed q>h. Thus the prior completed-only filter remains exact in its declared domain. For h=0, (1) reduces to the body-only theorem. Under arbitrary fees, the old A/B example retains its conclusion: future fee information can change current permissions even with full q_J and the DAG identical. The stronger result now identifies sufficient future information: the future fee multiset, together with completed q and the proposed job's p/h, is enough; no future body-cost split or edge enters safety.

## Operational interpretation and nonclaims

The quantity h is a mismatch-specific premium avoided by choosing fresh, not a fee charged by every call. Future premiums can support viable states outside C because future fresh choices can avoid them. In such states cached may be forbidden even though the current state is viable. With D having q=2, k=1, ell=3 and a single future job p=1,h=3,q=4, V=3: fresh finishes at 4=G1 while a cached mismatch finishes at7>G2=6. This state is reached in the established world A after cached0 bad then fresh1. Thus an implementation that permits every cached action throughout V would be wrong.

This solves a protection safety game for one all-budget benchmark. The benchmark is the charged all-cached curve, not proven charged-optimal. It does not determine worst total work, best ready order, retry-phase control, meaningful native h values, practical demand, FSE acceptance, or submission readiness. Generic top sums and backward safety reasoning are inherited. The mathematical gain over219 is an exact closed form for unrestricted mismatch premiums and every DAG, replacing a sufficient admission condition plus an impossibility pair with a complete residual characterization.

## Validation boundary

The proof above stands on its algebra and capped-writer argument. Earlier 130,832 finite games and a separate 12,288-case complete-policy enumeration corroborate the proposed expression in their fixed ranges; they are not its general proof and are not additional independent workload samples. Root proof review, implementation, additional checks, paper adoption and public reproduction must each be recorded separately. No prior hypothesis, raw result, adverse finding or frozen219 byte is changed here.

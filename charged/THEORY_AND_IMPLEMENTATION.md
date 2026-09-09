# From charged calls to a checked policy

The paper's normal form concerns a finite DAG of pure, opaque, whole kernels. Preparations use each job's own input identity and captured immutable predecessor outputs; completion persists. There is no retained guard, free completion by external work, cross-job callback work, or free proof that all future writers have finished. Noncompletion costs infinity. The allowance and charges are supplied.

At an unprepared boundary the three modes are fresh protection, cheapest validation retry, and cached atomic completion. With `m=min(v,k)`, use `c=w+m`, `delta=k-m`, `P=p+delta`, and `s=w+p`. The excess Bellman choices for job `i` are:

1. `P_i + F(S-i,b)`;
2. `max(F(S-i,b), c_i + F(S,b-1))`;
3. `delta_i + max(F(S-i,b), s_i + F(S-i,b-1))`.

At budget zero, omit mismatch branches. The paper's action-wise potential proves a lower bound even for programs retaining preparations and switching jobs. The serial choices attain it. A separate actual-write theorem assumes one foreground thread, distinct persistent keys, immutable identity-equal wrappers, fresh never-reused write identities, terminating Java calls, and no other-key/other-job work in callbacks. Rejection of an already stale preparation costs no additional adversarial write. Captured parents remain valid when their live entries change.

## General all-budget artifact

`charged_curves_02` composes discrete concave curves without enumerating the budget magnitude. Marginal insertion must use integer contacts. Supporting slopes are contained in `{0} union {c_i,s_i}`, with at most `2|S|+1` lines and `4|S|` positive runs. General construction/checking takes `2^n poly(L)` bit time, retaining the unfinished-set dimension. NP-completeness at one failure does not prove this enumeration necessary, nor membership in NP for arbitrary binary budgets.

The independent curve checker reconstructs the whole reachable domain, prices, baseline, readiness and routing fields. It verifies Bellman equality at affine endpoints/crossing neighbors and constant tails. The statement certifies game values and the mathematical argmin, with parsing, arithmetic, selector implementation and operational abstraction separately trusted or tested. It is not executable-code verification.

## Compatible mixed-price artifact

If each job has `p_i*delta_i=0`, set `t_i=min(c_i,s_i)` when `delta_i=0`, otherwise `t_i=c_i`. Two-fee jobs `(t_i,P_i)` admit a fixed increasing-`t` optimum. In reverse order, packing raises only the final partial marginal, then appends a counted `t_i` plateau and at most one remainder. At most two positive runs per job suffice; counted lengths are binary integers.

The proof connects this two-fee result to the original charged choices. Marginal insertion commutes with preceding deficit fills when its slope is at least their thresholds, for arbitrary nonnegative premiums. On sorted suffixes the charged operator equals the reduced operator; the same commutation supplies a lower bound for cached choices in arbitrary adaptive policies. Removing edges gives a lower bound, and a sorted topological policy attains it when each edge satisfies `t_u<=t_v`. These arguments, not an empirical solver match, establish global optimality.

Store one root curve `H`, its sorted job order and suffix premium sums `Z_k`; the suffix value is `min(H(b),Z_k)`. Its total cost uses the original suffix sum of `c_i`, not the sum of effective `t_i`. The artifact covers its own `n+1` cursor suffixes. It does not pretend to contain every reachable unfinished subset.

The cap checker first validates the zero origin, positive integer run counts, decreasing positive marginal heights, implicit zero tail and total premium mass. It reconstructs input conditions, original prices/baseline and order, and checks adjacent-cap Bellman equations at their uncapped, crossing and saturated portions. Zero premiums require identical adjacent caps. Concavity then extends the finite checks to every integer budget. A supplied `r`-run encoding costs `O(|E|+n log(r+2)+r)` arithmetic work plus reading its encoding; generated roots have `r<=2n`. Construction is `O(|E|+n log(n+1))`; operand bit lengths still count.

The runtime evaluates all three original choices for the fixed next job. Its protection/cheap/cached tie rule can differ from the general compiler's order and from earlier Java fixtures while preserving the minimax value. This is why the compact Java path outcomes were regenerated and checked against an explicit original-price, fixed-order oracle.

## What the sufficient conditions do not say

With independent work `(1,1,1,2)`, premiums equal to work, and common `v=5,k=6`, ascending work order costs 31 at budget 1, while another order and the adaptive optimum cost 30. Earlier finite common-price probes did not contain this case; their agreement remains recorded. Sorting by original `c` can also fail inside the zero-delta class when effective `t` has a different order. Both counterexamples are retained.

The source implementation of two-fee packing is inherited from the preceding zero-fee research; the charged reduction, preserved baseline and original-mode cursor execution are the new connection. General reflected recurrences, budgeted DP, concave marginal operations, input-slope envelopes and composition ordering are established techniques attributed in the paper. No application prevalence or measured latency theorem follows from this reduction.

# Charged atomic calls: author proof draft

This is a new, narrower primitive claim, not a proof of the full exposed-guard conjecture. The held-guard counterexamples in charged_guard_holding_01 remain obligations. No claim of practical prevalence, elapsed-time optimality, or novelty is made by this draft.

## Interface and prices

Jobs form a finite DAG. An unfinished job has state U (no usable current preparation) or C (a usable current preparation); D is permanently completed. A kernel may run only after all its parents have completed and captures their exact completed outputs. Completions remain valid despite later input changes. Kernels are opaque, whole, and have unguarded price w_i>0 and protected price w_i+p_i, p_i>=0. An identity-conditional call costs v_i>=0. Atomic callback entry/exit together cost k_i=g_i+r_i>=0; no guard survives a call. These are declared resource charges, not measured execution times.

The counted calls are: U->C preparation, price w_i; U->D fresh atomic completion, price k_i+w_i+p_i; C->D match or C->U invalidation by an identity-conditional call, both price v_i; C->D match or C->U invalidation by an atomic validation-only callback, both price k_i; and a cached atomic completion, which on a match costs k_i and on an invalidation costs k_i+w_i+p_i, completing in either case. An invalidation consumes one budget unit. At zero budget only match branches are available. Discarding a preparation is free. Free inspection is allowed only when the environment can preserve the current capability through a match outcome. Calls finish, have no cross-job foreground work, and return exact successful outputs. All noncompleting programs have infinite objective.

Atomic validation-only callbacks are part of this stated interface. They can retain the current map entry on an identity mismatch and report failure without exposing a monitor. No bare acquire, release, or guard-retaining action is included. Multiple jobs may retain preparations and the program may change jobs after any completed call.

Set m_i=min(v_i,k_i), c_i=w_i+m_i, delta_i=k_i-m_i, P_i=p_i+delta_i, s_i=w_i+p_i. The three-mode residual recurrence is F(empty,b)=0, F(S,0)=0 and, for b>0, the minimum over available i of

* protected: P_i+F(S-i,b);
* cheap validation: max(F(S-i,b),c_i+F(S,b-1));
* cached completion: delta_i+max(F(S-i,b),s_i+F(S-i,b-1)).

At b=0 the cached option is delta_i+F(S-i,0). A cheapest validation attempt consists of unguarded preparation followed by the cheaper of the identity-conditional call and atomic validation-only callback. A failed attempt starts over from U.

## Equality at the all-unprepared boundary

Claim: the minimum worst counted resource cost over all causal programs of this interface is sum_i c_i+F(J,B), attained by a serial three-mode controller.

The upper bound executes the three stated modes; their full success/failure costs give the recurrence after subtracting the per-unfinished-job baseline c_i. Every failure removes a budget unit and every success removes a job, so the chosen controller terminates.

For the lower bound let T be the unfinished set and define

Phi(x,b) = sum_{i:x_i=U} c_i + sum_{i:x_i=C} m_i + F(T,b).

All cached jobs are physically ready, hence available in T. Select a legal outcome of each observed call so that its price plus successor potential is at least Phi. Terms of unchanged jobs cancel:

1. Preparation replaces c_i by m_i and pays w_i=c_i-m_i exactly.
2. A validation call of price z_i in {v_i,k_i} has success excess z_i-m_i+F(T-i,b) and failure excess w_i+z_i+F(T,b-1). Since z_i>=m_i, these dominate respectively F(T-i,b) and c_i+F(T,b-1), whose maximum is the feasible cheap-validation bound on F(T,b). At b=0, success suffices.
3. Fresh atomic completion pays c_i+P_i and removes i, so the protected recurrence option gives the required inequality.
4. Cached atomic completion has, after canceling the old cached credit m_i, success excess delta_i+F(T-i,b) and failure excess delta_i+s_i+F(T-i,b-1). Their maximum is exactly its recurrence option. At b=0 only success is needed.
5. Discarding C increases its baseline by w_i; a preserving free inspection does not change the potential.

Choose Nature's branch after seeing the program action, respecting the remaining budget. Telescoping to completion yields the all-U initial potential; noncompletion already has infinite cost. The potential need not equal the optimum at intermediate states. This proof covers arbitrary job switching and simultaneous retained preparations, with no assertion about exposed or retained guards.

## Actual-write interpretation: obligations before adoption

The earlier Java callback theorem uses immutable fresh identity wrappers, persistent keys, one foreground, captured parents, no other-key work within callbacks, no guard surviving a call, and at most B successful external writes. Under those same assumptions the lower-bound adversary writes a fresh identity just before a selected validation/completion acquires its monitor. A validation-only callback must leave a mismatched current entry unchanged and report failure; on a match it publishes its prepared result. Its match/mismatch cases are the two charged validation branches above. The emitted controller rereads and recomputes after every failure, so its serial read-to-validation intervals inject failures into distinct external writes. This paragraph is an adaptation of the existing proof, not a new JDK experiment or a claim that Java supplies B or exact API prices.

Before a paper theorem is adopted: check the actual callback implementation and all-return paths, validate the price accounting with an independent operational checker, preserve the exposed-guard limitation, and compare contribution/importance with the strongest existing retry/locking work. The curve theorem is a separate claim currently undergoing external mathematical checking.

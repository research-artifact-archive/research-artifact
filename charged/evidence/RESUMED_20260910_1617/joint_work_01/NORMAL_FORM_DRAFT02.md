# Candidate r=0 all-program reduction — author draft, not adopted

Written after FINITE_PROTOCOL01 completed and before the Claude author04 response. That experiment enumerated canonical trees; this draft attempts to justify their scope separately. No finite agreement is used as the proof. The main interface is fixed163 Section 2, including separate own keys, permanent predecessor outputs, charged whole-kernel preparations, no preparation before readiness, and gate choice after job/mode selection.

## Statement to check

For each supplied finite B>=0 and deterministic admissible whole-kernel program P with Q<=n in every <=B-write environment, there exists a finite immediate-preparation policy tree T such that Q(T)<=n, max_E W(T,E)<=max_E W(P,E), and max_E L(T,E)<=max_E L(P,E), with all maxima over <=B writes. T chooses enabled fresh or prepared/cached completion; when the remaining certified write allowance is zero it may finish by prepare/cheap. Its decisions use the comparison outcomes recorded in the tree and no prediction of later writes. This is a domination result on worst resources, not trace equivalence to P under the same writer schedule.

## Restricted adversary and tree extraction

Fix an initial concrete state satisfying the interface. At every uncounted operation and fresh callback, the restricted adversary makes zero writes. At a completing comparison for a ready unfinished job it may choose zero writes or one fresh write to that job's own key, while maintaining an unconditional B-write counter. Fix a deterministic legal fresh identity at each such finite history. Never write to another unfinished key. If a prospective cheap comparison is encountered with positive remaining budget, its fresh-write child produces one noncompleting call. Because all n jobs require distinct completing calls, this contradicts Q<=n and admissibility. This argument uses an unconditionally B-bounded environment, including behavior on an inadmissible program; it does not let an adversary spend a conditional extra write after exhausting B.

Between counted operations, follow P through its finite uncounted behavior under zero writes. An infinite such segment would fail to complete in a finite-write environment. Consequently the next counted operation is reached. A fresh completion is a unary node. A cached completion whose zero-write outcome matches is a binary node with the actual zero-write and fresh-write continuations of P. Both branches complete the selected job, including the mismatch branch. Thus depth in completing calls is at most n. Each path spends at most B writes. The union of these finitely many concrete branch histories defines a finite deterministic tree, even if P contains arbitrary local computation or infinitely many possible concrete input values globally. The construction chooses one concrete value at each branch; it does not enumerate all values.

If stale snapshots or preexisting charged records are permitted initially, a cached call may already mismatch under zero writes. Keep only this zero-write continuation and represent it by a unary fresh node. The original already performs a protected whole kernel and completes at that node. Dropping its optional fresh-write continuation only restricts the lower-bound environment family. This handles intentionally stale record selection without claiming that every retained record matches. A cheap call that mismatches under zero writes is already inadmissible. If all snapshots originate in this execution and initial stores are empty, the stale case does not arise: no unfinished key is changed before its completing comparison, and its completed parents cannot change.

After B writes on a path, retain any one no-more-write suffix of P as the lower-bound witness; realize the remaining tree suffix by ready prepare/cheap steps. The original suffix might reuse preparations paid earlier, so DO NOT assert a fresh mandatory-work lower bound solely on that suffix. The cost comparison below is global across the complete execution.

## Global work charging and protected cost

For every complete restricted execution, each job needs at least one distinct charged kernel execution. Every binary cached mismatch additionally needs a distinct prepared whole kernel and the protected whole kernel performed in that completing callback. Kernels are tied to jobs and cannot be shared or fabricated. These charges are disjoint between jobs, so W(P,path)>=Omega+sum of w_i over binary mismatches in the extracted tree. Preparations may have occurred much earlier than their node; the bound remains global. Unary fresh nodes correspond to original protected completion, including a collapsed stale cached mismatch. Protected work on the original path is at least the sum of its extracted fresh and binary-mismatch weights; a replaced zero-budget suffix can only lower L. The two maxima need not have the same maximizing path, but each individual extracted path has an original <=B-write witness with at least its W and L.

## Realization against arbitrary writers

Run the extracted finite tree from the same DAG, preparing immediately before each binary cached node; fresh nodes execute one correct kernel using the current own input and actual exact predecessor outputs. Actual inputs and outputs can differ from the concrete values used during extraction. T ignores those values for scheduling: its lookup choices are the fixed choices at the current binary/unary tree node. They remain enabled because the set of completed jobs along that tree path is the same. Functional output correctness follows from the operation semantics, not from reproducing P's chosen concrete outputs.

Every actual mismatch has its own disjoint immediate-preparation-to-comparison interval containing at least one own-key write. Therefore the number of mismatches never exceeds B. Unobserved writes, multiple writes in one interval, writes to different keys or fresh nodes, and matching outcomes despite other writes merely leave a more conservative remaining allowance. T follows a represented path; at zero allowance, the B observed disjoint mismatches certify that no external write remains, making cheap publication safe. Every call completes, and there are exactly n. Its actual W is Omega plus its binary-mismatch weights, and L is its fresh plus binary-mismatch weights. Combining with the preceding global charging proves the proposed two-resource domination if all extraction details hold.

## Exact recurrence as a consequence, conditional on that proof

Let F(S,b) be the nondominated (E=W-Omega(S),L) pairs of these trees. F(empty,b)=F(S,0)={(0,0)}. For every ready i, write R=S\{i}. If b>0 include fresh candidates (e,w_i+l) for (e,l) in F(R,b), and cached candidates

    ( max(e0,w_i+e1), max(l0,w_i+l1) )

for independent successors (e0,l0) in F(R,b) and (e1,l1) in F(R,b-1). Take the nondominated union. The pairwise maximum is valid even when the W and L maxima use different branches. Keeping one nondominated successor suffices because the parent operations are monotone in both coordinates. The selected mismatch and matching subtrees may differ.

This recurrence is exactly the finite class implemented in check01.py; its correctness for arbitrary programs depends on the above argument. It is not a new general dynamic-programming principle. There are at most (min(B,n)+1)2^n subset/budget states. A frontier has at most as many different E values as subset sums over up to min(B,|S|) distinct jobs. Time/space can still be exponential. No claim about r>0, native elapsed time, arbitrary locking APIs, randomized policies, or uncharged compilation follows.

## Relationship to earlier claims

A and B have direct target-adversary lower bounds; C has a direct no-write-path lower bound and applies Lawler's inherited algorithm. None requires this complete recurrence. Keeping those proofs independent limits the consequences of a defect in this more general reduction. Earlier r>0 failures of greedy/all-tail W optimality and incompatible intermediate curves remain unchanged.

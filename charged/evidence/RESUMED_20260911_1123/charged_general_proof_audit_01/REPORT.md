# Author-side logical audit of the heterogeneous-fee residual theorem

Audit date: 2026-09-11 JST. Route: SCIENTIFIC. Requested deadline: 13:50 JST.

## Verdict and scope

**The closed form and both exact mode conditions are logically sound for the stated residual interface with causal deterministic policies, including policies that inspect actual identities.** I found no counterexample to that theorem. This conclusion follows from the argument below, not from zero differences in finite experiments. No exhaustive game, suffix enumeration, or other scientific experiment was run for this audit.

There is one local correction to the example: the state reached in world A after `cached0 bad; fresh1` has completed multiset **`q_D={2,2}`**, not a singleton `{2}`. PROOF01 line 70's phrase “D having q=2” should name both completed jobs. Its numerical inequalities are correct with the actual two-element multiset. If read as a singleton, the numerical interface example still works, but the stated reachability does not.

The important proof qualification is that necessity is for a residual contract restarted at a fixed history with offset `k`. It is not a claim that every continuation of a globally safe policy must satisfy that restarted contract after histories exposing extra writes. PROOF01 already disclaims this stronger claim. The replay argument below makes the distinction precise and avoids requiring the environment to observe the policy's private internal history.

This is an author-side proof adversary report, not a blind or human review. It makes no assessment of importance, acceptance, or submission readiness. The canonical proof and paper were not edited.

## Inputs inspected

- Primary: `charged_general_01/PROOF01.md`, lines 7–76. SHA-256: `cb0e9697e15ecbb3f4c9d88f97ffe230b0d2d80e3c12230d38e49c3094b25480`.
- Comparison: `charged_residual_01/PROOF03.md`. SHA-256: `de47f9c1f04fcc9765f21623477335040d728f0e1430cea572869f057791f468`.
- Derivation context only: `charged_dag_boundary_01/HYPOTHESIS02.md`. Its finite counts were not used as proof premises or re-executed.
- Paper comparison only: `RESUMED_20260910_0343/paper_candidate_bounded_retry/main.tex`, the body-only residual section beginning at line 242. This was used to check the interface boundary, not to audit the whole paper or a concurrently changing revision.

Paths above are relative to `RESEARCH_RESTART_20260905/RESUMED_20260911_1123/`, except the explicitly named `RESUMED_20260910_0343` path, which is relative to `RESEARCH_RESTART_20260905/`.

## 1. The proposition actually being proved

Fix the finite instance, a completed ideal `D`, and an admissible starting observation history `H`. Let `S=J\D`. The instance, costs, and readiness relation remain fixed; identities may affect the policy's decisions but not `p_i`, `h_i`, `q_i`, or which jobs are enabled by a completed ideal. At every cached call, mode and current preparation are committed before the environment's mismatch opportunity. From every such history both of the following are feasible: no write and a match; one own-key fresh-identity write and a mismatch. Calls have disjoint capture/comparison intervals. Every chosen action completes one remaining job in finite time.

Write `E_b` for causal writers with at most `b` future writes on **every play**, including plays other than the one against the policy under examination. Take `b` to be a nonnegative integer. Safety at `H` is

    exists one completing policy P, not supplied b,
      for every integer b >= 0 and every E in E_b,
        ell + L_future(P,E | H) <= G_(k+b).

The history `H` is fixed before considering suffix writers. Its past writes are not charged to the suffix cap `b`; `k` is the specified contract offset. The history does not restrict suffix environments beyond the stated residual interface. A host system with additional history-dependent restrictions on future writes would have a different contract.

The proof's policy class is deterministic and causal. If randomized policies are intended with a guarantee on every random execution, fixing a random tape reduces necessity to this class and the constructed deterministic policy gives sufficiency. An expected-cost or almost-sure interpretation is not established here and should not be silently substituted.

## 2. Quantifiers: a violating finite leaf really has an unconditional capped writer

Fix `P` and `H`. Restrict the environment to no writes outside cached mismatch opportunities. Fix a deterministic admissible rule for choosing the actual fresh identity at a mismatch. This rule must choose a value that mismatches the current capture, and can keep its own fresh-identity supply. It need not quotient or rename observations seen by `P`.

Under these writers, each history node has a single policy-selected ready job and mode. A fresh action has one successor and a cached action has at most two. The actual identities along each successor are concrete values fixed by the rule. Thus even an identity-sensitive `P` induces a finite tree of depth `|S|`. Different nodes with the same `(D,k,ell)` need not have the same action. No such nodes are merged in this argument.

Consider any one leaf, with `c` cached mismatches and future cost `t`. There is a causal script writer `E*` realizing that leaf: at the successive completion-call opportunities it requests exactly the designated mismatches, uses the chosen fresh-identity rule, and otherwise remains silent. It may stop on a publicly observable departure from the prescribed call/mode sequence. One can also define its behavior arbitrarily on departures; that behavior is immaterial after imposing the cap below.

Define `E*_c` by adding a physical write counter to `E*`: permit a requested write only while the counter is less than `c`. This new environment makes at most `c` writes on every play, even against other programs or on histories where the original script would have requested more. Therefore `E*_c` belongs to `E_c` by construction, rather than merely because one observed play happened to use `c` writes.

The interaction of `P` with `E*_c` reproduces the chosen leaf. Prove this by induction through the complete interaction. Before the `j`th selected write, only `j-1<c` writes have occurred, so the write and its exact identity are retained. All policy observations up to that point agree, hence its next action agrees. After the `c`th write, the original selected play contains no further writes, so suppression changes nothing on that play. For `c=0`, the writer is simply silent. Completion and all observed values are preserved.

It follows that a safe `P` must satisfy

    ell + t <= G_(k+c)

at **every** leaf of this restricted tree. The logical negation used for a lower bound is exactly

    for every candidate P,
      there exist c and an E*_c in E_c with a violating play.

Choosing `c` after deriving the finite play is legitimate for this existential counterexample. It does not supply `c` to the policy, change the policy, or require the writer to predict future actions while executing. The resulting capped script is a fixed causal environment.

The fact that the same policy receives no `b` is essential: changing the bound used to classify the writer must not change the actions of the policy. A family of separately optimized supplied-budget policies would not justify this replay inference.

For sufficiency, construct a policy that uses only the instance's prescribed numerical data and abstract completion outcomes. Any actual environment may make harmless writes, multiple writes, or writes during fresh calls. Nevertheless every cached mismatch requires a distinct write in its own disjoint interval. Thus if that execution has `c` mismatches and at most `b` writes, `c<=b`. Its job/mode/outcome sequence is a leaf of the abstract policy tree, so

    ell + t <= G_(k+c) <= G_(k+b).

The second inequality uses nonnegative `q` and remains valid after saturation. Extra writes do not have to be erased or replayed for this upper bound. In particular, the proof never identifies all actual writes with mismatches.

## 3. Exact finite-game induction, without assuming histories are binary-only

Define `W(D,k)` as the largest initial protected-cost allowance achievable by a finite abstract completion-policy tree, with each leaf of future cost `t` and `c` mismatches evaluated by `G_(k+c)-t`. Equivalently it is the maximum, over trees, of the minimum of these leaf allowances. There are finitely many trees for a fixed finite labeled DAG: every node offers finitely many job/mode choices and depth decreases by one job. Hence the maximum is attained. This is an analytic characterization, not an experiment performed here.

The preceding necessity argument maps every safe identity-sensitive policy to one such abstract tree by fixing the concrete fresh-identity rule. Therefore rich histories cannot yield an allowance larger than `W`. Conversely an abstract winning tree is a policy that ignores irrelevant identity information, and the preceding sufficiency argument makes it safe against all actual capped writers. Therefore `W` is the true viability threshold for this interface, for every fixed admissible starting history.

At a terminal state,

    W(J,k) = G_k.

The silent writer establishes necessity, and monotonicity in `b` establishes sufficiency.

For a ready `i`, let `D'=D union {i}`. A fresh first action incurs `p_i`, leaves the offset `k` unchanged, and has threshold

    F_i = W(D',k) - p_i.

A cached first action must admit both outcomes. The match threshold is `W(D',k)`; the one-write mismatch threshold is `W(D',k+1)-q_i`. The two continuation policies can differ after the observed outcome. They are subtrees of one causal policy, each satisfying all remaining suffix caps. They are not different policies selected using an unobserved bound. Thus the exact cached threshold is

    C_i = min(W(D',k), W(D',k+1)-q_i),

and

    W(D,k) = max_ready_i max(F_i,C_i).

This also has a direct adversarial reading. If `ell` exceeds this maximum, inspect the candidate policy's chosen first action. A fresh action leaves its sole child above the child's threshold. A cached action has at least one child above the child's threshold. Choose that child, with its actual identity, and repeat. The number of remaining jobs strictly decreases, so this produces a violating terminal leaf and then the capped writer of Section 2. This reasoning applies separately to every actual starting history; it assumes no equality of the policy's decisions across histories.

The phrase “each continuation must be safe” should be understood at these restricted zero-write or one-write first-action histories, or at a freshly posed local residual contract. It must not be generalized to arbitrary histories containing extra known writes. If `s` actual writes have been exposed but only `c<s` are mismatches, a global parent obligation may allow `G_(k+s+b)`, whereas restarting the local interface using only mismatches would demand the stronger `G_(k+c+b)`. The existing disclaimer correctly prevents that unsupported step.

## 4. Algebra and its boundary cases

Let `X` be a multiset of `m` nonnegative entries. Define `C_k=Top_k(X)` and `B_k=Top_k(X union {q})`, where `q=p+h`, `p>0`, `h>=0`.

First,

    min(B_k, B_(k+1)-q) = C_k.                         (A)

For `k=0`, `B_0=0` and `B_1>=q`, so the minimum is zero. For `1<=k<=m`, let `tau` be the kth largest entry of `X`.

- If `q<=tau`, adding `q` does not increase `Top_k`, so `B_k=C_k`. The top `k` entries of `X` together with the added `q` form a feasible `(k+1)`-element multiset, so `B_(k+1)>=C_k+q`. The minimum is `C_k`.
- If `q>tau`, the largest `k+1` entries consist of the added `q` and the largest `k` entries of `X`. Hence `B_(k+1)=C_k+q`, and `B_k=C_k+q-tau>=C_k`. The minimum is again `C_k`.
- Equality `q=tau` is covered by the first case; equal-valued entries retain their multiplicity.

If `k>m`, integrality gives `k>=m+1`, both `B` sums are fully saturated, and subtracting `q` gives `sum(X)=C_k`. This includes `X` empty with `k>=1`.

Second,

    max(B_k-p, C_k) = Top_k(X union {h}).              (B)

For `1<=k<=m`, insertion gives `B_k=C_k+max(0,q-tau)`. Therefore the left side is

    C_k + max(0, max(0,q-tau)-p)
      = C_k + max(0,h-tau).

To check the middle identity directly: if `q<=tau`, then `h=q-p<tau` and both increments are zero. If `q>tau`, the inner expression minus `p` equals `h-tau`. The last expression is exactly the insertion formula for `h`.

For `k=0`, the left side is `max(-p,0)=0`. For `k>m`, it is `max(sum(X)+h,sum(X))=sum(X)+h`, using `h>=0`. These are the corresponding right sides. No assumption of integral costs, strict separation between distinct weights, or unsaturated budgets is used.

## 5. Closed form, modes, and arbitrary ready order

Use induction on `|S|`, simultaneously for all integer `k>=0`. The terminal multiset is `q_J`, agreeing with `G_k`. For a ready `i`, put

    X_i = q_D union h_(S\{i}).

After completing `i`, the successor multiset is exactly `X_i union {q_i}` for both outcomes. The child's cost and offset, not its multiset, distinguish match from mismatch. Applying (A) and (B) to the recurrence yields

    cached threshold C_i = Top_k(X_i),
    fresh threshold  F_i = Top_k(X_i union {q_i}) - p_i,
    max(C_i,F_i) = Top_k(X_i union {h_i})
                 = Top_k(q_D union h_S).

The last quantity is the same for **each** ready `i`, which proves the claimed `V` and both permissions. A finite DAG with nonempty `S` has a ready vertex because `D` is an ideal. Its completion leaves an ideal with one fewer remaining job. Consequently a scheduler may choose any ready job, and there is a safe mode for it whenever `ell<=V`. The filter must continue enforcing the permissions at later states. Permission now means that a safe continuation exists, not that every later unconstrained action is safe.

More explicitly, if `ell>V` no first mode has a safe continuation. If `ell<=V` and cached is forbidden for the proposed ready `i`, then `ell>C_i`, so the equality `max(C_i,F_i)=V` forces `ell<=F_i`; fresh is permitted. Conversely, if fresh is forbidden, cached is permitted. At equality either or both may be permitted. This checks the potentially dangerous case where viability is supported by an unfinished premium but cached completion of that very job must be refused.

Only the multiset of all remaining premiums is needed, together with completed `q` values and the proposed job's own `p,h`. The mode calculation removes **one occurrence** of that job's `h_i` and inserts `q_i` on completion. Tied premiums are not removed as a set. The proposed job's body cost is needed; other unfinished body costs and edges are absent from the numerical predicate. The scheduler still checks readiness. This does not permit an implementation to omit unknown remaining premiums or silently apply the result to unbounded arrivals.

## 6. Physical offsets, ties, and the old theorem

The proof above is valid as an algebraic residual-interface statement even for `k>|D|`. Such an offset must not be described as a physically realized mismatch count. If `k>=|J|`, for example,

    V = sum(q_D) + sum(h_S).

All-fresh completion then exactly consumes at most the saturated allowance `sum(q_J)` when `ell<=V`. The local algebra covers this case; no unsaturated `k+1` step is being assumed. The empty instance has threshold zero by the terminal case.

For the physical range `1<=k<=|D|`, let `tau_D` be the kth largest completed `q`. Then

    Top_k(q_D union h_S) = Top_k(q_D)
      iff every future h_i <= tau_D.

If a future premium exceeds `tau_D`, replacing one completed entry of value `tau_D` gives a strictly larger feasible sum. If none does, the completed top `k` already attain the union's top sum. Equal premiums do not increase it. For `k=0`, both thresholds are zero separately.

Under `max_J h<=min_J q`, the displayed condition holds in every physical state. It also holds after either successor because the admission assumption is global and the physical inequality `k<=|D|` is preserved. Consequently the new `V` reduces to the old region and the old fresh predicate at the child. Every cached action is safe from that old region even without fee separation. This confirms PROOF03's declared exact domain and the body-only paper specialization. State-specific equality alone is not an invariant; the new proof does not rely on it being one.

For common `h`, every completed `q=p+h` is greater than `h`; with physical `k`, future `h` entries therefore do not displace the completed top `k`. For all `h=0`, future zeros have no effect. These reductions use multiplicities and remain true with ties among completed `q` values.

## 7. Reachable counterexample to permitting every cached action in V

Use the existing world A, not a new experiment:

    chain 0 -> 1 -> 2
    p = (1,1,1), h = (1,1,3), q = (2,2,4)
    G = (0,4,6,8), then saturation.

Starting from `D=empty, k=0, ell=0`, execute cached job 0 with a mismatch, then fresh job 1. The actual state is

    D={0,1}, q_D={2,2}, S={2}, k=1, ell=3.

Here `V=Top_1({2,2,3})=3`. Fresh job 2 satisfies `3+1<=Top_1({2,2,4})=4`. Cached job 2 fails its condition `3<=Top_1({2,2})=2`. If it is selected anyway, one future own-key write gives final cost `3+4=7`, exceeding `G_(1+1)=6`. The future writer can enforce a physical cap of one. Thus this is a concrete violation of the residual contract at a reachable viable state.

The prefix is reachable under a policy safe from the initial state, not just under an arbitrary unsafe prefix policy. One such policy is:

    cached 0;
      if mismatch: fresh 1, fresh 2;
      if match: cached 1;
        if mismatch: fresh 2;
        if match: cached 2.

Its four abstract leaves have `(mismatches, protected cost)` equal to `(1,4)`, `(1,3)`, `(1,4)`, and `(0,0)`. All satisfy `cost<=G_mismatches`. The disjoint-interval argument extends this to all capped actual writers, including harmless writes. This analytically verifies the required reachability.

Three jobs are minimal for this phenomenon when starting from the empty residual state with `k=ell=0` and using this completion-only action class. At a nonterminal prefix of an instance with at most two jobs, at most one job has completed. If `k=0`, viability requires `ell=0`. If `k=1`, that sole completed job was a cached mismatch, so `ell=q_i=Top_1(q_D)`. In either case the state is in the old all-cached-safe region, so no ready cached action can be forbidden there. This minimality statement concerns that stated initial condition; arbitrary external initial charges would be a different reachability question.

Suggested exact replacement for the ambiguous sentence in PROOF01 line 70:

> With completed jobs 0 and 1 of charged weights `q_D={2,2}`, `k=1`, `ell=3`, and the single remaining job 2 of `p=1,h=3,q=4`, we have `V=3`: fresh finishes at `4=G_1`, while a cached mismatch finishes at `7>G_2=6`. This state is reached in world A after cached job 0 mismatches and job 1 completes fresh.

## 8. Precision edits recommended to the root writer

These are not changes to the formula or evidence of a theorem counterexample.

1. Apply the completed-multiset correction above. A singleton `{2}` with `k=1,ell=3` is not the claimed prefix: with only one completed job and one mismatch, that job contributes exactly 2 under the residual completion rules.
2. In the standalone contract, explicitly write “every integer `b>=0`” and “one causal deterministic completing policy” (or explicitly give a pathwise randomized convention). The later proof already uses these conventions.
3. In the capped-writer paragraph, use “cap the causal script at `c` writes; the cap alone ensures membership in `E_c` on every play.” Stopping on a departure from the public call history is optional. There is no need to require the writer to observe private policy state.
4. In the recurrence paragraph, qualify continuation necessity as applying to the restricted zero/one-write successor histories. For general actual histories, retain the explicit statement that this is a restarted residual interface, not a global-history characterization. The strengthened history argument in Section 3 supplies the full proof without making that stronger claim.

These precision edits can be incorporated without rerunning the already completed exhaustive experiments. They are supplied here only; no canonical file was changed by this audit.

## 9. Completion and process scope

The accompanying `RECEIPT.json` records finish time, input hashes, and the report hash. All audit writes are confined to this directory. No external fetch, Claude use, human evaluation, usage reset, credit operation, paid API, helper agent, exhaustive game, or persistent/background job was initiated. There are no audit-owned child processes or tool sessions left active. This statement concerns this audit's work; it is not a claim that the concurrently working root has stopped.

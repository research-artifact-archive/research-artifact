# Unknown-budget observation boundary on a four-job DAG

This author mathematical proof follows DRAFT01 and the fixed finite check01. It strengthens the erased lower-bound presentation with a forward coupling that explicitly includes early preparations and retained records. The finite erased search covers its declared canonical class only; it is not the all-program proof below. The graph family was selected after exploratory general-DAG work, not as an independent evaluation population. No native timing claim or mechanical proof certification is made.

## 1. Interface and quantifiers

Use the persistent whole-kernel completion interface of the manuscript. Jobs form a DAG. A job becomes ready after its parents complete. Its pure opaque kernel costs its fixed positive work on every execution and receives its own captured input identity and exact immutable saved parent outputs. A retained record certifies its target, capture identity, parent tuple and creating computation. Copying cannot retag it. Preparing before readiness, partial kernel reuse, uncharged computations, and externally supplied completion are excluded. Inspections of any live key and arbitrary finite records/snapshots are allowed. At each finite history an unfinished target admits a write identity fresh to all its preceding captures and records, including old snapshots.

The environment writes before each foreground action. After this gate, selection may use records already computed in the prior store; new unprotected computation is a separate action with a later gate. A cheap call succeeds only on a matching record; a fresh call computes under protection; a cached call uses its matching record or recomputes under protection. Successful completion publishes and saves its output and persists. A call ends its guard. Q counts calls, W all kernel executions from the common start, and L protected kernel executions. Every job must complete after finitely many foreground actions on every finite-write play; infinite free inspection or preparation is not completion.

For the erased contract every kernel execution of job i returns the same immutable per-job object z_i. A cached invocation's entire permitted visible transition reveals only this output/completion: it saves no compared input, Boolean, branch-dependent record selection, or callback-local side effect. Work counters, allocation IDs, clocks and writer-history ghosts are hidden. The controller may retain everything else, including old snapshots, inspect outside calls, and branch on cheap success/failure. Merely omitting a returned Boolean would not suffice. For the visible contract the cached comparison is also returned.

Fix integer r>=1. V_r contains one deterministic causal program P receiving no write bound, completing with Q<=n+r against every environment with a finite unconditional write bound. In addition, P must satisfy sup_E L(P,E)<=Top_(b-r)+ for every b>=0, where Top_k is the sum of the largest min(k,n) job works and Top_0=0. For either observation contract we minimize W_P(B)=sup over environments using at most B writes of W(P,E), pointwise over V_r. The attaining policy must be one member of V_r for the entire curve, not a separate program selected using B.

## 2. Result

Take A→U→V and independent Z, with works (M,1,1,2). Assume integers M>=3, r>=1 and the sufficient condition r(M-2)>=3. Put Omega=M+4 and C=Omega+(r+1)M. The least entire curves are

* visible: W(B)=Omega+B M for B<=r+1, and W(B)=C+1 for B>=r+2;
* erased: W(B)=Omega+B M for B<=r+1, W(r+2)=C+1, and W(B)=C+2 for B>=r+3.

One policy under each contract attains its whole curve and the optimal protected curve Top_(B-r)+. For M=5,r=1, Q<=5 and B=0,...,5 give visible W=(9,14,19,20,20,20), erased W=(9,14,19,20,21,21), and L=(0,0,5,7,8,9).

This family gives a sufficient separation condition, not a characterization of every M,r nor a smallest-instance claim. It does not settle the least whole curve for arbitrary DAGs.

## 3. Attaining policies and all upper coordinates

Both policies use the order Z,A,U,V. Prepare immediately before each cheap call until r cheap failures have occurred, then use immediate prepare/cached. The erased policy continues this way unconditionally.

The visible policy has one exception. If Z completed cheaply and both A and U completed by cached mismatch, finish V fresh, before preparing V. The trigger certifies at least r+2 distinct writes. Only A and U have protected bodies at this point; adding V gives M+2=Top_2. This is permitted at every consistent bound B>=r+2. All other paths retain the standard optimal-protection bound. There are at most r failed calls and four completions, hence Q<=4+r. Both policies complete under every finite write count.

Before the threshold, every failed preparation costs at most M. Each failed cheap call or cached mismatch requires a write in its own disjoint interval from immediate preparation to comparison. At B<=r+1 this bounds W by Omega+B M, and the fresh exception is unreachable. More generally it suffices to bound duplication beyond the mandatory Omega.

If cached mode begins at Z, all r cheap failures were at Z. The duplicate charge is at most 2r+Omega, since each job has at most one cached mismatch. The sufficient family condition gives

    2r+Omega <= (r+1)M+1  iff  r(M-2)>=3.

If Z completed cheaply, failed work is at most rM. Cached duplication occurs only along the three-job chain. The visible exception prevents all of A,U,V from being duplicated, so the duplicate sum is at most M+1. Thus visible W<=C+1. The erased policy permits chain duplication M+2, giving W<=C+2. At B=r+2 at most two cached mismatches can follow the r cheap failures, so its chain duplication is at most M+1 and erased W<=C+1. Additional harmless writes do not increase these policy bounds. The general optimal-protection lower theorem, applicable to these DAG jobs, turns the upper protected guarantees into the claimed exact curve.

## 4. Common all-program prefix and early lower coordinates

The order-independent maximum-job lower argument already applies to root A. For completeness, at most k<=r+1 useful fresh writes at its no-write-matching comparisons force k distinct M-unit duplicate computations. Before any completion with at most r writes, optimal protection requires L=0; a fresh or stale-cached completion is impossible. A useful cached mismatch within that prefix is likewise impossible. At the (r+1)-st useful comparison, an additional cheap failure would exceed the global r spare calls, so A must complete by cached mismatch. Finite completion forces a relevant comparison even if arbitrary inspections and preparations intervene. Cap the writer by k on every play. Charge these invalidated preparations separately from the mandatory final body for each job. This gives W>=Omega+k M for all k<=r+1; k=0 is mandatory work alone.

A useful way to fix the common prefix is E_r: insert a fresh write at the first r no-write-matching A comparisons, and then stop. The writer has an unconditional r-write counter. For every P in V_r all r affected calls must be cheap failures: any protected completion in an at-most-r-write execution violates L=0. Finite completion forces these r failures before A can complete. Therefore A,U,V are unfinished after the last one. Other failed calls are impossible because the r failures already exhaust the call slack.

## 5. Visible all-program lower plateau

Extend this E_r prefix by writing once at the next useful A comparison, with an unconditional r+1 counter. On the no-more-write continuation, A cannot finish fresh or stale-cached because the prefix has only r writes and permits no protection. It cannot take another cheap call: one fresh write would fail it and contradict Q<=n+r in a finite environment. Thus finite completion forces a no-write-matching cached A call. A fresh write invalidates every available A record, including any selected after the gate, and forces a cached mismatch.

The actual prefix now has r+1 writes and L>=M. With no further writes optimal protection allows only Top_1=M. U, which was not ready before A completed, therefore cannot complete fresh or stale-cached. Another cheap call remains universally inadmissible, since one further write would exceed the call cap. Its eventual useful matching cached call is forced. Use one additional fresh write there, and stop permanently; an unconditional r+2 counter applies on every play. Global distinct charging gives

    W >= Omega+rM+M+1 = C+1.

This bound holds under either observation contract at B=r+2. For larger B it persists by inclusion of bounded environment classes. It does not assume that all costly completions occur in a particular topological order.

## 6. Erased all-program lower plateau: forward coupling

Fix any erased P in V_r. First consider the completed reference execution against E_r above. It uses exactly r writes and has L=0. After its r useful cheap failures, every remaining completion must be matching cached: fresh/stale-cached would have positive protection, while cheap is either already failing or can be made to fail by one additional write in another finite environment. This latter extension is a call-cap contradiction; that additional write is not present in the reference execution. Finite completion rules out endless free actions. In particular, A,U,V have matching cached completions in the reference suffix.

Construct a second writer with the same first r writes and then three explicit unused slots, one for A, U and V. It spends each slot at that job's first subsequent useful cached comparison and never spends a slot twice. Its unconditional count is at most r+3 on every play; no truncation of an unbounded writer is involved.

After the common r-failure prefix maintain equality of the permitted foreground history, live input map, saved completed outputs, available snapshots/records and controller locals in the two executions. Hidden resource and writer-history ghosts are excluded from this relation. Intervening foreground operations choose the same job/mode and receive the same values. In particular, inspections see the same live entries. Preparations capture the same own identity and immutable parent tuple, create corresponding records and incur the same ordinary work.

At a selected cached call the reference continuation matches. The inserted own-key identity is fresh to every pre-gate target record and snapshot, so no post-gate selection can produce a matching record in the second execution. One execution uses the prepared result; the other recomputes. Nevertheless, both publish and save the identical z_i. Strict erasure excludes any surviving compared identity, flag or branch-dependent retained state. Thus the foreground relation is restored on return. The transient write identity has no permitted surviving handle, and all old snapshots and records remain corresponding. This establishes the relation inductively, including arbitrary early preparations and record stores; it does not assume that simply deleting a write automatically preserves an arbitrary program's state.

Consequently the second execution performs cached mismatches at all three A,U,V calls. Charge the r invalidated A preparations and the three cached duplicates separately from the four mandatory final computations:

    W >= Omega+rM+M+1+1 = C+2.

The r failed preparations have pairwise fresh capture identities. The A mismatch invalidates all those captures and a later useful preparation; U and V are different targets and can be prepared only after their parent completes. Constant returned objects do not identify these paid computations: record certificates cannot be retagged, and each new required record executes its prescribed whole kernel. This is exactly the global distinct-charge argument of the manuscript's charging lemma.

The constructed writer is at most r+3 bounded, so W>=C+2 at that coordinate and all larger coordinates. Together with the preceding lower bounds and explicit upper policies, this proves both least entire curves. Visible-branch tree extraction is not used as an erased-program completeness theorem.

## 7. Corroboration and boundaries

The pre-fixed check01 contains 28 roots, M=2,...,8 and r=1,...,4: 21 satisfy the sufficient family condition and seven remain out-of-family controls. Every root completed; all 9,373 interpreted paths and both deliberate negative controls are retained. The family curves agree with the unchanged visible oracle and the explicitly restricted canonical erased oracle. The two invalid policies expose why Z must have completed cheaply and why the exceptional fresh V must not first be prepared. These checks corroborate the policies and formulas; Section 6 supplies the independent mathematical responsibility for arbitrary erased programs. Inputs overlap earlier visible investigations and are not new independent populations. No conclusion about native latency, general-output erasure, arbitrary positive-retry DAGs, or FSE acceptance follows.

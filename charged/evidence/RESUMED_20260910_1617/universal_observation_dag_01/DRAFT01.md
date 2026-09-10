# Candidate: cached comparison information matters under unknown budgets on a DAG

Exploratory author proof draft; not adopted or independently certified. Same strict full-history erased interface as paper207 Section5.2: every job kernel returns one immutable per-job object; cached visible transition exposes only output/completion, with no compared input/flag/branch-dependent retained state. Free inspections and retained records remain allowed. The controller receives no B and belongs to V_r: all finite-write plays complete with Q<=n+r and L<=Top_(b-r)+ for every bound b. All whole-kernel work is charged from the common start, and fresh own-gate writes invalidate all prior target records.

Let jobs(A,U,V,Z) have works(M,1,1,2), precedence A→U→V and independent Z. Let integer M>=3, r>=1 satisfy r(M-2)>=3, and Omega=M+4. Write C=Omega+(r+1)M.

Candidate exact least curves, attained by one policy per observation contract:

visible W(B)=Omega+B*M for B<=r+1, and C+1 for B>=r+2.
erased W(B)=Omega+B*M for B<=r+1, C+1 at B=r+2, and C+2 for B>=r+3.

For M=5,r=1, these are(9,14,19,20,20,20) and(9,14,19,20,21,21) at B0..5. Both have optimal L=(0,0,5,7,8,9) and Q<=5. This would complement, not refute, the independent-job theorem whose attaining policy needs no cached Boolean.

## Visible attaining policy

Use fixed order Z,A,U,V; prepare/cheap until r cheap failures, then use immediate prepare/cached. One exception: if Z completed cheaply and both A and U completed by cached mismatch, choose fresh V BEFORE preparing it. The exception has at least r+2 distinct writes and protected load M+1 before V; fresh V makes M+2=Top_2, which is allowed at every consistent budget. Later writes only loosen the permitted bound. Call count stays n+r. Every other path is the standard optimal-protection policy.

If cached mode started at Z, failed preparation costs at most2r and all cached duplicates at mostM+4. This is <=(r+1)M+1 by r(M-2)>=3. Otherwise Z completed cheaply; failed work costs at mostrM. Among chain duplicates, the only way to exceed M+1 would be to mismatch all A,U,V, but the fresh exception prevents it. Thus W<=C+1 at every budget. At B<=r+1 the standard disjoint-interval argument gives Omega+B*M; the exception cannot be reached before r+2 writes.

## Visible all-program lower bound

Early values through r+1 are the existing order-independent maximum-job target lower bound. For B=r+2, target A with fresh writes only at its no-write-matching comparisons until r+1 useful cheap failures or completion, with an unconditional r+1 cap. Prefix capping and L<=Top_(d-r)+ force exactlyr useful cheap failures and one useful cached mismatch before A completes; a fresh or stale-cached completion at d<=r would violate zero protected work. The call cap excludes r+1 failures. The independent job can only add mandatory work and cannot remove these charges. At A completion the actual prefix has d=r+1 and L>=M; the no-more-write continuation must keep L<=Top_1=M. U therefore cannot complete fresh/stale-cached. A further cheap call can be invalidated and violate the universal call cap. Finite completion forces a no-write-matching cached U; one additional fresh write makes it mismatch. The environment is unconditionally bounded by r+2, and global distinct charges give W>=Omega+rM+M+1=C+1. This bound persists at larger B.

## Erased attaining policy

Use Z,A,U,V, cheap until r failures and then all cached, ignoring cached outcomes. When cached mode begins at Z, duplicate work is at most2r+M+4<=rM+M+1. When Z completed cheaply, failure cost<=rM and cached chain duplicate sum<=M+2. At B=r+2 at most two cached jobs mismatch and their chain sum<=M+1; at B>=r+3 all three may mismatch. The early-budget bounds remain unchanged. This attains the candidate erased curve.

## Erased all-program lower bound, key obligation

Obtain the same r useful cheap failures followed by a cached mismatch of A. Then force cached mismatches at U and V, using at mostr+3 writes in total. Because the r useful failures exhaust every spare call, an additional cheap attempt can fail in a finite extension and is universally inadmissible. After A, and then after U, erase the hidden own-gate writes from a counterfactual execution while retaining the r cheap-failure writes. Each cached completion publishes/saves the same per-job object, its pre-gate snapshots/records are unchanged, and the inserted own identity leaves no visible survivor. Free outside inspections see the same post-completion live map; saved predecessors and the whole allowed record/local state agree. By induction the controller follows the same visible history in this counterfactual r-write execution. Its optimal-protection cap is L=0, so the next child cannot complete fresh or via a stale cached record there, and hence cannot choose such an operation on the original indistinguishable history. Finite completion forces a no-write-matching cached child; a fresh gate write invalidates every retained record.

The useful preparations charged at A'sr failures and at A,U,V cached mismatches are pairwise distinct from each other and from the four mandatory completions. Thus W>=Omega+rM+M+1+1=C+2. Impose an unconditional r+3 counter on the constructed writer, stop on off-witness histories, and stop at any noncompliant r+1cheapfailure event. The proof must explicitly check its counterfactual prefix relation for arbitrary early preparations/records; do not invoke the visible-branch normal-form theorem as an erased-policy completeness theorem.

No actual-time benefit, arbitrary-output erasure, global minimal input or general DAG least-curve theorem is claimed. Prior tied-order exploration03--06 is the motivating source; its mixed/negative results remain unchanged.

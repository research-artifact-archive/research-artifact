from pathlib import Path
import hashlib, json
from datetime import datetime, timezone

D = Path(__file__).resolve().parent
old = D / 'PROOF_CANDIDATE01.md'
assert hashlib.sha256(old.read_bytes()).hexdigest() == '023e94a23c325cda84eab44d87e42550ef3d4824483169f2bde1ead2b589cfd4'
s = old.read_text()
s = s.replace('These are author proof candidates, fixed before numerical corroboration.', 'This is the second author proof version, following the first fixed corroboration and Cost10 criticism. The first version, inputs, run and raw criticisms remain unchanged.')
s = s.replace('## A. Complete supplied-one-write frontier for W and P_g', '''## Explicit operation and adversary contract

Programs are deterministic. Their two objective coordinates take separate pathwise suprema over admitted environments and initial inputs; expected randomized costs are outside this theorem. Each whole kernel execution necessarily costs exactly w_i, independent of its inputs, not merely at most w_i. Its computed record contains the exact live own-key identity read and completed predecessor outputs. The charged common start supplies no free computed records. Inspections and local record choices do not complete jobs or protect kernels.

Each job needs its own completing call; a call completes at most one job. Cheap publication compares a saved record and either completes on a match or counts as one unsuccessful call. Fresh completion executes the kernel and completes under its guard. Cached completion compares under its guard and, within that same single counted call, either reuses the matching record or executes the kernel and completes on mismatch. The guard is released at return. The cached comparison is exact, with no spurious mismatch. Its Boolean result is visible in part A, although B's attaining policies need no cached result. A kernel callback that instead returns an error and requires an additional call is a different interface.

Before each selected operation's gate, a writer can install a fresh own-key identity distinct from all retained target identities. All preparations count toward W, including discarded and early computations. Writers and programs can depend on the observed history; a globally b-bounded environment must respect its cap on every play, including inadmissible-program plays. A finite prescribed own-gate write sequence, with an unconditional cap, supplies each lower-bound witness used here. Completed jobs persist and can be used as parents without being invalidated again.

## A. Complete supplied-one-write frontier for W and P_g''')
s = s.replace('Fix a body-work cap W<=S+M, where S=sum_i w_i and M>=0.', 'Require completion, Q<=n and W<=S+M in every globally at-most-one-write environment, where S=sum_i w_i and M>=0.')
s = s.replace('including any already-stale cached completion', 'with all paid preparations accounted for')
s = s.replace('Classify its matching cached completions as C and its fresh or already-stale cached completions as the complement. An already-stale cached completion pays at least a fresh completion in both coordinates.', 'Classify its matching cached completions as C and its fresh completions as the complement. Correctly formed target records do not become stale on a no-write run; initial preparations are charged. Even if an enlarged interface admitted an initially stale record, its cached completion would pay at least a fresh completion in both coordinates, provided mandatory computation remains charged.')
s = s.replace('The original pair is therefore weakly dominated by the displayed pair for C.', 'For this no-write execution e_0, let Phi(C) be the displayed subset pair. Componentwise, Phi(C) <= (W_t(P,e_0),P_t(P,e_0)) <= (sup_E0 W_t(P,E0),sup_E0 P_t(P,E0)). The original pair of separate suprema is therefore weakly dominated by the displayed pair for C.')
s = s.replace('As a threshold crosses a weight,', 'For an intermediate threshold, the actual duplicate bound is max({w_i:w_i<=M} union {0}); equality with M is needed only at the retained weight thresholds. As a threshold crosses a weight,')
s += '''

## C. Information and comparison-charge boundaries within the same regime

These statements keep the same n-call, whole-kernel, single-completion-call interface and the same fully charged W_t/P_t resources. They are direct consequences of B's equivalence, not comparisons between the different regimes of A and B.

**Supplied zero-write information.** If B=0 is supplied, immediate preparation followed by cheap publication of every ready job terminates in exactly n calls. It pays exactly S total work and no protected or guarded charge. Mandatory kernel work gives W_t>=S, and costs are nonnegative, so (S,0) is the single nondominated point. This holds with arbitrary nonnegative g and c and every DAG. It assumes the stated zero charge for cheap publication; an added positive cheap charge defines a different cost model.

**Universal completion with zero additional comparison charges.** Retain the requirement of completion with Q<=n for every finite-write environment, evaluate costs at B=0, and set all c_i=0. The no-write lower bound from B still rules out cheap calls. All-cached dominates each fresh choice and attains the unique pair (S+Gamma,Gamma). Thus the heterogeneous-positive-c result is a transition within this same universal, zero-write evaluation regime; changing g alone gives a constant shift, not the subset tradeoff.

**At most d distinct positive comparison charges.** Omit all jobs with w_i<=c_i from the cached set. Partition the remaining jobs into d groups with equal charges c_v and sizes n_v. Sort each group's positive profits w_i-c_v in nonincreasing order and let A_v(k) be its first-k profit sum. For a fixed cardinality vector (k_1,...,k_d), total comparison cost is sum_v k_v c_v and does not depend on identities within a group. Protected cost is minimized by the top k_v profits in each group, because replacing a smaller selected profit by a larger unselected one preserves total cost and decreases protected cost. Hence Pareto pruning the candidates

    (S+Gamma+sum_v k_v c_v, S+Gamma-sum_v A_v(k_v))

for 0<=k_v<=n_v is exact. There are at most product_v(n_v+1)<=(n+1)^d candidates. Group sorting and prefix sums take O(n log n) comparisons; forming and sorting m candidates takes O(dm+m log m) arithmetic/comparison operations, with ordinary polynomial-bit integer sums. Fixed d therefore gives a polynomial-time frontier. This is an exponent depending on d, not a fixed-parameter tractability assertion. For d=1 it gives the common-charge result; the exponential example has d=n. Since B's argument depends on a topological no-write completion order but not on which order it is, the subset frontier and these statements hold on any DAG as well as independent jobs.

These elementary consequences describe the price of universal completion and heterogeneous validation charges in this interface. They do not establish an empirical speedup, a real caller SLA, strong NP-hardness, original free-comparison hardness, or a least full curve for positive-retry DAGs.
'''
out = D / 'PROOF02.md'
assert not out.exists()
out.write_text(s)
raw = D / 'CLAUDE_COST10_RAW.md'
assert hashlib.sha256(raw.read_bytes()).hexdigest() == 'da99bba8ec17fdb227a6fc7b57bfa6f25b011f773049cd02200588ae602f18c4'
receipt = {'utc':datetime.now(timezone.utc).isoformat(),'role':'author-side proof critique','requested_model':'Fable5.1 maximum','actual_model':'Opus4.8 maximum per in-generation service fallback notice','displayed_thinking_time':'12m34s','url':'https://claude.ai/chat/5d5533ce-45f3-4255-a1a8-8b293294b898','raw':{'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'bytes':raw.stat().st_size,'chars':6715,'char_fnv1a32':1304205400},'proof02':{'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size},'prior_raw_and_first_run_changed':False,'safeguard_bypass_or_retry':False,'paid_actions':0}
(D/'CLAUDE_COST10_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))

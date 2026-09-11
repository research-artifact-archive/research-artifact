# A short policy separating minimum-ready order from admissible completion

This is author mathematical development after the previously observed six-job example, not a fresh independent evaluation population. The earlier tied examples, nine distinct-weight equalities, one successful distinct-weight candidate, all protocols and the original large trees remain unchanged. The companion lower proof is `../general_DAG_followup_01/PROOF08.md`. The argument below replaces reliance on the large unrestricted tree with a short explicit policy and an eight-case calculation. The chain-first guarded construction and the warning about premature fresh5 appeared in the earlier ordinary-model technical critique for the tied predecessor. Here they are instantiated for the distinct weights, with an explicit phase policy, complete case table and standalone verification. It does not establish the unrestricted all-program optimum752 or a least whole curve for every DAG.

## 1. Statement and interface

Use deterministic causal programs in the visible-comparison, persistent whole-kernel completion interface. Jobs0,...,5 have works `(62,83,15,84,30,31)` and edges `1->2, 3->4, 4->5`. Each ready job must complete once. Preparation executes and charges the entire kernel on its captured own identity and immutable completed-parent outputs. Paid records and snapshots may be retained; copying cannot retag a computation. A fresh own-key gate write invalidates every earlier target record. A cheap mismatch consumes a failed call; cached always completes, recomputing protectively on mismatch; fresh always computes protectively. Guards end on return. Job/mode is fixed before the writer gate; any post-gate record selection is from the already-computed store. Inspections and local actions cannot replace finite completion.

Write `Omega=305` and `G=(0,84,167,229,260,290,305)` for the sorted largest-work sums. An admissible policy receives no write budget B and, against every environment with any finite unconditional write bound B, completes with `Q<=9` and `L<=G[min(6,max(0,B-3))]`. The restriction called minimum-ready requires every cheap/fresh/cached invocation to target a minimum-work ready unfinished job; it does not constrain preparation order or record retention.

Every such minimum-ready program has `W(7)>=766`, by the all-program lower proof summarized in Section4. The short unrestricted policy below has `W(7)=752` while satisfying all the same call and protected-work bounds at every B. All works are distinct. Its cheap phase itself follows minimum-ready order: the counterexample concerns imposing that target rule throughout the guarded phase as well.

## 2. Explicit policy

Prepare immediately before each comparison call. Until three cheap failures, call the minimum-work ready job cheaply. Let j be the target of the third failure.

* If there are fewer than three failures before completion, finish in the cheap phase.
* If `j!=1`, finish all remaining jobs by immediate cached completion in minimum-ready order.
* If `j=1`, job0 has completed, and jobs1,...,5 remain. Cached-complete jobs3,4,5 in that order, regardless of their flags. Then complete job1 and job2 in order. At each of these last two decisions use fresh exactly when `L+w_i <= G[min(6,d-3)]`; otherwise use immediate cached. Here d is the number of observed cheap failures plus cached mismatches, and L is the policy's sum of weights of protected completions. These values are computed from declared results and known weights, without inspecting hidden resource counters or receiving B.

The policy never prepares a job before choosing fresh for it. In the special chain3,4,5 it deliberately keeps cached calls even when a fresh body would currently fit the protection cap. Their comparison results may permit a later, more expensive fresh completion.

There are at most three failed calls and six completing calls, hence Q<=9. Every selected operation terminates; the finite policy therefore completes. A bad comparison requires a write between its immediately preceding preparation and its comparison. These intervals are disjoint, so the observed d never exceeds actual writes. Arbitrary extra harmless writes do not create new program branches. It suffices to verify protection at the smallest consistent count d; G is nondecreasing.

Outside the special suffix, protection is zero before the third failure and consists of at most d-3 distinct cached-mismatch jobs afterwards. Its sum is at most G[d-3]. Inside the special suffix, the chain's protected set consists of exactly its mismatching jobs, so the same argument holds until job1 is selected. Section3 checks the two remaining operations including every cached branch after a fresh operation.

## 3. Eight special-suffix cases

Let S be the set of cached mismatches among jobs3,4,5, whose weights are84,30,31. At their return the state is `d=3+|S|`, `L=sum(S)`. All three chain jobs have completed. Matching job1 leaves d,L unchanged; mismatching it adds1,83. The following table gives the prescribed job1 mode, job2 modes after job1, and the largest suffix duplicate work. C means an immediately prepared cached call; F means a fresh body. Duplicate work excludes Omega and the three failed preparations.

| S | d,L after chain | Job1 | Job2 after job1 match / mismatch | Maximum suffix duplication |
|---|---:|---|---|---:|
| empty | 3,0 | C | C / C | 98 |
| {3} | 4,84 | C | C / C | 182 |
| {4} | 4,30 | C | F / F | 113 |
| {5} | 4,31 | C | F / F | 114 |
| {3,4} | 5,114 | C | F / F | 197 |
| {3,5} | 5,115 | C | F / F | 198 |
| {4,5} | 5,61 | F | F (no comparison at job1) | 61 |
| {3,4,5} | 6,145 | F | C (no comparison at job1) | 160 |

For cached job1 rows, substitution in G checks both subsequent job2 branches. The potentially tight cases are S={3}: a job1 mismatch gives L=167,d=5, so a job2 mismatch raises these to182,6, below G[3]=229; and S=empty: two tail mismatches give98,5, below G[2]=167. Rows where job2 is fresh give final protected values at most129,212 or213 at their corresponding d. For S={4,5}, fresh1 then fresh2 give L=159 at d=5, below167. For S={3,4,5}, fresh1 gives228 at d=6, below229, then cached2 either matches or gives243 at d=7, below260. Thus every prefix obeys its cap, including branches after fresh completions. This proves protection for every actual finite write budget, not just B=7.

At B=7 the total duplicate work in each non-special phase is bounded as follows. The cheap minimum-ready order is0,1,2,3,4,5; all jobs preceding the third-failure target have completed cheaply. A bad cached comparison can duplicate a remaining job only once.

| Third-failure target | Bound on failed preparation work | Bound on later duplicates at B<=7 | Bound on total W |
|---|---:|---:|---:|
| 0 | 3*62=186 | G[4]=260 | 751 |
| 1 | 3*83=249 | eight-case maximum198 | 752 |
| 2 | 3*83=249 | 15+84+30+31=160 | 714 |
| 3 | 3*84=252 | 84+30+31=145 | 702 |
| 4 | 3*84=252 | 30+31=61 | 618 |
| 5 | 3*84=252 | 31 | 588 |

The target0 row uses at most four later mismatches because three writes already caused failures and B<=7. The other non-special rows use all remaining weights, a valid upper bound even if fewer writes remain. If the third failure never occurs, there are at most two lost preparations and no protected duplication, so W<=305+2*84=473. These cases prove W(7)<=752.

Equality is attained by cheap0 matching, three cheap1 failures, cached3 mismatching, cached4 matching, cached5 mismatching, cached1 mismatching, and fresh2. This path has six writes, nine calls, L=213 and

    W = 305 + 3*83 + 84 + 31 + 83 = 752.

All comparisons have their own immediate preparation and each specified mismatch is realizable with one fresh own-key gate write. A writer capped unconditionally at six such slots realizes the path. Therefore this policy's W(7) equals752.

## 4. All-program lower bound under minimum-ready targets

For any admitted program, stopping a concrete d-write prefix enforces the cap G[(d-3)+] at that prefix. Give no writes until job0 completes; it is the unique minimum ready target. At job1 force three useful comparisons to fail with fresh identities. They must be cheap, since protection is zero at budgets at most3. A useful comparison means that the same selected call without its gate write would match some already-paid record; the writer may depend on the fixed deterministic program. Finite completion forces these comparisons despite free inspections and early preparations. An earlier deliberately stale failure would make the three forced failures incompatible with the call cap, so it cannot avoid the argument in an admitted program.

The three failures charge249 distinct lost units and exhaust the call slack. A further cheap call either already fails or can be failed by one further write in a finite alternative environment, violating Q<=9. Minimum-ready order now forces targets1,2,3. Fresh or stale-cached completion is forbidden respectively by `83>0`, `83+15>84` and `83+15+84>167` on the no-more-write continuation. Their useful matching cached calls are therefore forced. Write at each one, adding duplicate charges83,15,84 and reaching six writes with L=182.

Jobs4,5 remain. They cannot both complete protectively on the no-more-write continuation because `182+30+31=243>G[3]=229`; this includes fresh and already-stale cached calls. At least one matching cached comparison must occur. A seventh write at the first such comparison adds at least30 duplicate units. The writer reserves three initial slots at job1, one subsequent cached slot for each of1,2,3, and one final slot among4,5. Each is used at most once on every play, so it has an unconditional seven-write cap.

A fresh identity invalidates every retained target record, including any alternative selected after the gate. A record that would match the no-write continuation is already paid; distinct useful writes retire distinct captured identities. Together with the mandatory final computation at each job these are separate kernel executions. No double charge is introduced by early preparation or record copies. Thus every admitted minimum-ready program obeys

    W(7) >= 305 + 3*83 + 83 + 15 + 84 + 30 = 766.

Combining this bound with Section3's explicit policy proves strict suboptimality of imposing minimum-ready targets on all calls. The upper alone suffices; unrestricted all-program optimality752 is not asserted.

## 5. Fixed corroboration and a premature-fresh control

The fixed check01 enumerates all427 branches of this newly constructed policy. An independently implemented, unchanged operation interpreter agrees on every worst coordinate: W=(305,389,473,557,641,721,752,752,781,796) and L=(0,0,0,0,84,167,229,260,290,305) at B0,...,9. These W coordinates equal those of the earlier larger full-oracle tree, a retrospective observation rather than a general optimality proof.

The predetermined control also allows fresh bodies in the special chain whenever the current protection inequality permits them. All421 paths still satisfy Q and L, but W(7)=766. On three cheap1 failures, cached3 and4 mismatches allow fresh5; then cached1 and2 mismatches give duplicate84+30+83+15 plus249 lost units, hence766. Taking fresh5 removed a comparison whose result could have guided job1. This one policy comparison does not establish that every early-fresh policy is inferior.

All branch traces, both trees, fixed protocol, source hashes, lower-proof predecessors and unfavorable earlier results are retained. No native latency benefit, human outcome, independent proof certification or FSE acceptance follows from these checks.

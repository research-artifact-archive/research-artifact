# Paper-to-artifact map

The detailed tables below are a historical map for the earlier zero-fee paper, *Compiling Optimal Retry Policies for Dependent Transformations*, preserved under `package/paper/`; their theorem numbers and old PDF hashes do not identify the current manuscript. For the current paper, *Retry Synthesis with Bounded Calls and Protected Work*, use [the charged claim map](charged/CLAIM_EVIDENCE_MAP.md), [research lineage](charged/RESEARCH_LINEAGE.md), [source semantics](charged/SOURCE_SEMANTICS_AND_PARTIAL_REPAIR.md), and [partial-repair compiler supplement](charged/PARTIAL_COMPACT.md). The current exact PDF/source identity is recorded in [paper/SNAPSHOT.json](paper/SNAPSHOT.json). Later supplements may precede their adoption in the manuscript.

The historical [theorem/checker guide](THEOREM_AND_CHECKER_GUIDE.md) maps inherited results, additional proof obligations, checker pseudocode, and the object returned by each old method.

## Reconstruct the tables and denominators

Run from the repository root:

```sh
python3 -B tools/reproduce_tables.py
python3 -B tools/reproduce_tables.py --json
```

This read-only command uses JSON/JSONL records and file hashes. It imports no scientific solver and launches no experimental workers. It checks unique IDs, complete recorded unit coverage, expected/observed native metadata, per-policy worst-case witnesses, layout agreement, primitive root agreement, and controller byte bindings. The JSON form lists every incomplete unit and the source hashes used. Run `python3 -B tools/verify_release.py` to verify the complete distribution inventory too.

| Paper result | Fixed input and raw evidence | Aggregation and expected output |
|---|---|---|
| Table 1, pp.14–15 | `package/data/native/INPUTS.json`, `RAW.jsonl`, `SUMMARY.json`, `COMPARISON_ANALYSIS.json` | Maximize observed total weighted work within each policy/layout cell; verify both layouts agree; remove the four separately declared controls and count each of 48 cases × four budgets once. This yields 192 roots. |
| Table 2, p.16, B=1 | `package/data/extended/b1_constraint_comparator_01/benchmark01/` plus `screened01/BENCH_RAW.jsonl` | CP-SAT 78/0, screened DP 68/10, all-budget hybrid 53/25 SUCCESS/TIMEOUT. The earlier subset DP remains separately recorded at 56/22. |
| Table 2, B=2 | `package/data/extended/b2_contingent_comparator_01/benchmark01/` | CP-SAT 48/0, screened DP 48/0, all-budget hybrid 46/2 SUCCESS/TIMEOUT. |
| RQ1 complete primitive, pp.13–14 | `package/data/semantic/PLAN.md`, `DENOMINATORS.json`, `INPUTS.json`, `RAW.jsonl` | 4,232 authored priced inputs; 21,160 budgeted roots; 1,220,680 states; 9,239,600 actions; 12,551,856 outcome edges; 68,520 policy cells. |
| RQ1 native correspondence, p.14 | `package/data/native/PLAN.md`, `INPUTS.json`, `CASES.tsv`, `INPUTS.tsv`, `RAW.jsonl`, `MATH_VALIDATION.json` | All 19,644 recorded paths agree on the saved expected numerical and trace fields. This is not enumeration of all Java schedules. |
| RQ3 original 87-input scale, p.15 | `supplement/history/dependency_scale_01/` | 174 method units: construction 78 success/9 timeout; checking 74 success/4 timeout/9 `NOT_RUN` because construction did not succeed. |
| RQ3 57-input hybrid and later checker, p.15 | `supplement/history/dependency_hybrid_01/` and `dependency_hybrid_check_02/` | Preserve both original construction/checking rows and the separate later checks. A later result does not replace an old timeout. |

Table 1 rows `(hybrid smaller / equal / larger; maximum reduction)` are:

| Comparator | Counts | Maximum total-work reduction |
|---|---:|---:|
| Best fixed order with adaptive modes | 2 / 190 / 0 | 2.08% |
| Lookahead, fast on ties | 18 / 174 / 0 | 12.50% |
| Lookahead, protected on ties | 30 / 162 / 0 | 13.64% |
| Exact cached fallback | 138 / 54 / 0 | 76.74% |

Reduction is `(comparator - hybrid) / comparator`, including normal work. Both fixed-order improvements are the same case `native-final-47`, at budgets 2 and 4: abstract totals 47 versus 48 and 61 versus 62. These are two conditions, not two independent applications. Its controller is `package/data/native/artifacts/native-final-47.json` with SHA-256 `49e499a30ba901e3dcd034c7aca583b76dff1fe87e9ad02923df6e0443fe3323`; its deployment profile is `profiles/native-final-47.tsv`, SHA-256 `04d4688d7c4ed4fa67675cbbb1ace08ca21cbf49b01ae46057e0b1148022addc`.

Table 2 displays 378 method units but the artifact retains all 456 historical units: 234 original B1, 78 later screened B1, and 144 B2. The extra 78 are the earlier subset DP, not dropped observations. Existing controller files on a timed-out run do not make it a successful checked run. The three B1 `four_chains-32-*` timeout runs and both B2 `composed-5-disjoint-*` timeout runs that retain controller files remain timeouts.

## Replay the core semantic and native results

Use an assertions-enabled Python 3.10+ on a POSIX system for the older semantic harness, which uses `SIGALRM`. The native stage additionally requires a Java 17 JDK. Output directories must be new and outside `package/`.

```sh
python3 -B package/reproduce.py semantic --out work/semantic-full
python3 -B package/reproduce.py native --out work/native-full
python3 -B package/reproduce_extended.py bench1 --out work/b1-recorded
python3 -B package/reproduce_extended.py bench2 --out work/b2-recorded
```

For an explicit JDK, add `--java /path/to/java --javac /path/to/javac` to the native command. These paths refer to the reviewer's installation. The original JDK runtime is not redistributed and was not independently rebuilt from the cited OpenJDK source.

`semantic` recomputes all 4,232 retained inputs and compares root values, numerical fields and controller hashes. The input grid consists of forward-edge subsets on one, two and three jobs, with eight cost/premium pairs per job: `8 + 2*8^2 + 8*8^3`. It retains redundant-edge descriptions separately; it is not the universe of all labeled DAGs. Five budgets, 0 through 4, give 21,160 roots. There are 584 empty-edge regressions and four dependent preflight overlaps. The 25 separate control cases (one valid, 24 malformed) are not additional final inputs.

Join semantic `INPUTS[].id` to `RAW.input_id`, then inspect `roots[]`. Serialized controllers are `artifacts/<input_id>.json`, with `artifact_bytes` and `artifact_sha256` in each raw row. Ordered and ideal routes contribute 2,936 and 1,296 successful inputs respectively.

`native` compiles the authored Java harness and replays the exact saved path set, checking outputs, action traces, captured parent seeds, generations, work, writes, and policy maxima. This is stronger than printing a saved summary, but does not explore additional Java interleavings. Fresh replay timings are not substituted for the original performance observations. Original native preparation took 5.033 s; compile/execution was recorded jointly as 1.542 s, with no separate original phase times.

`bench1` and `bench2` inspect the complete historical status partitions and check 255/142 successful requested-budget policies. They do not rerun cold performance experiments, timeout units, or every all-budget Bellman certificate. Optional solver-based checks are described in `package/history/v4/README.md` and require OR-Tools. CP/DP return a requested-budget solution; the hybrid constructs an all-budget artifact. Their output and trusted-checking scopes differ.

## Native input and path selection

The generator seed is `202609080250`. The 48 core cases are sizes 3/4/5 × two price/order strata × eight cases. Each uses budgets 0/1/2/4, distinct and colliding bin layouts, and five policies. The generated cases retain all 397 topological orders. The fixed-order comparator chooses its best order separately for each initial budget and adapts modes within that order.

For each core policy/root, the preparation code recursively enumerates every success/failure outcome path allowed by that policy and residual budget, visiting success before failure. A protected action completes the job without a failure branch; an unprotected success completes it, while an affordable failure leaves it unfinished and decreases the budget. The resulting action/outcome paths are serialized for both layouts. They include the policy's abstract worst-case witness. This covers the finite abstract policy path set, not arbitrary thread timing or all Java executions. The two parent-postwrite controls use only their first generated path under each layout and are identified separately.

| Path group | Count |
|---|---:|
| Core hybrid | 4,640 |
| Fixed order | 4,686 |
| Lookahead fast | 4,858 |
| Lookahead protected | 4,390 |
| Cached fallback | 1,066 |
| Parent-postwrite controls | 4 |
| Total | 19,644 |

The core has 384 layout cells and 1,920 policy cells; controls add two cases and four layout cells. `INPUTS.json` stores each unit's `id,case,cell,kind,layout,budget,order,outcomes,actions,postwrite,expected`. Join its `id` with `RAW.jsonl`. `CASES.tsv`, `INPUTS.tsv` and `profiles/` are the actual serialized Java inputs. Preparation, generation, freeze and class-hash receipts are in `supplement/history/final_evaluation_dag_native_01/`; see the supplement README for projections and limits. The ordered parent-postwrite control repeats a development vector; the 48 core vectors do not.

## Later compilers, checkers, and cost studies

Use `package/reproduce_latest.py` and `package/reproduce_basis.py` as described in the package README. They do not include the core evaluations above.

| Evidence | Historical denominator and result | What its replay does |
|---|---|---|
| `fixed_order_profile_02/semantic01` | 24,029 semantic units; 63 controls | Recompute retained fixed-order values and controls. |
| `fixed_order_profile_03/semantic01` | 44,838 shared-checker cases and controls | Check the later implementation on retained cases. |
| `paired_chain_hardness_01` | 19,786 reductions | Recompute the retained reduction checks; the theorem is weak binary-price hardness. |
| `fixed_order_profile_02/scale01` | Old hybrid 36/24 and persistent plus first checker 42/18 success/timeout, each out of 60 | Preserve all 120 original outcome rows. |
| `fixed_order_profile_03/scale01` | Persistent plus changed checker 54/6; all 60 constructions completed | `scale` validates all outcome counts and saved construction hashes, then checks 54 successful certificates. |
| `sweep_pipeline_01/run01` | 45/3 success/timeout on 48 inputs | `pipeline` checks 45 saved successes and retains all three construction timeouts. |
| `linear_slope_bound_01/run01` | 17,656 algebra units, 4,355 copied certificates, 64 tight chains, two controls | Basis-only replay, including 128,116 stored curves. This is not replacement full Bellman certification. |

Paths in this table are relative to `package/data/extended/`; executable counterparts are under `package/src/`. `package/ALIASES.json` resolves deduplicated logical artifact/input files without removing outcome rows. A full latest replay checks 88,830 retained units, and a full basis replay checks 22,077. Quick modes are samples.

Use each historical replay's matched checker. `package/retry.py check` is the current dispatcher interface, not a universal checker for every earlier schema/route; for example, a valid historical ideal certificate may correspond to a case now dispatched to a persistent route. Generated persistent certificates have the stated efficient shared-subtree checking bound; arbitrary valid but differently shared certificates may be slower.

All elapsed-time comparisons retain the stated original limits, initial construction costs, and incomplete units. Across different runs they are descriptive, not a simultaneously randomized timing comparison. None of these counts establishes real-world prevalence or elapsed-time improvement.

## Earlier comparisons, refutations, and selected examples

The following previously omitted histories were added in the publication completion update. They are additional public access to existing observations, not new evaluations. `tools/reproduce_tables.py --json` verifies their complete input/raw ID coverage and partitions without executing old benchmark drivers.

| Paper discussion | Public history | Full retained partition |
|---|---|---|
| Independent PRISM/AND-OR comparisons | `supplement/history/primitive_scale_01/` | 130 planned/recorded units: 84 SUCCESS, 37 TIMEOUT, five FAILURE, four INVALID. |
| Earlier independent screened DP | `supplement/history/native_price_scale_01/` | 432 units: packing 144/0, ordered saturation 132/12, screened order 137/7 SUCCESS/TIMEOUT. |
| Divisibility-screened extension | `supplement/history/native_price_scale_supplement_01/` | 144 units: 140 SUCCESS, four TIMEOUT. Original comparisons remain separate. |
| Broader charged-acquisition refutation | `supplement/history/primitive_rmw_02/` | 384 completed inputs, 2,688 budget comparisons, five inputs with lower primitive cost; `fractional-0040` at budget two gives 242 versus 243. All five witnesses and raw state/action records remain. |
| Four-job family and minimum-size argument | `supplement/history/adaptivity_gap_search_01/` | 12,288 search records and 30 selected scalar checks/365 roots, with `FAMILY_PROOF.md` and the author-side proof disposition. These are exploratory/selected results, not additional final-evaluation roots. |

The complete common-price grids are already in `package/data/extended/critical_exposure_01/` and `package/data/extended/critical_exposure_02/`: 27,105 plus 66,560 successful records, with seven strict-gap inputs. The selected simplified example and its 746 native paths remain in `package/data/extended/critical_exposure_operational_01/`. The main final evaluation's 192-root denominator is unchanged.

Preparation receipts retain their original source hashes, even when public copies project workstation paths. The supplement provenance records both original and public hashes. In particular, the older PRISM scale preparation read an extra guard input registry that its historical manifest did not bind. This is an original limitation, not a provenance claim repaired by publication. Runtime installations and private raw assistant correspondence are excluded; historical source drivers are for inspection and are not promised to execute in the public directory layout.

Workflow supplement: `charged/WORKFLOW_REPAIR.md` maps the unpriced DAG criterion, positive-toll bounds, history-dependent policy certificates, and measured arrival-count analysis to stages32--33. Paper129 predates these additions; the next fixed PDF will cite the immutable evidence commit.

Local/shared-cap supplement: `charged/CAP_CONTRACTS.md` maps local/shared cap formulas, the full-kernel toll sensitivity bound, and per-update native comparisons to stages34--35. Paper129 predates these additions; the next fixed PDF will cite the immutable evidence commit.

Fixed paper137 cites evidence commit `7e93190645f2f16f21539ad8bcb32404722ca294`. Its central whole-kernel cap/toll and workflow repair claims map to `charged/CAP_CONTRACTS.md` and `charged/WORKFLOW_REPAIR.md`; the new timing figure maps to per-update analysis, not the earlier arrival data. Supplement descriptions referring to paper129 describe that historical predecessor.

One-job minimax regret: `charged/SINGLE_JOB_REGRET.md`, stage36, supplements the policy-specific bound in paper137. The next fixed paper will cite this immutable evidence commit.

Fixed paper140 cites evidence commit `c49ae8bc180c17f5283cef9444324d3de3457ae8`. Its cap/toll claims map to `charged/CAP_CONTRACTS.md`, exact one-job minimax loss to `charged/SINGLE_JOB_REGRET.md`, and repair/workflow claims to `charged/WORKFLOW_REPAIR.md`. Figure3 maps to per-update timing analysis; Figure2 explains an indistinguishable repair prefix. Supplement descriptions referring to paper129 describe that historical predecessor.

Paper146 refines the state/history/gate and inspection definitions, the within-budget failure witness and the Java source assumptions. `charged/INTERFACE_GUIDE.md` relates the two games to the existing solver scopes. Theorem formulas, native observations and scientific worker/input/outcome bytes are unchanged from paper140. The prior full standard36 replay remains tied to evidence commit `c49ae8bc180c17f5283cef9444324d3de3457ae8`; this document update is not a new replay or new experiment.

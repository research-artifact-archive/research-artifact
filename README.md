# Retry Synthesis with Bounded Calls and Protected Work

Anonymous research artifact for the paper of this title. The package contains the implementations, authored inputs, per-unit outcomes, controllers, certificates, traces, and supporting proof documents used in the paper. It includes unfavorable results and the full recorded denominators. This is an author-provided artifact; publication is not independent certification or evidence of acceptance.

## Charged-call revision

The [charged supplement](charged/README.md) adds the current three-mode compiler, mixed-price cursor reduction, native Java integration, Deephaven source case, and complete retained outcomes. See its [claim map](charged/CLAIM_EVIDENCE_MAP.md), [theory guide](charged/THEORY_AND_IMPLEMENTATION.md), and [theorem-by-theorem research lineage](charged/RESEARCH_LINEAGE.md). The [resource extension](charged/RESOURCE_BOUNDARIES.md) adds exact call-cap/protected-work bounds, a sharp price ratio for independent jobs and three native counter studies, including one policy that needs no writer-budget input. The preceding zero-fee package remains unchanged.

```sh
git clone https://github.com/research-artifact-archive/research-artifact.git
cd research-artifact
python3 -B tools/verify_release.py
python3 -B charged/reproduce.py all --out work/charged-full --timeout 300
```

Use Python 3.10 or later with assertions enabled. The thirty-three standard stages use the standard library and replay saved evidence; they do not rerun the timing campaigns as fresh measurements. Optional Java and native Deephaven commands are in the supplement. It adds about 2.0 GB of stored evidence, including two losslessly compressed input ledgers. No prices or finite write/update budget are inferred from applications. The universal resource policy needs no B input; scalar minimax and Deephaven guarantees retain their supplied-budget conditions. The [charged manuscript](paper/main.pdf) cites the immutable evidence commit. The preceding immutable evidence commit ec02a7a passed all 17 then-current standard stages. The [bounded-source extension](charged/BOUNDED_SOURCE.md) adds four stages, the guarded-tail counterexample/refinement, controlled blocking and all Roslyn source outcomes; its fresh public checkout passed all 21 then-current stages, the guarded-tail Java replay and a fresh Roslyn source build. The [suffix certificate](charged/SUFFIX_CERTIFICATE.md) adds exact feasible choices, complete positive/adverse comparisons and stage 22; its fresh public checkout passed all 22 standard stages and re-executed all 20,594 suffix Java paths with byte-identical raw output. Earlier unchanged sources passed all five optional JDK17 native stages and all 372 native Deephaven records; see the [reproduction receipt](REPRODUCTION_20260909.json). These are author-side fixed-evidence replays.

The [source-semantics and partial-repair extension](charged/SOURCE_SEMANTICS_AND_PARTIAL_REPAIR.md) adds five stages: 592 event/state semantic records, 55 reentry processes with four retained TIMEOUTs, all 5,664 independent-arrival units, two exact partial-repair studies and 96 compiler-dependency/snapshot cases. It includes a guarded source-rebase comparator and a fresh native rebuild helper. Publication does not convert full-transform counts into elapsed-time or total-work guarantees. Its exact public checkout passes all33 standard stages; source rebuild and compiler-projection receipts are in [September10 reproduction](REPRODUCTION_20260910.json). Its preceding exact public checkout passed all27 then-current standard stages; source rebuild and compiler-projection receipts are in [September10 reproduction](REPRODUCTION_20260910.json).

## Preceding zero-fee package

Use Python 3.10 or later with assertions enabled. The standard-library checks need no package installation or network access. The checkout contains approximately 1.5 GB of uncompressed data and more than 100,000 files.

```sh
git clone https://github.com/research-artifact-archive/research-artifact.git
cd research-artifact
./reproduce.sh portable
```

The command verifies release hashes and the frozen package, then replays small known-input checks of the latest compiler and supporting-line basis. It writes fresh results under `work/`. A quick check is not the full evaluation and does not replace earlier outcomes or increase scientific sample counts. To obtain an immutable version, check out the commit cited in the paper before running it.

- [Current charged paper](paper/main.pdf) and [source/build information](paper/README.md); the [preceding zero-fee paper](package/paper/main.pdf) remains preserved.
- [Compiler usage and complete latest replay](package/README.md).
- [Evidence index](package/EVIDENCE_INDEX.md) and [paper-to-artifact map](PAPER_ARTIFACT_MAP.md).
- [Zero-fee theorem attribution, checker pseudocode, and returned objects](THEOREM_AND_CHECKER_GUIDE.md).
- [Earlier stages and dependency requirements](package/history/v4/README.md).
- [Rights and provenance](NOTICE.md).

The `package/` directory is the byte-preserved version-5 snapshot. Its historical README and paper describe their *pre-publication* local status; the current charged paper in `paper/` cites its separate public evidence commit. Prior package versions, metadata, aliases, projections, and negative outcomes retain their original meaning. The [publication supplement](supplement/README.md) adds preparation provenance, complete earlier comparisons, charged-acquisition refutations, and the constructive-gap search. The public entry points and this README are an additional distribution layer.

READMEs archived under `package/history/` describe their original package roots. Their instructions to run “from this directory” do not refer to those archive subdirectories. In this distribution, use the repository-root commands in the paper-to-artifact map, or run the historical `reproduce*.py` commands from `package/`.

## Run the compiler

Create an input such as `{"cp":[[3,2],[1,4]],"edges":[[0,1]]}` in `work/case.json`, where each pair gives failure cost and protection premium. Use a new output path:

```sh
python3 -B package/retry.py compile --input work/case.json --out work/controller.json
python3 -B package/retry.py check --artifact work/controller.json
python3 -B package/retry.py query --artifact work/controller.json --budgets 0 1 2 1000000000000
```

The compiler assumes the mathematical retry contract in the paper. It does not infer costs, a write budget, or contract compliance from arbitrary concurrent code. Exact dispatch uses cost-compatible packing, a persistent unique-order representation, or the general ideal compiler. A supplied serial order on a branching DAG certifies that restricted order only. The general route may require exponentially many residual sets.

## A counted-work cap decision

Replay the four-job example from the introduction through the public compiler:

```sh
python3 -B tools/work_cap_example.py --out work/work-cap-example
```

For failure budget two and normal work 16, the checked adaptive policy has worst total work 24. The script enumerates all three legal fixed orders and compiles optimal adaptive modes within each; all three have worst total work 26. Thus the declared counted-work cap 25 can be met by the adaptive policy and by no fixed serial retry order. The primitive theorem rules out an improvement below 24 by retention or batching under its contract. This is a replay of the existing constructed example, not an elapsed-time result. The output directory preserves each controller and exact CLI response.

## Full retained-result replay

Reconstruct both paper tables and full recorded denominators with `python3 -B tools/reproduce_tables.py`. Use new output directories for each replay invocation. The following two commands replay 110,907 retained units; this count is not a new evaluation population:

```sh
python3 -B package/reproduce_latest.py all --out work/latest-full
python3 -B package/reproduce_basis.py all --out work/basis-full
```

The older entry points cover complete primitive semantics, native Java correspondence, comparisons, budget queries, and the general sweep checker. Their exact workflows are in the paper-to-artifact map. Java stages require a Java 17 JDK; optional constraint-programming replays require the recorded OR-Tools dependency. Saved timeout experiments are inspected with their original outcomes and are not automatically rerun. Timing observations from different runs are not a randomized performance comparison.

All inputs are authored. The evidence establishes bounded semantic checks and properties under the stated contract, not application prevalence, elapsed-time improvement, human benefit, or correctness of every possible Java execution.

The [compact partial-repair supplement](charged/PARTIAL_COMPACT.md) adds stage28, an exact competitive-threshold compiler, a monotone-profile acceleration and all384 original/changed-version process outcomes, including all six earlier timeouts. This solves a separate partial-repair objective; it does not strengthen the whole-kernel theorem or calibrate Roslyn repair costs.

The [objective and batch extension](charged/OBJECTIVES_AND_BATCH.md) adds stages29–30: exact additive/toll recomputation and all saved batch-rebase native/arrival outcomes. Timing improvements are not established.

[Document-state guard supplement](charged/DOCUMENT_GUARD.md) adds stage31: all fixed native projections and the four changed resource rows. No new timing samples.

[Workflow and arrival-count supplement](charged/WORKFLOW_REPAIR.md) adds stages32--33: fixed DAG equations, checkable policy thresholds, and reconstruction of foreground-period publications from existing native timelines.

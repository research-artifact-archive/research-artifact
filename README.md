# Compiling Optimal Retry Policies for Dependent Transformations

Anonymous research artifact for the paper of this title. The package contains the implementations, authored inputs, per-unit outcomes, controllers, certificates, traces, and supporting proof documents used in the paper. It includes unfavorable results and the full recorded denominators. This is an author-provided artifact; publication is not independent certification or evidence of acceptance.

## Start here

Use Python 3.10 or later with assertions enabled. The standard-library checks need no package installation or network access. The checkout contains approximately 1.5 GB of uncompressed data and more than 100,000 files.

```sh
git clone https://github.com/research-artifact-archive/research-artifact.git
cd research-artifact
./reproduce.sh portable
```

The command verifies release hashes and the frozen package, then replays small known-input checks of the latest compiler and supporting-line basis. It writes fresh results under `work/`. A quick check is not the full evaluation and does not replace earlier outcomes or increase scientific sample counts. To obtain an immutable version, check out the commit cited in the paper before running it.

- [Paper snapshot](package/paper/main.pdf) and [source](package/paper/main.tex).
- [Compiler usage and complete latest replay](package/README.md).
- [Evidence index](package/EVIDENCE_INDEX.md) and [paper-to-artifact map](PAPER_ARTIFACT_MAP.md).
- [Theorem attribution, checker pseudocode, and returned objects](THEOREM_AND_CHECKER_GUIDE.md).
- [Earlier stages and dependency requirements](package/history/v4/README.md).
- [Rights and provenance](NOTICE.md).

The `package/` directory is the byte-preserved version-5 snapshot. Its historical README describes its *pre-publication* local status; this repository supplies public access to that same snapshot. The included paper snapshot likewise predates this release and its Data Availability paragraph will be superseded by the revised paper. Prior package versions, metadata, aliases, projections, and negative outcomes retain their original meaning. The [publication supplement](supplement/README.md) adds preparation provenance, complete earlier comparisons, charged-acquisition refutations, and the constructive-gap search. The public entry points and this README are an additional distribution layer.

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

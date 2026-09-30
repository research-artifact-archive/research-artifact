# Use FG-DUCS

Follow the [build, run and screenshot walkthrough](../README.md#use-the-tool).

- `source/`: baseline MTSA/FG-DUCS source, tests and resource files.
- `models/`: inherited FSP examples and 27-contract families.
- `build.py`: build baseline or E1/E2/E5 in a fresh workspace, fetching verified upstream dependencies.
- `run.py`: run one finite JSON contract and create a local report. Canonical finite models are in `../results/granularity/e6/`.
- `view_result.py`: render a saved result/certificate as searchable, offline HTML.

The source is a research prototype. See [input assumptions](../docs/INPUTS.md), [LICENSE](../LICENSE) and [NOTICE](../NOTICE). Runtime adapters and real deployments are outside the supplied implementation.

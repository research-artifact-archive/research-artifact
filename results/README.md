# Evidence by question

The [main README](../README.md#results-and-interpretation) gives all principal outcomes and their limits before you open raw files.

| Question | Browse | Evidence available |
|---|---|---|
| Why can local updates and separate requirement boundaries matter? | [granularity/e6](granularity/e6/) | All family versions, generators, inputs, raw results, certificates, independent checks, traces and controls |
| Do inherited contracts already show a granularity separation? | [ablation](ablation/) | E1 54 null comparisons; E2 pruning/full-construction comparison, separate Mac/Xeon data |
| What happened in the preliminary and restricted-transfer tests? | [granularity](granularity/) | E4 original/corrected fixtures, E4.3 assessment, E5 initial-only transfer diagnostics and deadline-unexecuted jobs |
| What is the budgeted solver performance? | [performance](performance/) · [generated tables](../paper/source/build/generated/) | Fixed/scaling analyses, configurations and current ext1–7 raw data |
| How do the formal correctness tests behave? | [correctness](correctness/) · [formal-witnesses](formal-witnesses/) | Derived expectations, raw jobs, invalid-input controls and witness/diagram checks |
| What are the initializer and endpoint limitations? | [initialization](initialization/) · [supplement-checks](supplement-checks/) | Residual coverage, frontend lookup, completion ranks, quiescent-goal and load-target checks |
| How big are the declared contracts? | [contract-sizes](contract-sizes/) | 27 source-derived contract counts, scripts, CSV and TeX |
| What does the different-objective Legacy reference mean? | [legacy-fidelity](legacy-fidelity/) · [legacy-industry](legacy-industry/) | Fidelity/projection analysis and static product checks |
| Can one different contract repair the Industry case? | [contract-repair](contract-repair/) | Separate variant, all-root ranks, original losing entries and repair analysis |
| Where are the large original logs? | [archives](archives/) | Self-contained lossless raw parts, restored and verified by `reproduce/materialize.py` |

Development inventory and supplementary performance material are preserved in `inventory/` and `supplement-performance/`. Files containing old workspace paths are read through the compatibility workspace. Scientific counts use the final indexes, not counts of every historical directory.

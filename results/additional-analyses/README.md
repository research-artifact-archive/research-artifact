# Additional saved-evidence analyses

The canonical scripts, copied inputs and recorded outputs accompany the manuscript in [`paper/source/evidence/`](../../paper/source/evidence/README.txt). They extend the analysis of existing measurements; no synthesis or performance experiment is rerun. All original unfavorable results remain in their existing result directories.

From the repository root:

```sh
python3 -B reproduce/check_added_analyses.py --output work/added-analyses
```

Python 3 standard library only. Choose a new output directory. The command checks the copied inputs against this archive, recomputes the three analyses, replays their controls, compares all output fields (except temporary directory names), and checks that distributed evidence remains unchanged. It is also included in `reproduce/check.py`.

| Analysis | Script and inputs | Recorded results | Scope |
|---|---|---|---|
| Railcab activation | [Directory](../../paper/source/evidence/railcab_saved_activation/) | [Analysis](../../paper/source/evidence/railcab_saved_activation/analysis.json), [controls](../../paper/source/evidence/railcab_saved_activation/negative_controls.json) | Two policies, 22 old-entry vectors each, 21 NEW starts; one shared post graph. Saved entry vectors are assumed, not independently decoded runtime activations. |
| Command observation and reset | [Directory](../../paper/source/evidence/command_observation/) | [Analysis](../../paper/source/evidence/command_observation/analysis.json), [controls](../../paper/source/evidence/command_observation/negative_controls.json) | All 46 source positions, 138 variant occurrences and 1,587 lookup cells. The 357 error-to-safe reset projections are retained; cells are not actual starts. The restricted parser and language checker are reused. |
| Saved Threads serialization | [README and script](../../paper/source/evidence/threads_saved_serialization/README.md) | [Summary](../../paper/source/evidence/threads_saved_serialization/output/summary.json), [all outputs](../../paper/source/evidence/threads_saved_serialization/output/) | Ten related backpressure policies; 620 entry occurrences; identity transfers, identical OLD/NEW components, empty requirements and precedence. All 50 corruptions are rejected. No general converter, synthesis-speedup or runtime claim. |

Railcab replays one positive and three negative controls; command observation replays four negative controls. Threads produces fourteen byte-identical output files, including ten expanded policy graphs. The saved saturated-offer LOSS cases and other excluded measurement populations remain unchanged and do not enter this analysis cohort. Static disassembly text records an earlier inspection; the reproduction command does not execute the experiment JAR.

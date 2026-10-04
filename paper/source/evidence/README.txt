Supplementary saved-evidence analyses

These analyses accompany Technical Appendix F.2 (command observations) and
F.3 (two saved Railcab policies). They read copied archived inputs. They do
not run synthesis, execute a controller or measure performance. Python 3 and
its standard library suffice. The source parser and monitor-language checker
are reused from the archived artifact, not independently implemented here.

Each directory contains its script, copied inputs, analysis.json, a negative-
control script and negative_controls.json. The disassembly text records static
inspection of the experiment JAR; the JAR is not redistributed here. That
inspection supports the stated decoding/command rules, not general compiler
or runtime correctness.

From the manuscript source directory, using a new output directory:

  mkdir -p /tmp/fgducs-evidence-recheck
  python3 evidence/command_observation/analyze_command_observation.py \
    --artifact-root evidence/command_observation/inputs \
    --output /tmp/fgducs-evidence-recheck/command-analysis.json
  python3 evidence/command_observation/test_negative_controls.py \
    --artifact-root evidence/command_observation/inputs \
    --output /tmp/fgducs-evidence-recheck/command-controls.json \
    --work-dir /tmp/fgducs-evidence-recheck/command-controls
  python3 evidence/railcab_saved_activation/analyze_saved_railcab.py \
    --artifact-root evidence/railcab_saved_activation/inputs \
    --output /tmp/fgducs-evidence-recheck/railcab-analysis.json
  python3 evidence/railcab_saved_activation/test_negative_controls.py \
    --artifact-root evidence/railcab_saved_activation/inputs \
    --output /tmp/fgducs-evidence-recheck/railcab-controls.json \
    --work-dir /tmp/fgducs-evidence-recheck/railcab-controls

Choose a fresh directory for a later recheck. The control scripts deliberately
alter temporary copies, retain their changed inputs and check that the original
inputs remain unchanged. Their output paths may differ across runs.

Command analysis covers 46 source positions / 138 occurrences and all 1,587
lookup cells: 900 non-error and 687 error cells. It retains the 357 error-to-safe
reset projections, not only the accepted cells. Cells are not observed starts.
Railcab analysis accepts 22 saved old-entry vectors in each of two policies,
checks all 21 NEW starts, and checks their shared reachable post graph of 70
states and 116 edges. These are not two independent post graphs. Neither
analysis validates general activation/fallback calls or platform execution.

Technical Appendix R presents the separate saved Threads policy expansion in
threads_saved_serialization/. Its README describes the ten-case cohort,
independently implemented standard-library checker, all 50 negative controls
and limits. Run from the manuscript source directory:

  python3 evidence/threads_saved_serialization/check_saved_serialization.py \
    --output /tmp/fgducs-threads-recheck

No solver or performance measurement is invoked.

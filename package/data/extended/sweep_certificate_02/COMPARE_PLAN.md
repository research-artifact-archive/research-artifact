# Fixed comparison of two certificate scanners

Exploratory performance comparison on the same 36 previously successful ideal
certificates. They are selected by the already fixed BENCH_INPUTS.json, not by
new-scanner runtime. The 9 ordered successes and 19 timeout records from the
original 96-unit comparison remain outside this new checker-only probe. No
constructor, failed/timed-out original unit, or new policy synthesis is run.

Each certificate is read and checked in a fresh Python 3.12.14 process once by
the previous shape-plus-full-Bellman scanner and once by the new shape-plus-
zero-coverage scanner with direct stored-policy attainment. There are 72 units. Alternate old/new and new/old order
by input index. Freeze source hashes, the 36 certificate hashes, exact unit
order, Python binary/version, arguments, and caps before execution.

Both methods hash and parse identical saved bytes and check the full Bellman
equation. Neither performs root-value queries or construction. Measure cold
parent-observed process time, worker import/read-hash-parse/check phases, and
process ru_maxrss. Cold cap 5 seconds, sampled RSS cap 1 GiB at 50ms intervals,
whole comparison cap 420 seconds; closeout begins Sep8 10:50 JST and all work
stops at 11:00. A shared-resource load effect is not controlled by this small
author probe; no speed or prevalence claim for a new input population follows.

Retain every SUCCESS/FAILURE/TIMEOUT/INVALID/NOT_RUN and the first result; no
exclusion or repeat. All paired successful certificates must be accepted and
report the same complete state count. Any verdict disagreement is a falsifier.
Report totals and ranges for both phases/cold times plus all statuses; do not
replace original timing records or extrapolate end-to-end solver completion.

Predecessor sweep_certificate_01 comparison remains unchanged. This evaluates changed code; the new scanner directly certifies stored-policy attainment as well as values. This adds a guarantee, which is disclosed in the comparison rather than treating the outputs as strictly identical.

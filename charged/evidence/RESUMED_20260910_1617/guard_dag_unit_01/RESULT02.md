# Fixed unit-guard DAG check02

All declared rows completed with no mismatch, exception, timeout or invalid input. The fixed run took66.61619770800462 seconds; this is checker runtime, not native kernel performance. Original input/checker hashes, all completed and started counts, and every raw row are in run02/RESULT.json and the compressed ledgers.

* Source graphs:3,208 labeled graph/k cases on3–5 vertices.1,809 have too few edges and map to a declared exact-height-two negative target.
* Nontrivial reductions:1,399 targets, maximum18 jobs; independent CLIQUE enumeration gives728 yes and671 no. Every joint-cap decision from the inherited unrestricted two-mode DAG Pareto DP agrees. That DP and the added-fee recurrence each visit1,419,390 states.
* Positive constructive policies:8,190 interpreted no-write or first-mismatch paths. Every order is topological, every execution completes in Q=n, and separate worst coordinates attain the constructed caps.
* General common-guard cases:675 declared DAG/work/guard combinations,46,998 order/mask policies,5,049 states in each recurrence. Every frontier agrees with complete order/mask enumeration, satisfies the first-coordinate candidate set and n²+1 bound, and translates correctly under heterogeneous all-call fees.
* All-call fee: the separate recurrence counts the fee on fresh/cached calls and on each cheap suffix call. Every nontrivial embedding uses d_i=1; every general case uses d_i=i+1. All complete frontier translations agree.
* Three fixed alterations are detected. Omitting cheap-suffix fees changes the v3-m7-k3 frontier. Removing precedence or omitting no-write protected load changes the v4-m7-k3 cap answer from no to yes. Full altered frontiers and detecting inputs are retained.

These are bounded author corroborations of the reduction, returned witnesses and fee recurrence. They are not asymptotic proofs, independent reproduction, a human study or evidence of native latency improvement. The pre-execution checker correction remains explicit: sealed v1 was unexecuted; v2 added the research deadline, accurate partial-completion accounting and an exact-height-two trivial target without changing the fixed graph population.

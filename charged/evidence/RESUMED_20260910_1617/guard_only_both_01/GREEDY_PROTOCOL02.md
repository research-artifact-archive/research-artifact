# Greedy improvement02: fixed validation

The read-only author critique supplied a faster common-g algorithm after fixed01 completed. This validates that new algorithm; it is not a retry or replacement of01. Inputs are the exact836 uniform cases from INPUTS01. Expected complete frontiers come from the already-saved unrestricted-mode results in run01/ROWS.jsonl.gz. For each threshold T in {Gamma} union {w_i+j*g>Gamma: j1..n}, compare greedy saved work to the independently implemented count DP, verify its actual subset cost, and collect a frontier. Require that frontier to equal the saved all-mode frontier. Also evaluate all43,565 uniform cap queries already recorded in CAPS01. Preserve all threshold and cap rows.

Greedy sorts w descending once. If k jobs are selected, choose the next i exactly when (k+1)*g+w_i<=T. Rank-wise domination of every feasible chosen subsequence proves both cardinality and saved-work optimality. This is an inherited scheduling selection idea specialized to the completion-program equivalence; no new general scheduling algorithm is claimed. Source attribution is recorded separately.

One additional deliberate control deletes the baseline threshold on N=1,w=1,g=0. It must miss the all-fresh frontier point. Candidate01 and its fixed checker ALREADY included0; the control demonstrates the importance of that baseline and does not assert an actual01 defect.

Hash-bind code, protocol, inputs and expected raw files before this new run. Limit60seconds. No native/timing sample, no changing01, all mismatches/controls/denominators retained.

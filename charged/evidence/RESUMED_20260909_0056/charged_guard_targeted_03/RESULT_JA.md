# Targeted exposed-guard search03

All511 newly perturbed inputs, comprising6643 all-U budget roots0..12, completed in40.70seconds with no full-game/three-mode gap and no violation of the independently derived Hflat/H-Bmu lower bounds. The explicit solver checked every reachable Bellman equation and selected-policy termination for each input. There were0FAILURE,0TIMEOUT,0INVALID and0NOT_RUN inputs.

The511 inputs are quarter-price perturbations of16 deliberately selected previously observed examples where retaining a failed-validation guard could improve a root-optimal action relative to forcing immediate resolution. This is targeted, outcome-informed exploration. It is not held-out sampling, proof of general equality, or evidence of deployment prevalence. All primitive and macro values, clipped-price values, graph sizes, action counts and source selection are retained. The prior43-versus45 intermediate-state counterexample is unaffected.

The author proof now establishes all-U equality for B<=1 and, at all budgets, when each job satisfies m=0 or p<=m. The general B>=2 case with an exceptional positive-m job remains unproved despite this negative counterexample search. See CHARGED_EXPOSED_GUARD_AUTHOR_REPORT_07.md and charged_callback_theory_01/EXPOSED_GUARD_ROOT_REVIEW_01.md for the separate mathematical arguments.

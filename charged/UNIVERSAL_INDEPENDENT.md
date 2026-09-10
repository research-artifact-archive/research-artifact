# The least total-work curve without a write-budget input

This extension concerns independent whole-kernel jobs with positive works, no free initial prepared result, and a universal call cap Q<=n+r. The policy must attain the optimal protected-work bound at **every** finite write budget. This is a specified simultaneous-protection contract, not the class of all terminating programs and not the unrestricted pointwise price of unknown information.

Sort works a1<=...<=an, let Omega be their sum and Top_m the sum of the largest m (saturated at n). The least worst-total-work curve is

```
F_r(B) = Omega + B*a_n                                      for B<=r;
         Omega + max_{1<=m<=min(B-r,n)} (r*a_(n-m+1)+Top_m)   for B>r.
```

One fixed policy attains the whole W curve and L(B)=Top_(B-r)+: take jobs in ascending order, prepare immediately before each cheap call until r such calls fail, then prepare immediately before every cached completion. It observes only cheap completion/failure and the fixed ordering; it needs no B input, cached Boolean, value, clock or cost counter. The lower bound permits the stronger observation contract. A target-only adversary cannot be forced to spend retries on cheaper non-target jobs. The proof uses a common paid start and charges the matching record of the zero-write continuation. The max over m is essential; it need not occur at the largest m.

The [full proof10](evidence/RESUMED_20260910_1617/joint_work_general_r_01/UNIVERSAL_INDEPENDENT_PROOF10.md) preserves the stronger-program lower bound, conditional policy-class comparison and saturated cases. The [scope proof11](evidence/RESUMED_20260910_1617/joint_work_general_r_01/UNIVERSAL_SCOPE_PROOF11.md) gives the all-DAG early-budget extension through B=r+1 and the10->1->1,r1,B3 counterexample: the DAG optimum33 exceeds the independent32. At r0 the least curve is Omega+Top_B on every DAG. Positive-r arbitrary-DAG least entire curves and intermediate-state uniqueness remain unproved. The [four-job observation counterexample](evidence/RESUMED_20260910_1617/joint_work_general_r_01/UNIVERSAL_OBSERVATION12.md) proves that cached-comparison erasure can cost work on a positive-retry DAG even under the universal contract: chain2->4->1->1,r1,B4 has visible minimum17 and erased minimum18. Independent-job saturation does not imply all-budget DAG independence. Separate W/L maxima may coincide or may require different plays.

Standard stage42 `universal-independent` recomputes the first-only fixed647 independent roots,34,814 policy paths and36 fixed scope roots. The full universal Pareto oracle and a separately expressed policy interpreter agree at every fixed coordinate, with zero failures/timeouts/exclusions. The retrospective117 independent roots and237 zero-retry DAG roots overlap in39 cases and are not new independent samples. The additional fixed observation study retains all8,672 erased finite policy trees across four roots and102,122 interpreted paths:4 admissible trees and8,668 with explicit protection violations. Its preexecution parser error and corrected source are preserved. Every previous arbitrary-chain/intermediate-continuation counterexample is retained.

Standard stage43 `universal-independent-native` reconstructs **all20,384 saved actual Java17 executions**, in10,192 cheap-wrapper pairs and512 curve groups containing2,464 budget coordinates. The policy has no B input and no cached-comparison observation. Every group attains its exact W/L/Q curves. The records include24,168 cheap failures,108,576 cached calls and4,092 executions with verified actual TreeBins. Twelve fixed checker corruptions are all rejected. Each selected1-bit gate actually executes an own-key fresh write on a separate writer thread before the foreground API call;0-bits issue no write. This matrix does not add multiwrite-gate, resize, arbitrary concurrent JMM or natural-arrival evidence. Every original writer executor terminates. The3.641-second compile/run duration is execution-management provenance, not a measured performance advantage.

```
python3 -I -S -B charged/reproduce.py universal-independent --out work/universal42
python3 -I -S -B charged/reproduce.py universal-independent-native --out work/universal43
```

Choose new empty output paths. Large JSONL files use lossless gzip transport, with both stored and decoded hashes in `PROVENANCE.json`; workers materialize the original decoded bytes before replay. Replay collects no new native measurement and is author-side reproducibility, not independent certification. Paper172 and all preceding payloads, denominators, negative results and judgments remain unchanged in this evidence release. A subsequent fixed paper may integrate this new theorem. No evidence here establishes deployment prevalence, strong novelty, operational importance or submission readiness.

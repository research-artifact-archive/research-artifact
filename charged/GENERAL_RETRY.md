# Exact total/protected-work frontiers with arbitrary retry slack

Current manuscript197 puts the least all-budget independent-work curve in Section4.1, supplied frontiers in4.2--4.3, changed call weight in4.4, program domination and recurrence in5, and observation erasure in5.2. Its Section7 added-cost complexity claims concern supplied B=1, Q<=n and are separate from the body-work retry results.

This extension adds corrected full-program domination at arbitrary retry allowance r, a complete polynomial independent-job frontier for every supplied B/r, and the all-DAG/output-only corollary when r>=B. The fixed common start charges every computed record. Fresh useful comparison writes invalidate the counterfactual matching record; stale failures are not charged again. Separate maxW/maxL are resource caps, not a combined objective or native-time prediction.

The complete proofs are [general-r domination](evidence/RESUMED_20260910_1617/joint_work_general_r_01/PROOF02.md), [independent and enough-retry frontiers](evidence/RESUMED_20260910_1617/joint_work_general_r_01/INDEPENDENT_PROOF07.md), and [simplified stopping policy with sharp valid-budget range](evidence/RESUMED_20260910_1617/joint_work_general_r_01/SIMPLIFIED_PROOF08.md). Original drafts, pre-correction text, protocols and adverse examples remain; author consultation is not an independent proof or novelty verdict.

Standard stage40, `general-retry`, recomputes all96,795 canonical/finite-retained cases;713 unknown-budget roots;10,842 one-write retrospective rows;33,804 distinct independent/enough-retry retrospective rows (1,998 and32,526 scopes overlap in720); both separately fixed independent-policy variants on the SAME13,850 inputs with540,230 paths each; and9,240 sharp-boundary cases with481,995 paths. Original check06 and simpler check08 have different policies and separate raw outputs. It verifies exact output hashes, including every retained path. Finite retained-state enumeration is only a bounded corroboration; the full program class is justified by the proof, not by enumerating it. The general positive-retry unknown-budget least curve remains unresolved.

Standard stage41, `one-retry-native`, reconstructs all12,224 SAVED actual Java17 executions. The policy has suppliedB1/r1 and observes cheap success/failure only. All6,112 replace/validation-only wrapper pairs agree; all176 groups attain their resource maxima. It retains304 cheap failures,1,056 cached calls,4,336 verified actual TreeBin executions,1,848 late writes explicitly unissued because their call position was not reached, and4,792 saved-output/final-live differences. Java source, full input population, original logs, checker, semantic projections and all extrema are included. This standard replay creates no new native timing samples. The original Java compile/run took2.214seconds for execution management, not a measured performance improvement. Resize, arbitrary concurrent JMM schedules and natural-arrival benefits are not established.

Run from the artifact root using Python3 with assertions enabled:

```sh
python3 -B charged/reproduce.py general-retry --out /tmp/general-retry-replay --timeout 300
python3 -B charged/reproduce.py one-retry-native --out /tmp/one-retry-native-replay --timeout 300
python3 -B charged/reproduce.py all --out /tmp/all41-replay --timeout 300
```

Choose a new empty output path. `charged/reproduce.py verify` checks the entire provenance manifest, including stored and decoded hashes for gzip transport. New JSONL files larger than8MiB are stored losslessly as `.jsonl.gz`; the standard worker materializes their exact original bytes in its output directory. The original scripts continue to use `.jsonl` names. Already-gzipped simplified paths remain byte-exact. No path/record is omitted by compression. All earlier39 stages, public paper163, old negative results and original work denominators remain unchanged during this evidence release. A separately fixed revised paper follows it.

Paper172 follows this evidence release and cites immutable evidence commit `90812054158ced9ae313240f9211ec5f61f51f1e`, whose fresh public checkout passed all41 stages. Its Section4 states the polynomial independent/sufficient-retry frontiers, Section6 the complete finite policy class, and Section8 the finite/native denominators. The additional unknown-budget independent-job formula and its later native matrix are not part of paper172 or this evidence commit.

Paper180 now includes the unknown-write-bound independent-job least total-work curve for arbitrary retry allowance, with its central proof in Section4.1. The chain counterexample limits extension to general positive-retry DAGs. Section6 and the output-erasure supplement distinguish visible comparison from output-only completion. Exact evidence commit `6ca1285673b758bf7706cbf8540237925435d6c2` passed all45 stages, including general-retry42--43 and Linux/guard44--45. This paper update preserves their scientific bytes.

Paper187 retains the central arbitrary-retry independent-job all-budget curve and proof in Section4.1, the general-program domination/recurrence in Section6, and the two-job visible/erased distinction in Section6.2. The complete zero-retry erased frontier and positive-retry witnesses remain here in the supplement. The later fully charged one-write NP-completeness statement is a different added-cost class.

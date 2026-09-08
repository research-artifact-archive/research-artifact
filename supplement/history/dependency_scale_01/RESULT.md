# DAG size exploration01 result

All174 planned units for87 fixed authored inputs were recorded in140.826seconds. Compilation:78 SUCCESS,9 TIMEOUT. Separate all-budget Bellman checking:74 SUCCESS,4 TIMEOUT,9 NOT_RUN because construction had not succeeded. No FAILURE/INVALID occurred. Each process had5seconds and sampled1GiB RSS limits. All timeouts, untouched controllers produced before checker timeouts, raw logs and command receipts remain saved.

The9 compilation timeouts cover every pricefamily of four disjoint chains of length12, fence24, and independent16. Checking alone timed out for chains_w4_l8_WIDE_P, random_layers_w8_l8_WIDE_P, independent12 SMALL andWIDE_P. Thus74/87 inputs have both successful compilation and completed full-budget identity checking;78/87 have completed construction. These denominators must remain distinct.

Successful construction reaches6,561 states and83,042 segments for32 jobs arranged as4 chains of length8 with large premiums. Construction+serialization for that case is1.550seconds and3,248,007bytes; its checker timed out, so it is not among the74 fully checked cases. The same graph with WIDE_C has6,561states/82,994segments,2,609,317bytes and1.289seconds, and its checker succeeds. The largest positive root run count observed is22. H6 (at most2n positive runs) has no counterexample among78 completed constructions; the9 unconstructed cases are unresolved, and no general bound has been proved.

Large numerical budgets do not automatically make a root nontrivial. At the fixed diagnostic budgets there are22 completed-and-checked roots with budget>10^10 and strict L<V<U, so the numerical study includes cases not solved by equality of these particular inexpensive bounds. This is a diagnostic, not a solver-speed or application-use claim. Every diagnostic's actual bound/order values are saved. The generic ideal compiler is deliberately inferior to the already known independent O(n log n) algorithm on independent templates.

RAW SHA2561df65500a4a9780cd6f37fd2fa482a64d9e265ad45812a190e54ce5262992487. The study is exploratory and authored; it is not a held-out workload population or fixed final evaluation.

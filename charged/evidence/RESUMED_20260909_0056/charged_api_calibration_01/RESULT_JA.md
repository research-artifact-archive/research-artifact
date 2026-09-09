# Native API calibration — retained adverse exploratory result

All72 fixed JMH cells succeeded in278.11s. All144 fresh forks and720 measurement iterations were retained; no timing cell was retried or removed. OpenJDK17.0.19/JMH1.37 and complete named wrappers were measured. This includes two cached-completion validation paths that were added before any timing output, following author review19. The superseded56-cell preparation is retained separately.

The fixed mean-cost model was representable in2/8 settings under the pre-fixed20% fit plus cached-path validation residual rule. Every direct inter-path residual t_fresh-max(validation callbacks)-t_prepare was negative. In the nonnegative fit every inferred p was0. This is not evidence of a measured positive lock premium, and the fitting criterion does not establish timing stability or a worst-case guarantee.

| Layout / payload length | Model fit max relative error | Inter-path residual ns | Fitted w/v/k/p ns | Representable |
|---|---:|---:|---|---|
|distinct-1|7.9%|-1.20|5.54/8.48/8.31/0.00|True|
|distinct-8|21.4%|-5.33|7.82/8.45/7.48/0.00|False|
|distinct-64|22.0%|-9.44|55.42/8.47/6.70/0.00|False|
|distinct-512|49.1%|-20.97|517.26/8.47/4.36/0.00|False|
|colliding-1|34.2%|-13.41|9.92/12.79/10.91/0.00|False|
|colliding-8|22.6%|-11.18|14.58/12.47/10.37/0.00|False|
|colliding-64|19.8%|-13.65|57.26/12.79/12.80/0.00|True|
|colliding-512|74.4%|-47.16|535.54/13.44/3.95/0.00|False|

The fixed sensitivity denominator was1152 two-job/budget/declared-weight roots.72 were evaluated within representable calibrated states;1080 were explicitly OUTSIDE_CALIBRATED_MODEL. No strict third-mode improvement occurred among the72. Only one payload length per layout was representable, so the eligible same-layout pairs had no heterogeneous sizes. This is a retained limitation, not a reason to remove the1080 or expand the20% tolerance after observing results.

The raw residual includes map.get, wrapper field assignments, different input reuse and different object lifetimes: preparation reads the original source and discards each output, while fresh/cached mismatch retains its output as next input. It is not an isolated measurement of critical-section overhead. The code isolates match/mismatch in separate JVMs and could have different JIT profiles from mixed workloads.2forks and600ms warmup per fork do not establish steady state; every fork/iteration value and drift diagnostic is in ANALYSIS01.json/raw JMH files. Some fork ratios are substantial. Small score differences must not be called statistically significant gains.

These results do not invalidate the declared-resource-price theorem or the source-instrumented operation-count comparisons. They fail to establish that the charged model accurately predicts elapsed CPU time in this wrapper family, or that the third mode improves such measured execution time. The external merit gap on practical nonzero-fee benefit remains open. Any changed calibration model, extra workload, uncertainty study or kernel redesign must be explicitly separated from this outcome, with a new rationale/input fixation; no in-place rescue of this result.

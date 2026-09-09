# Complete paired blocking results

Semantic check: 4320 measurement and 1440 warmup invocations SUCCESS; 17280 measured probes; 2160 measured pairs. All 5760 outputs match 12 independent Python sequential references. Twelve checker controls rejected after a post-outcome strengthening; original checker gap retained. No exclusions or retries.

All times below are microseconds. Difference = two minus three; CI is the descriptive paired bootstrap of the median (20000 resamples), not a tail bound. Each row pools 90 pairs from three JVMs. The per-fork range is the range of three paired median differences.

| scale | r | layout | two median | three median | paired difference | 95% interval | fork difference range |
|---:|---:|---|---:|---:|---:|---|---|
| 64 | 0 | same_bin | 30.730 | 29.958 | 0.855 | [0.270, 1.458] | [0.250, 1.312] |
| 64 | 0 | disjoint_bin | 3.896 | 3.854 | 0.043 | [-0.123, 0.209] | [-0.083, 0.064] |
| 64 | 1 | same_bin | 31.042 | 29.770 | 0.896 | [0.312, 1.333] | [0.291, 0.981] |
| 64 | 1 | disjoint_bin | 3.896 | 3.833 | 0.063 | [-0.042, 0.209] | [0.001, 0.146] |
| 64 | 2 | same_bin | 30.459 | 30.145 | 0.855 | [0.126, 1.542] | [0.084, 2.022] |
| 64 | 2 | disjoint_bin | 3.938 | 3.917 | 0.001 | [-0.167, 0.126] | [-0.084, 0.105] |
| 2048 | 0 | same_bin | 62.541 | 29.166 | 33.186 | [32.499, 33.957] | [32.584, 34.458] |
| 2048 | 0 | disjoint_bin | 3.542 | 3.605 | 0.021 | [-0.082, 0.125] | [-0.041, 0.042] |
| 2048 | 1 | same_bin | 61.623 | 28.980 | 33.376 | [32.666, 34.271] | [33.124, 33.999] |
| 2048 | 1 | disjoint_bin | 3.604 | 3.501 | 0.166 | [0.043, 0.395] | [0.064, 0.271] |
| 2048 | 2 | same_bin | 62.895 | 29.166 | 33.417 | [32.791, 34.187] | [32.896, 33.917] |
| 2048 | 2 | disjoint_bin | 3.708 | 3.521 | 0.209 | [0.123, 0.416] | [0.147, 0.314] |
| 65536 | 0 | same_bin | 884.083 | 29.396 | 855.355 | [852.646, 861.438] | [854.063, 859.583] |
| 65536 | 0 | disjoint_bin | 3.438 | 3.417 | 0.041 | [0.000, 0.106] | [0.001, 0.084] |
| 65536 | 1 | same_bin | 885.312 | 29.396 | 855.188 | [852.606, 858.979] | [853.397, 859.563] |
| 65536 | 1 | disjoint_bin | 3.502 | 3.417 | 0.290 | [0.085, 0.437] | [0.082, 0.376] |
| 65536 | 2 | same_bin | 884.646 | 29.021 | 854.812 | [853.293, 856.917] | [854.644, 856.605] |
| 65536 | 2 | disjoint_bin | 3.542 | 3.396 | 0.293 | [0.124, 0.561] | [0.084, 0.542] |
| 2097152 | 0 | same_bin | 26814.438 | 31.312 | 26784.500 | [26758.125, 26823.915] | [26778.230, 26789.499] |
| 2097152 | 0 | disjoint_bin | 3.833 | 4.041 | -0.291 | [-0.436, -0.062] | [-0.416, -0.062] |
| 2097152 | 1 | same_bin | 26825.499 | 31.188 | 26794.354 | [26762.345, 26808.521] | [26740.939, 26808.521] |
| 2097152 | 1 | disjoint_bin | 3.958 | 4.291 | -0.270 | [-0.499, -0.083] | [-0.459, -0.188] |
| 2097152 | 2 | same_bin | 26813.355 | 31.291 | 26781.314 | [26747.395, 26808.958] | [26756.856, 26807.645] |
| 2097152 | 2 | disjoint_bin | 4.042 | 4.125 | -0.061 | [-0.290, 0.104] | [-0.103, 0.042] |

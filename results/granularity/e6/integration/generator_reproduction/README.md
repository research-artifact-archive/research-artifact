# Frozen-generator reproduction check

Status: **PASS**. Completed at 2026-09-29T18:59:39+09:00. This checks regeneration only; it runs no solver or JVM and makes no new experimental measurements.

All **214 frozen JSON inputs across eight families**, plus **one PC2 FSP input**, reproduce byte for byte. No canonical-JSON fallback was needed. The 13 saved reference copies also match bytes. Exact per-input paths and original/frozen/regenerated SHA-256 values are in `input_comparisons.csv` and `report.json`; reproduced inputs are under `generated/`.

| Family | Inputs | Result | Unchanged generator API used |
|---|---:|---|---|
| Rolling | 70 | byte-identical | `rolling/gen_rolling.py: make(n,m,k)` |
| Canary | 30 | byte-identical | `canary/gen_canary.py: generate(n,m,grouped)` |
| Policy v2 | 2 | byte-identical | `policy/v2/gen_policy.py: model(coarse)` |
| DB-Rolling v2 | 4 | byte-identical | `db_rolling/gen_db_rolling.py: model(m,merged)` |
| Rolling+Audit | 4 | byte-identical | `fine_model` and `grouped`, consuming independently regenerated Rolling bytes |
| Threads | 40 | byte-identical | `threads/gen_threads.py: make(n,b,regime,grouped)` |
| Rolling scale | 40 | byte-identical | `rolling_scale/gen_scale.py`'s imported, unchanged Rolling `make` |
| Canary controls | 24 | byte-identical | unchanged `main`, with only in-memory output/reference-root globals redirected; consumes the regenerated Canary inputs |
| PC2 | 1 FSP | byte-identical | unchanged `gen_pc2.py: main`; only in-memory `HERE` redirected, original plant read without alteration |

The PC2 generator itself is in its frozen manifest. Its original plant SHA is `117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43`; the replay performs the existing prefix and erasure assertions and reproduces the saved final input exactly. This is not a new endpoint or synthesis run.

All default generator CLIs were avoided. Pure functions return models, serialized using the generator's original `json.dump(indent=2)` plus newline. Controls' original main has no pure constructor, so it reads the newly regenerated Canary data through an explicitly redirected root; its existing frozen-hash assertions remain enabled. The minimal `generated/canary/v1/build/frozen_manifest.json` is a **read fixture** containing original expected file hashes, not a new experiment freeze. PC2 likewise redirects only its destination directory; it still reads and validates the original plant.

A Python audit hook rejects any write outside this check directory and rejects child-process creation. Bytecode writing is disabled. The comparison checks all input filenames against each canonical frozen manifest, not merely a sample of schedule entries. Before/after comparisons cover **279 unique frozen files (361 manifest occurrences)**, all unchanged and matching their original frozen hashes. The fixed E1 JAR and original PC2 plant hashes match. The **2,532 raw files** retain the same file set, sizes, and nanosecond modification times. Raw preservation here uses these metadata plus the write guard; it is not described as a fresh full-content rehash. Guard violations: zero.

## Preserved checker failure and repair

`check_reproduction.py` is the first verifier version, preserved unchanged with `execution_failure.json`, its logs, and generated outputs. It successfully regenerated 190 JSON inputs and PC2, but its redirected Controls output parent was absent. The original Controls main calls `OUT.mkdir(exist_ok=False)` without `parents=True`, so Controls did not generate; the verifier then failed while trying to compare a missing reference copy. This was a **verification harness directory error**, not an input mismatch or a failed solver result.

`finish_reproduction.py` records the first attempt in `attempt01_failure_analysis.json`, creates only the missing scratch parent, invokes the **unchanged** Controls generator, and performs the complete final comparison. Earlier generated files are not overwritten or regenerated. The original generator, frozen inputs, configs, classes, raw files, manifests, JAR, and manuscript remain unchanged. Both verifier versions and the failed attempt remain available; these are create-only provenance scripts, not commands to rerun in the already populated directory.

`freeze_checks.json` records the original pre-execution checks; `freeze_checks_after.json` records all final hashes; `raw_metadata_before.json` preserves the raw metadata snapshot. `report.json` is the final authoritative result, with script and generator hashes. Generated scratch configs and the PC2 projection report are auxiliary outputs, not replacement campaign artifacts.

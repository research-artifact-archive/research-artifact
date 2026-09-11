# Executable residual safety interface in Java17

The [adopted Java filter](evidence/RESUMED_20260911_1123/java_residual_filter_01/v2/ResidualFilter.java) receives completed weights, mismatch credit, incurred protected body work, the proposed current weight and the public completion outcome. Its interface receives no future weights, DAG, total job count, write budget or runtime diagnostics. A fresh query uses a constant number of arithmetic/comparison operations. Completion updates use two linked complete binary heaps and O(log n) pointer/comparison operations. Allocation/GC latency is outside that bound; long overflow raises an exception and does not assert mathematical unsafety. Read the [implementation boundary](evidence/RESUMED_20260911_1123/java_residual_filter_01/IMPLEMENTATION_NOTES.md).

The initial PriorityQueue version passed the same semantic cases, but backing-array expansion did not support the requested strict single-update operation bound. Its entire attempt remains alongside the recorded [revision](evidence/RESUMED_20260911_1123/java_residual_filter_01/REVISION02.md). Repeating the fixed population does not create independent samples.

## Fixed evidence

There are498 filter operation sequences (486 from18 small roots and12 boundary cases), plus two heap-structure regression roots. The native integration has48 roots and996 complete paths, with31,892 events; every event and saved output agrees with a separately written sorting/transition interpreter. All Java execution statuses are SUCCESS; invalid-input, unsafe-fresh and overflow outcomes are expected API rejections and remain recorded. The final report and full initial/revised traces are included.

A six-job chain reaches completed weights(100,1),k=1,ell=1 and permits fresh weight2 while the prior whole-suffix rule refuses it. This establishes a strict safe-choice difference. All62 matched worst-body-work coordinates are equal to the same cheap phase followed by all-cached completion. All-fresh is also run, but it does not satisfy the same zero-write protected-work contract. The118 postpublication paths and118 double-write paths are subsets of the996 paths. They check saved-output persistence and distinguish observed mismatches from actual writes.

These are authored whole-kernel fixtures, not an actual application client, latency study, Java Memory Model proof, or validation of every concurrent interleaving. The filter itself is body-only; it does not implement heterogeneous fees. The native source/API correspondence remains conditional. No new performance benefit is inferred from the number of traces or the additional permitted action.

## Reproduction

The standard57th stage recomputes the Python reference from the fixed input and compares all saved Java events and derived records:

```sh
python3 -B charged/reproduce.py java-residual-filter --out work/java-residual57 --timeout 300
```

This stage runs no new native campaign and needs only Python3.10+. The separate [native reproduction commands](evidence/RESUMED_20260911_1123/java_residual_filter_01/REPRODUCE.md) compile the adopted v2 sources with the reviewer's Java17 in a fresh directory. Original execution supervisors retain their historical deadline; use the documented fresh commands for later reproduction. Some large stored JSON/JSONL files are compressed: decompress them to their adjacent original names in a fresh copy before running those commands. The standard stage creates such a decoded `fixed/` directory automatically. Original source/public/decoded hashes and author-path projections are in PROVENANCE.json.

The upstream JDK source excerpt is retained only in the private author record. SOURCE_PROVENANCE.json records its source archive and exact source hash; the excerpt is excluded from redistribution, as are compiled classes and Python caches. All89 authored source, input, trace, protocol and report files remain here. This supplement was initially outside manuscript216. Current manuscript219 integrates the Java component in Section9.1 and cites the verified combined57-stage evidence commit.

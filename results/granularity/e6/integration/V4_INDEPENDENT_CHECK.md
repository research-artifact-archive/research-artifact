# Independent check of the next anonymous snapshot

`check_v4_independent.py` only reads evidence. It never creates an anonymous copy, starts a JVM, reruns measurements, or imports the export builder/verifier. Its only write is a create-only JSON report directly under `integration/`.

The initial 395-Mac-trial source preparation passed in `v4_independent_preparation01.json` (that report identifies its exact helper SHA). A subsequent read-only code review requested two stronger future checks: the original PC2 three-job order and a full campaign/host/heap/budget/job-key join of the five-row comparison to the two original result tables. Those checks were added. Three Xeon trials were then received and explicitly authorized for separate acceptance, so the current helper also checks their receipt manifest and eight-row comparison. The original preparation remains historical; no preparation result claims to have checked a future v4 snapshot, and v3 is not rechecked.

The current 398-trial source preparation passed in `v4_independent_preparation04_xeon.json`. The first Xeon-aware preparation failed because its completion metadata has no `files` digest map; that failure, the corresponding helper source, and the schema correction are preserved. Mac completions still require their original digest maps. Xeon instead requires the complete receipt-time 18-file map and original ZIP entry byte comparison. Null exit codes are not converted to integers, and UTF-8 BOM bytes are retained while JSON parsing accepts them.

After the parent creates the new snapshot, run once from the E6 directory, substituting its actual new directory name:

```sh
python3 integration/check_v4_independent.py \
  --snapshot public_exports/REPLACE_WITH_NEW_V4_NAME \
  --output integration/v4_independent_final_review.json
```

Keep source documents unchanged between creation and verification. A new or changed source file after export is reported as a mismatch, rather than silently treating the snapshot as the latest source. The report is written after the inventory check and is therefore a subsequent supplement, not a file purportedly contained in the snapshot. An existing report is never overwritten. The helper explicitly refuses the already-reviewed v3 name.

The check covers:

- The exact current retained-source and public file sets, every original/public SHA and length, and literal local-path/hostname replacements only. This retains failed model versions, null/negative outcomes, and all raw data; documented runtime/privacy exclusions remain the same as the exporter.
- Byte-identical inputs, returned result/certificate/diagnostic JSON files, and `.class` files. Raw invocation/log files may require the documented literal path redaction; all other raw bytes and the complete raw inventory remain preserved. Completion and certificate digest references are checked against `original_sha256`, not the public digest of redacted metadata.
- All canonical freeze references, including the PC2 extension's `files` map rooted at `pc2_rolling/extended_7200/` (6 files) and `original_pc2_files` map rooted at `pc2_rolling/` (25 files). The 364 earlier references plus these 31 references happen to total 395; this is unrelated to the trial count.
- Exactly 398 measurements: Mac's 395 (194 WIN, 197 LOSS, 4 TO) plus received Xeon's 3 (1 WIN, 2 TO), totaling 195 WIN, 197 LOSS, 6 TO, with zero pending. These remain separate platform series. Registered schedules and underlying completion/result records are checked. Preflights, validation replays, failed construction attempts, and the nine `reference_e4` rows are not counted as new E6 measurements.
- PC2's original `lazy_none`, `lazy_transfers`, `direct_full_none` schedule and ordered 7,200-second/32g `lazy_transfers`, `direct_full_none` extension, both new trials timed out with exit `-9`, with no returned certificate or inferred state/rank counts. The original three trials and new two trials remain five separate rows with exact campaign/host/heap/budget/job keys. Status, input/JAR SHA, wall time, exit code, raw directory, and shared state/rank/certificate metrics are joined to the appropriate original result row; new rows also match their result rows in full. All four timeout rows retain empty unavailable fields.
- The final PC2 readiness/native-LaTeX marker and its original SHA references to the independent audit, three derived scripts, five tables, and frozen manifest.
- The Xeon arrival ZIP SHA and all 18 entry/raw byte identities, receipt-time raw manifest, acceptance-source/report/table hashes, 200g/7,200-second settings, actual serial invocation order, and RSS byte-to-GiB conversion. Xeon's completed WIN matches the Mac diagnostic (except diagnostic time); both TO rows keep unavailable fields empty. All three unrecorded exit codes stay empty, and missing runtime class SHA remains a provenance limitation. The distributed class SHA is not presented as a remote runtime measurement. Its eight-row table keeps the original five Mac rows and the three received Xeon rows distinct. These 18 receipt-hash references are separate from the 395 canonical freeze references.

The helper writes PASS only when every check succeeds. On failure it writes FAIL and exits nonzero; arbitrary exception text and local identity strings are not serialized. It does not claim a new solver proof, a semantic rerun, or a new privacy/PDF review. The export builder's exact-digest identity/PDF checks and the previously reviewed PDF exceptions remain separate requirements.

No v4 copy has been created by this preparation.

# Supplementary RQ3 trials

These two separate campaigns preserve the original unresolved records.
They use the same Xeon host, measured JAR, model bytes and method properties as the main campaign.
All original results remain in `rq3`; supplementary results have separate directories.

| Configuration | Cell | Heap / timeout | Planned slots | Purpose |
|---|---|---|---:|---|
| rq3_supplement_workflow_r2_direct_full | Workflow/R2, Direct-Full | 64 GiB / 1,200 s | 5 | Complete an operationally interrupted cell using a separate campaign |
| rq3_supplement_pc_arms2_r2_fg_3600 | PC Arms=2/R2, FG lazy | 64 GiB / 3,600 s | 1 | Observe the unresolved case at a longer cap, retaining the original 1,200 s result |

## Recorded outcomes

Workflow's first trial timed out. Its remaining four slots are `SKIPPED_AFTER_RESOURCE_FAILURE`.
Table 3 therefore displays TO with a provenance mark; S4 retains the original operational interruption and the supplementary timeout.
PC also timed out at 3,600 seconds. Its Table 3 cell remains the original 1,200-second TO.
The sampled process RSS was about 67 GiB with a 64 GiB heap cap; process RSS does not establish heap saturation.
Neither supplementary condition has a five-completion timing median.

## Reproduction steps

Use the host and local JAR placement in [the campaign guide](CAMPAIGN.md).
Run only after the main campaigns have finished, using a fresh replication package.
Run from `campaign/`; append explicit `-Python` and `-Java` paths if necessary:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage plan
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage stage2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage collect
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_pc_arms2_r2_fg_3600 -Stage plan
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_pc_arms2_r2_fg_3600 -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_pc_arms2_r2_fg_3600 -Stage collect
```

Workflow starts with one trial; only a valid completed decision enables four more.
Resource failures, abnormal termination and inconsistency leave explicit skips and are not retried.
PC has only one trial and no stage2. The maximum cap sum is 160 minutes plus overhead.
The plans retain the original method definitions but select only the intended method via each model's `method_ids`.
No input or configuration is edited to improve an outcome.

Retain the complete new directories:

- `campaign/raw/rq3_supplement_workflow_r2_direct_full/`
- `campaign/raw/rq3_supplement_pc_arms2_r2_fg_3600/`

The archived paper evidence restores under
`FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/` with the same campaign names.
The renderer validates these separate campaigns and produces the provenance table containing configurations,
start/end times, limits, statuses, peak RSS and links to the original records.
New replications are kept separately and never overwrite those originals.

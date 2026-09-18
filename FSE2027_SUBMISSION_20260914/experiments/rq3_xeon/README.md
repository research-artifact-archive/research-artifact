# FG-DUCS experiment source layout

All original Xeon campaigns and both supplementary RQ3 trials have completed.
This directory retains the fixed configuration files, generated inputs, generators,
measurement scripts and the paper's returned-data layout.
The English execution guide is `docs/CAMPAIGN.md` at the package root;
`docs/RQ3_SUPPLEMENT.md` documents the two separate follow-ups.
The portable Windows drivers and their matching model/runtime files are under root `campaign/`.
Run new campaigns there; keep this directory's archived data separate.

## Restore and inspect

From the package root, restore both raw-data assets using `restore_results.py`.
`raw/rq3`, `raw/rq4_controlled`, `raw/rq4_independent`, `raw/rq4_travel`,
`raw/rq4_hub` and both `raw/rq3_supplement_*` directories contain the returned records.
The independent Industry/R1 Mac check is decision evidence, not Xeon timing data.
Use `python quickstart.py` for a fresh, isolated verification and rendering run.

## Render from the saved evidence

Install the pinned plotting dependency from `plot-requirements.txt`.
From this directory, use a new output directory:

```sh
python scripts/render_results.py --mode xeon --input-root raw --output ../../../replication/rendered
python scripts/analyze_results.py --input-root raw --output ../../../replication/rendered
python scripts/check_render_results.py
```

Xeon mode validates configs, environments, plans, run records, stage1 summaries and repetition eligibility.
A missing or incomplete RQ3 campaign is rejected. Incomplete RQ4 families remain explicitly pending,
without replacing completed RQ3 or other complete RQ4 evidence.
Only five valid, decision-consistent completions receive median and min–max times.
TO/OOM and explicit skips remain visible; original raw is not rewritten.

The outputs include `rq3-table.tex`, `rq3-supplement.tex`, `rq3-cells.csv`,
`rq4-points.csv`, `rq4-scaling-combined.pdf`, complete state/time panels and the Travel status grid.
The main paper supplies the captions and labels.
The optional `placeholder`, `pilot` and synthetic `fixture` modes are identified in every output;
fixture and pilot output paths must have their dedicated names and must not enter the paper as measurements.
The Mac pilot contains 15 jobs (13 completed, one OOM, one timeout) and is separate from Xeon evidence.

## Preserve the protocol

The protocol uses one fresh JVM at a time, a 64 GiB heap and a 1,200-second cap,
except for the explicitly separate 3,600-second single trial.
Successful or proven-losing stage1 cells receive four further repetitions; failures are not retried.
The process-tree probe, sampled RSS, environment fingerprints and all terminal statuses are retained.
The driver catches native stderr as text and checks the actual process exit code.
Changing the directory layout does not change configs, model bytes or solver semantics.

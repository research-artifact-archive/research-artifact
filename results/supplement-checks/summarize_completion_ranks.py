"""Read all 27 fixed-campaign Lazy rows; do not execute or replace any trial."""
from pathlib import Path
import csv,json,re,statistics
HERE=Path(__file__).resolve().parent
PROJECT = (Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())) / "FSE2027_SUBMISSION_20260914"
RAW=PROJECT/'experiments/rq3_xeon/raw/rq3'
rows=list(csv.DictReader((RAW/'summary.csv').open()))
out=[];all_ranks=[]
for row in rows:
 if row['method_id']!='fg_ducs_otf':continue
 vals=[];sources=[]
 for rep in range(1,6):
  source=RAW/'runs'/f"{row['model_id']}__{row['target_id']}__rep{rep:02d}__fg_ducs_otf"/'output.txt'
  if not source.exists():continue
  text=source.read_text()
  a=re.findall(r'Worst completion rank \[revised_worst_completion_rank\] : ([0-9]+) steps',text)
  b=re.findall(r' - Worst completion rank: ([0-9]+)',text)
  assert a==b,(source,a,b)
  if a:assert len(a)==1;vals.append(int(a[0]));sources.append(str(source.relative_to(PROJECT)))
 if row['stage1_status']=='SUCCESS':
  assert len(vals)==5 and len(set(vals))==1,(row,vals)
  assert row['completed_valid_repetitions']=='5'
  all_ranks.append(vals[0])
 else:assert not vals,(row,vals)
 out.append(dict(model=row['model_id'],variant=row['target_id'],status=row['stage1_status'],rank=vals[0] if vals else '',valid_rank_records=len(vals),all_repetitions=';'.join(map(str,vals)),sources=';'.join(sources)))
assert len(out)==27 and len(all_ranks)==25
with (HERE/'completion_ranks.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
report=dict(scope='All 25 winning Lazy contracts in the fixed 27-contract RQ3 campaign; 125 saved runs. No new trials.',contracts=27,winning_contracts=25,minimum=min(all_ranks),maximum=max(all_ranks),median=statistics.median(all_ranks),stable_in_all_five_runs=True,limitation='Maximum retained rank bounds observed update-game events; it is not a shortest path, elapsed downtime, or guarantee without the stated progress premises.')
(HERE/'completion_ranks_summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

#!/usr/bin/env python3
"""Independent design checks, explicitly separate from E1 measured trials."""
import argparse,hashlib,json,time
from pathlib import Path
from check_games import E6,Model,sha

def main():
 ap=argparse.ArgumentParser();ap.add_argument('family');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 base=E6/args.family;checks=[];start=time.monotonic()
 for path in sorted((base/'inputs').glob('*.json')):
  model=Model(json.loads(path.read_text()),'none');seen,graph=model.enumerate();ranks,iterations=model.solve(seen,graph)
  row=dict(input=path.name,sha256=sha(path),decision='WIN' if model.roots<=ranks.keys() else 'LOSS',states=len(seen),initial_states=len(model.roots),
   minimum_worst_root_rank=max(ranks[s] for s in model.roots) if model.roots<=ranks.keys() else None,iterations=iterations)
  checks.append(row)
  print(json.dumps(row),flush=True)
 report=dict(status='PASS',scope='Independent finite-model design calculation, NOT E1 trial measurements. Does not fill any raw/summary field.',checker_sha256=sha(Path(__file__).with_name('check_games.py')),elapsed_seconds=time.monotonic()-start,checks=checks)
 with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
if __name__=='__main__':main()

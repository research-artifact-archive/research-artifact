#!/usr/bin/env python3
"""Fixed scale extension; invokes unchanged Rolling construction, never tunes inputs."""
import argparse,json,runpy
from pathlib import Path
E6=Path(__file__).resolve().parents[1]
make=runpy.run_path(str(E6/'rolling/gen_rolling.py'))['make']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path(__file__).parent/'v1');args=ap.parse_args()
 out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir();jobs=[]
 for n in range(7,17):
  for m in [1,n-1]:
   files={}
   for k in [1,n]:
    model=make(n,m,k);filename=f"inputs/{model['id']}.json";files[k]=filename
    with (out/filename).open('x') as f:json.dump(model,f,indent=2);f.write('\n')
   prefix=f'n{n:02}_m{m:02}'
   jobs += [dict(id=prefix+'_fine_lazy',input=files[1],merge='none',solver='lazy',expected_decision='WIN',parameters=dict(n=n,m=m,k=1)),
     dict(id=prefix+'_merged_lazy',input=files[1],merge='transfers',solver='lazy',expected_decision='LOSS',parameters=dict(n=n,m=m,k=n),compare_input=files[n],compare_merge='none'),
     dict(id=prefix+'_all_lazy',input=files[n],merge='none',solver='lazy',expected_decision='LOSS',parameters=dict(n=n,m=m,k=n)),
     dict(id=prefix+'_fine_df',input=files[1],merge='none',solver='direct_full',expected_decision='WIN',parameters=dict(n=n,m=m,k=1))]
 rel=str(out.relative_to(E6))
 config=dict(schema='e6-family-run-v1',family='rolling_scale',version='v1',heap='32g',timeout_seconds=1200,trials=1,
  start_cutoff='2026-09-30T09:39:00+09:00',deadline='2026-09-30T10:00:00+09:00',jobs=jobs,
  frozen_paths=['rolling_scale/gen_scale.py','rolling_scale/analyze_scale.py','rolling_scale/README.md','rolling/gen_rolling.py','rolling/validate_endpoints.py','common/SCHEMA.md','common/witness.schema.json'],
  endpoint_checks=[['python3','-B','rolling/validate_endpoints.py',rel]],
  preflight_jobs=['n07_m01_fine_lazy','n07_m01_merged_lazy'],
  analysis_commands=[['python3','-B','rolling_scale/analyze_scale.py',rel]])
 with (out/'config.json').open('x') as f:json.dump(config,f,indent=2);f.write('\n')
 print(json.dumps(dict(inputs=40,jobs=len(jobs),output=str(out),create_only=True)))
if __name__=='__main__':main()

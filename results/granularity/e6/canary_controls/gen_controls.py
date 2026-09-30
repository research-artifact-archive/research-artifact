#!/usr/bin/env python3
"""Create-only two preregistered edits to byte-preserved Canary reference inputs."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;E6=HERE.parent;OUT=HERE/'v1'
def save(path,data):
 with path.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def main():
 OUT.mkdir(exist_ok=False);(OUT/'inputs').mkdir();(OUT/'reference').mkdir();jobs=[];refs=[]
 base_manifest=json.loads((E6/'canary/v1/build/frozen_manifest.json').read_text())
 for n in range(2,5):
  for m in range(1,n):
   for group in ('fine','all'):
    source=E6/f'canary/v1/inputs/canary_n{n:02}_m{m:02}_{group}.json';digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest==base_manifest['files'][str(source.relative_to(E6))]
    shutil.copy2(source,OUT/'reference'/source.name);refs.append(str((OUT/'reference'/source.name).relative_to(E6)))
   for control in ('healthy_only','no_recovery'):
    generated={}
    for group in ('fine','all'):
     source=OUT/f'reference/canary_n{n:02}_m{m:02}_{group}.json';data=json.loads(source.read_text());data['id']=f'canary_controls_n{n:02}_m{m:02}_{control}_{group}';data['family']='canary_controls';data['parameters']['control']=control
     for c in data['components']:
      if control=='healthy_only':c['transfer']['H']=['HP']
      else:c['new']['edges']=[edge for edge in c['new']['edges'] if not edge[1].startswith('restart_')]
     data['metadata'].update(control=control,reference_input='reference/'+source.name,reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),expected_decision='WIN' if control=='healthy_only' else 'LOSS',control_scope='Only transfer outcome set changes.' if control=='healthy_only' else 'Only B-to-H recovery edges are removed; all action declarations and tester observations remain unchanged.')
     generated[group]=data;save(OUT/'inputs'/(data['id']+'.json'),data)
    for variant,group,merge,solver in [('fine_lazy','fine','none','lazy'),('merged_lazy','fine','transfers','lazy'),('all_lazy','all','none','lazy'),('fine_df','fine','none','direct_full')]:
     data=generated[group];job=dict(id=f'n{n:02}_m{m:02}_{control}_{variant}',input='inputs/'+data['id']+'.json',merge=merge,solver=solver,expected_decision=data['metadata']['expected_decision'],parameters=dict(n=n,m=m,control=control,k=n if variant in ('merged_lazy','all_lazy') else 1),variant=variant)
     if variant=='merged_lazy':job.update(compare_input='inputs/'+generated['all']['id']+'.json',compare_merge='none')
     jobs.append(job)
 config=dict(schema='e6-family-run-v1',family='canary_controls',version='v1',heap='32g',timeout_seconds=1200,trials=1,start_cutoff='2026-09-30T09:39:00+09:00',deadline='2026-09-30T10:00:00+09:00',jobs=jobs,
  frozen_paths=['canary_controls/gen_controls.py','canary_controls/validate_controls.py','canary_controls/analyze_controls.py','canary_controls/README.md','rolling/validate_endpoints.py','common/SCHEMA.md','common/witness.schema.json']+refs,
  endpoint_checks=[['python3','-B','canary_controls/validate_controls.py','canary_controls/v1']],preflight_jobs=['n02_m01_'+c+'_'+v for c in ('healthy_only','no_recovery') for v in ('fine_lazy','merged_lazy')],analysis_commands=[['python3','-B','canary_controls/analyze_controls.py','canary_controls/v1']])
 save(OUT/'config.json',config);print(json.dumps(dict(inputs=24,references=12,jobs=len(jobs),create_only=True)))
if __name__=='__main__':main()

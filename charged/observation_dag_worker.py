"""Replay the fixed strict-observation four-job family and both controls."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SRC=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic()
assert __debug__ and STAGE=='universal-observation-dag'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
folder='universal_observation_dag_01';prior=SRC/folder;fixed=read(prior/'START01.json');d=OUT/folder;d.mkdir()
for name,h in fixed['hashes'].items():
 assert sha(prior/name)==h,name
 shutil.copy2(prior/name,d/name)
dep=OUT/'joint_work_general_r_01';dep.mkdir();source=SRC/'joint_work_general_r_01/unknown02.py';assert sha(source)==fixed['visible_oracle_sha256'];shutil.copy2(source,dep/'unknown02.py')
t=time.monotonic()
with (OUT/'observation.stdout').open('xb') as out,(OUT/'observation.stderr').open('xb') as err:
 proc=subprocess.run([sys.executable,'-B',str(d/'check01.py'),'run'],stdout=out,stderr=err,timeout=300)
assert proc.returncode==0,proc.returncode
x,y=read(d/'SUMMARY01.json'),read(prior/'SUMMARY01.json');assert set(x)==set(y)
for key in x:
 if key not in {'utc','ended_utc','seconds'}:assert x[key]==y[key],key
stable=['ROWS01.json','TREES01.json','NEGATIVE_CONTROLS01.json','PATHS01.jsonl.gz']
for name in stable:assert sha(d/name)==sha(prior/name)==x['outputs'][name],name
assert x['status']=='SUCCESS' and x['counts']=={'SUCCESS':28} and x['family_roots']==21 and x['negative_controls_detected']==2
r=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,steps=[dict(step=STAGE,returncode=0,seconds=time.monotonic()-t)],counts=x['counts'],family_roots=21,outside_family_controls=7,interpreted_paths=x['interpreted_paths'],negative_controls_detected=2,byte_equal_scientific_outputs=stable,new_native_runs=0,new_timing_samples=0,new_evaluation_population=False,all_program_proof_certification=False,independent_reproduction=False,erased_oracle_scope='canonical cheap-prefix policies only')
with (OUT/'SUMMARY.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r),flush=True)

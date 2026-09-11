"""Replay the fixed sufficient safe-fresh transformation; no new population."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SRC=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic()
assert __debug__ and STAGE=='safe-fresh-suffix'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=SRC/'safe_fresh_suffix_01';fixed=read(a/'START01.json');old=SRC/'joint_work_general_r_01/unknown02.py'
for n,h in fixed['hashes'].items():assert sha(old if n=='unknown02.py' else a/n)==h,n
for folder,names in [('joint_work_general_r_01',['unknown02.py']),('safe_fresh_suffix_01',['check01.py','PROTOCOL01.md'])]:
 d=OUT/folder;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(SRC/folder/n,d/n)
b=OUT/'safe_fresh_suffix_01'
with (OUT/'fixed714.stdout').open('xb') as out,(OUT/'fixed714.stderr').open('xb') as err:
 p=subprocess.run([sys.executable,'-B',str(b/'check01.py')],stdout=out,stderr=err,timeout=65)
assert p.returncode==0
stable=['INPUTS01.json','ROWS01.json','TREES01.json','PATHS01.jsonl','CONTROL01.json','CONTROL_TREE01.json','CONTROL_PATHS01.json','STRICT01.json']
for n in stable:assert sha(a/n)==sha(b/n),n
x,y=read(a/'SUMMARY01.json'),read(b/'SUMMARY01.json');assert set(x)==set(y)
for k in x:
 if k not in ['utc','seconds']:assert x[k]==y[k],k
assert x['status']=='SUCCESS' and x['counts']=={'SUCCESS':714} and x['interpreted_paths']==22583 and x['strictly_improved_roots']==2 and x['control_violations']>0
r=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,fixed_roots=714,interpreted_paths=22583,strictly_improved_preselected_roots=2,equal_roots=712,control_violations=x['control_violations'],byte_equal_scientific_outputs=stable,new_native_runs=0,new_timing_samples=0,new_independent_inputs=0,independent_reproduction=False,theorem_source='analytic proof; finite replay is corroboration',general_DAG_least_work_claim=False)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r),flush=True)

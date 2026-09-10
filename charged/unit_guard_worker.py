"""Replay the fixed unit-guard precedence embedding and fee translation."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SRC=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic()
assert __debug__ and STAGE=='unit-guard-dag'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
folder='guard_dag_unit_01';fixed=read(SRC/folder/'INPUT_FIX_RECEIPT02.json');d=OUT/folder;d.mkdir()
for name in list(fixed['files'])+['INPUT_FIX_RECEIPT02.json']:
 target=d/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/folder/name,target)
dep=OUT/'charged_comparison_01';dep.mkdir();shutil.copy2(SRC/'charged_comparison_01/check04.py',dep/'check04.py')
t=time.monotonic()
with (OUT/'unit-guard-dag.stdout').open('xb') as out,(OUT/'unit-guard-dag.stderr').open('xb') as err:
 proc=subprocess.run([sys.executable,'-B',str(d/'check02.py')],stdout=out,stderr=err,timeout=900)
assert proc.returncode==0,proc.returncode
actual=d/'run02';prior=SRC/folder/'run02';stable=sorted(x.name for x in prior.glob('*.jsonl.gz'))+['CONTROLS.json']
for name in stable:assert sha(actual/name)==sha(prior/name),name
x,y=read(actual/'RESULT.json'),read(prior/'RESULT.json');assert set(x)==set(y)
for key in x:
 if key not in {'utc','seconds'}:assert x[key]==y[key],key
assert x['status']=='SUCCESS' and x['complete_denominator']
r=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,steps=[dict(step=STAGE,returncode=0,seconds=time.monotonic()-t)],counts=x['counts'],byte_equal_scientific_outputs=stable,new_native_runs=0,new_timing_samples=0,new_evaluation_population=False,all_program_proof_certification=False,independent_reproduction=False)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r),flush=True)

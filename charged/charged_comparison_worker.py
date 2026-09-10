"""Replay fixed charged-cost mathematics or the saved native counting analysis."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SRC=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic();steps=[]
assert __debug__ and STAGE in ['charged-comparison','fully-charged-one-write','linux-counting']
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cp(folder,names):
 d=OUT/folder;d.mkdir(parents=True,exist_ok=True)
 for name in names:
  target=d/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/folder/name,target)
 return d
def run(name,args):
 t=time.monotonic()
 with (OUT/(name+'.stdout')).open('xb') as out,(OUT/(name+'.stderr')).open('xb') as err:
  proc=subprocess.run([sys.executable,'-B']+list(map(str,args)),stdout=out,stderr=err,timeout=180)
 assert proc.returncode==0,(name,proc.returncode)
 steps.append(dict(step=name,returncode=0,seconds=time.monotonic()-t))
def compare(a,b,exclude):
 x,y=read(a),read(b);assert set(x)==set(y),(a.name,'keys')
 for key in x:
  if key not in exclude:assert x[key]==y[key],(a.name,key)
if STAGE in ['charged-comparison','fully-charged-one-write']:
 folder='charged_comparison_01';version='01' if STAGE=='charged-comparison' else '04'
 fixed=read(SRC/folder/('INPUT_FIX_RECEIPT'+version+'.json'))
 if version=='01':names=['check01.py','INPUTS01.json','INPUT_FIX_RECEIPT01.json','PROOF_CANDIDATE01.md','PROTOCOL01.md','CONTROL_PREDICTION_NOTE01.md','generate_inputs01.py']
 else:names=list(fixed['files'])+['INPUT_FIX_RECEIPT04.json']
 d=cp(folder,names);result=d/('run'+version)
 args=[d/('check'+version+'.py')]
 if version=='01':args+=['--out',result]
 run(STAGE,args)
 prior=SRC/folder/('run'+version)
 names=sorted(x.name for x in prior.glob('*.jsonl.gz'))+['CONTROLS.json']
 for name in names:assert sha(result/name)==sha(prior/name),name
 compare(result/'RESULT.json',prior/'RESULT.json',{'utc','seconds','outputs'})
 status=read(result/'RESULT.json');assert status['status']=='SUCCESS'
 values=dict(counts=status['counts'],byte_equal_scientific_outputs=names,all_program_proof_certification=False)
else:
 folder='linux_dentry_01'
 d=cp(folder,['MATRIX_JOINED02.json','MATRIX_COMPARISON02.json','MATRIX_GLOBAL03B.json','implementation03/cached_body.c.inc','Q_SENSITIVITY04_PLAN.md','q_sensitivity04.py'])
 run(STAGE,[d/'q_sensitivity04.py'])
 assert sha(d/'Q_SENSITIVITY04_ROWS.json')==sha(SRC/folder/'Q_SENSITIVITY04_ROWS.json')
 compare(d/'Q_SENSITIVITY04_RECEIPT.json',SRC/folder/'Q_SENSITIVITY04_RECEIPT.json',{'utc'})
 r=read(d/'Q_SENSITIVITY04_RECEIPT.json');assert r['status']=='SUCCESS' and r['pairs']==384
 values={k:r[k] for k in ['pairs','groups','maximum_logical_Q','maximum_named_primitive_sum','posthoc_descriptive_reconstruction']}
summary=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,steps=steps,**values,new_native_runs=0,new_timing_samples=0,new_evaluation_population=False,independent_reproduction=False)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

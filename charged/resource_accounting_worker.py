"""Replay fixed comparison-free guard mathematics and alternative call accounting."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SRC=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic();steps=[]
assert __debug__ and STAGE in ['guard-only-joint','uniform-guard','double-counted-mismatch']
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
def compare_result(a,b):
    x,y=read(a),read(b);assert set(x)==set(y)
    for key in x:
        if key not in {'utc','seconds'}:assert x[key]==y[key],(a.name,key)
if STAGE in ['guard-only-joint','uniform-guard']:
    folder='guard_only_both_01';cp('charged_comparison_01',['check04.py'])
    if STAGE=='guard-only-joint':
        fixed=read(SRC/folder/'INPUT_FIX_RECEIPT01.json')
        names=[x['path'] for x in fixed['files']]+['INPUT_FIX_RECEIPT01.json']
        version='run01';script='check01.py';controls=['CONTROLS.json']
    else:
        fixed=read(SRC/folder/'GREEDY_FIX_RECEIPT02.json')
        names=[x['path'] for x in fixed['files']]+['GREEDY_FIX_RECEIPT02.json']
        version='greedy02';script='greedy02.py';controls=['CONTROL.json']
else:
    folder='split_call_count_01';cp('joint_work_general_r_01',['check01.py'])
    fixed=read(SRC/folder/'INPUT_FIX_RECEIPT01.json')
    names=[x['path'] for x in fixed['files']]+['INPUT_FIX_RECEIPT01.json']
    version='run01';script='check01.py';controls=[]
d=cp(folder,names);run(STAGE,[d/script]);prior=SRC/folder/version;actual=d/version
stable=sorted(x.name for x in prior.glob('*.jsonl.gz'))+controls
for name in stable:assert sha(actual/name)==sha(prior/name),name
compare_result(actual/'RESULT.json',prior/'RESULT.json')
r=read(actual/'RESULT.json');assert r['status']=='SUCCESS'
summary=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,steps=steps,counts=r['counts'],byte_equal_scientific_outputs=stable,new_native_runs=0,new_timing_samples=0,new_evaluation_population=False,all_program_proof_certification=False,independent_reproduction=False)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

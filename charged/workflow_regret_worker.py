"""Recompute exact workflow policy vectors and uniform additive loss."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time

HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[2])
BASE=HERE/'evidence/RESUMED_20260910_0343'
SOURCE=BASE/'workflow_uniform_regret_02'
assert __debug__ and sys.argv[1]=='workflow-regret'
start=time.monotonic();dest=OUT/'workflow_uniform_regret_02';dest.mkdir()
other=OUT/'partial_repair_toll_dag_01';other.mkdir()
shutil.copy2(BASE/'partial_repair_toll_dag_01/threshold_compile.py',other/'threshold_compile.py')
for name in ['PLAN.md','FIXED_PLAN02.md','PROOF.md','run01.py','run_fixed02.py','regret_compile.py']:
    shutil.copy2(SOURCE/name,dest/name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
stages=[]
for script,folder,expected in [('run01.py','run01',540),('run_fixed02.py','fixed02',5360)]:
    t=time.monotonic()
    with (OUT/(folder+'.stdout')).open('xb') as out,(OUT/(folder+'.stderr')).open('xb') as err:
        run=subprocess.run([sys.executable,'-B',str(dest/script)],stdout=out,stderr=err,timeout=240)
    assert run.returncode==0,(script,run.returncode)
    fresh=json.loads((dest/folder/'SUMMARY.json').read_text());old=json.loads((SOURCE/folder/'SUMMARY.json').read_text())
    assert set(fresh)==set(old)
    for key in fresh:
        if key not in ['utc','seconds']:assert fresh[key]==old[key],(folder,key)
    assert fresh['status']=='PASS' and fresh['all_units']==expected
    for name in ['INPUTS.json','RAW.jsonl']:
        assert sha(dest/folder/name)==sha(SOURCE/folder/name),(folder,name)
    files=sorted((SOURCE/folder).glob('unit_*.json'));assert len(files)==expected
    for p in files:assert sha(dest/folder/p.name)==sha(p),p.name
    stages.append(dict(folder=folder,conditions=expected,seconds=time.monotonic()-t,exact_policy_vector_and_threshold_exports=len(files),totals=fresh['totals'],controls=fresh['controls']))
summary=dict(status='SUCCESS',stage='workflow-regret',seconds=time.monotonic()-start,replay_only=True,new_native_runs=0,new_timing_samples=0,exploratory_conditions=540,fixed_conditions=5360,all_conditions=5900,budget_coordinates=43460,nondominated_root_vectors=13257,positive_loss=2458,zero_loss=3442,stages=stages,scope='Exact unchanged recomputation of full observation-history policy vectors, informed curves, uniform additive losses and shifted policy extraction; mathematical proof is separate.')
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

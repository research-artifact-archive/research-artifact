"""Replay a previously observed distinct-order root and its new short policy."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SRC=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic()
assert __debug__ and STAGE=='short-order-policy'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(folder,names):
 d=OUT/folder;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(SRC/folder/n,d/n)
 return d
old=SRC/'joint_work_general_r_01/unknown02.py'
short=SRC/'general_DAG_short_policy_01';fixed=read(short/'START01.json')
assert sha(old)==fixed['hashes']['unknown02.py']
for n in ['check01.py','PROTOCOL01.md']:assert sha(short/n)==fixed['hashes'][n]
follow=SRC/'general_DAG_followup_01';f07=read(follow/'START07.json')
for n,h in f07['hashes'].items():assert sha(follow/n)==h,n
assert sha(old)==f07['oracle_sha256']
copy('joint_work_general_r_01',['unknown02.py'])
a=copy('general_DAG_followup_01',['INPUTS07.json','PROTOCOL07.md','claude_candidate07.py','greedy_order04.py'])
b=copy('general_DAG_short_policy_01',['check01.py','PROTOCOL01.md'])
steps=[]
for name,argv in [('distinct-root07',[sys.executable,'-B',str(a/'claude_candidate07.py'),'run']),('short-policy01',[sys.executable,'-B',str(b/'check01.py')])]:
 t=time.monotonic()
 with (OUT/(name+'.stdout')).open('xb') as stdout,(OUT/(name+'.stderr')).open('xb') as stderr:
  p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=30)
 steps.append(dict(step=name,returncode=p.returncode,seconds=time.monotonic()-t));assert p.returncode==0,name
assert sha(a/'RESULT07.json')==sha(follow/'RESULT07.json')==fixed['reference_sha256']
assert sha(a/'WITNESS07_0.json')==sha(follow/'WITNESS07_0.json')
stable=['candidate_TREE01.json','candidate_PATHS01.jsonl','control_TREE01.json','control_PATHS01.jsonl']
for name in stable:assert sha(b/name)==sha(short/name),name
x,y=read(b/'SUMMARY01.json'),read(short/'SUMMARY01.json');assert set(x)==set(y)
for k in x:
 if k not in ['utc','seconds']:assert x[k]==y[k],k
assert x['status']=='SUCCESS' and [p['paths'] for p in x['policies']]==[427,421]
assert x['policies'][0]['W'][7]==752 and x['policies'][1]['W'][7]==766
r=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,steps=steps,previous_root_replayed=1,previous_full_paths=313,previous_minready_paths=309,new_policy_paths=427,premature_fresh_control_paths=421,new_independent_inputs=0,unrestricted_upper_B7=752,all_program_minready_lower_B7=766,lower_bound_source='author analytic proof; not proved by replay',byte_equal_scientific_outputs=['RESULT07.json','WITNESS07_0.json']+stable,new_native_runs=0,new_timing_samples=0,independent_reproduction=False,general_root_least_curve_claim=False)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r),flush=True)

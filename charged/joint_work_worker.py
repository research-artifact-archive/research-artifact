"""Exact finite reruns and replay of the saved observable-comparison Java matrix."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'evidence/RESUMED_20260910_1617'
OUT=Path(sys.argv[2]);assert __debug__ and sys.argv[1]=='joint-work'
started=time.monotonic();steps=[]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def run(label,script):
    t=time.monotonic()
    with(OUT/(label+'.stdout')).open('xb') as out,(OUT/(label+'.stderr')).open('xb') as err:
        p=subprocess.run([sys.executable,'-B',str(script)],stdout=out,stderr=err,timeout=180)
    assert p.returncode==0,(label,p.returncode)
    steps.append(dict(step=label,returncode=p.returncode,seconds=time.monotonic()-t))
def same_keys(a,b,keys):
    x,y=read(a),read(b)
    for k in keys:assert x[k]==y[k],(a.name,k)

src=SOURCE/'joint_work_01';dst=OUT/'joint_work_01'
for f in ['check01.py','FINITE_PROTOCOL01.md']:copy(src/f,dst/f)
run('finite_frontier',dst/'check01.py')
for f in ['known_frontiers01.jsonl','one_write_caps01.jsonl','one_write_corollary01.jsonl','unaware_curves01.jsonl','independent01.jsonl','saturation01.jsonl','fixtures01.jsonl']:
    assert sha(dst/f)==sha(src/f),f
same_keys(dst/'SUMMARY01.json',src/'SUMMARY01.json',['status','counts','planned_counts','canonical_finite_class_only','denominators_match','output_hashes'])

for f in ['order02.py','ORDER_PROTOCOL02.md']:copy(src/f,dst/f)
run('all_fixed_orders',dst/'order02.py')
for f in ['order_comparisons02.jsonl','ascending_comparisons02.jsonl']:assert sha(dst/f)==sha(src/f),f
same_keys(dst/'ORDER_SUMMARY02.json',src/'ORDER_SUMMARY02.json',['status','counts','strict_adaptive_order_counts','ascending_counts','strict_vs_ascending','expected_counts','outputs'])

for f in ['invisible05.py','INVISIBLE_PROTOCOL05.md']:copy(src/f,dst/f)
run('invisible_partitions',dst/'invisible05.py')
assert sha(dst/'invisible05.jsonl')==sha(src/'invisible05.jsonl')
same_keys(dst/'INVISIBLE_SUMMARY05.json',src/'INVISIBLE_SUMMARY05.json',['status','cases','weight_vectors','statuses','strict_Boolean_value_cases'])

src=SOURCE/'joint_work_native_01';dst=OUT/'joint_work_native_01'
for f in ['check01.py','INPUTS.json','RAW01.jsonl']:copy(src/f,dst/f)
run('saved_native_events',dst/'check01.py')
for f in ['CHECK_ROWS01.jsonl','MAXIMA01.json']:assert sha(dst/f)==sha(src/f),f
same_keys(dst/'SUMMARY01.json',src/'SUMMARY01.json',['status','denominator','correct_policies','negative_controls','statuses','correct_policy_success','control_violations','control_nonviolations','same_output_mismatches','saved_differs_live'])
summary=dict(status='SUCCESS',stage='joint-work',seconds=time.monotonic()-started,steps=steps,known_frontier_cases=26844,one_write_cap_cases=18390,one_write_corollary_cases=5421,independent_cases=2004,universal_cases=237,saturation_cases=363,all_order_cases=26844,invisible_cases=2367,strict_Boolean_value_cases=950,saved_native_valid_policy_cases=2076,saved_native_negative_controls=52,predicted_control_violations=4,control_nonviolations=48,new_native_runs=0,new_timing_samples=0,independent_reproduction=False,scope='Exact author-side finite recomputation and saved native event reconstruction. Full-program/source proofs are not mechanically verified by these enumerations.')
with(OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

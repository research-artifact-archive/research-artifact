"""Recompute fixed universal curves and reconstruct saved Java executions."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SOURCE=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);assert __debug__ and STAGE in ['universal-independent','universal-independent-native']
START=time.monotonic();steps=[]
def read(p):return json.loads(p.read_text())
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def source(f):
 p=SOURCE/f
 return p if p.exists() else p.with_name(p.name+'.gz')
def materialize(f,dest):
 src=source(f);dest.parent.mkdir(parents=True,exist_ok=True)
 if str(src).endswith('.gz') and not str(f).endswith('.gz'):
  with gzip.open(src,'rb') as inp,dest.open('xb') as out:shutil.copyfileobj(inp,out)
 else:shutil.copy2(src,dest)
def decoded_digest(f):
 src=source(f);h=hashlib.sha256();opener=gzip.open if str(src).endswith('.gz') and not str(f).endswith('.gz') else open
 with opener(src,'rb') as inp:
  for b in iter(lambda:inp.read(1048576),b''):h.update(b)
 return h.hexdigest()
def same_output(folder,files):
 for f in files:assert digest(OUT/folder/f)==decoded_digest(Path(folder)/f),(folder,f)
def same_summary(folder,name,keys):
 a=read(OUT/folder/name);b=read(source(Path(folder)/name))
 for k in keys:assert a[k]==b[k],(folder,name,k)
def copyfiles(folder,files):
 for f in files:materialize(Path(folder)/f,OUT/folder/f)
def run(label,script):
 start=time.monotonic()
 with(OUT/(label+'.stdout')).open('xb') as out,(OUT/(label+'.stderr')).open('xb') as err:p=subprocess.run([sys.executable,'-B',str(script)],stdout=out,stderr=err,timeout=180)
 assert p.returncode==0,(label,p.returncode)
 steps.append(dict(step=label,returncode=p.returncode,seconds=time.monotonic()-start))
if STAGE=='universal-independent':
 g='joint_work_general_r_01'
 copyfiles(g,['unknown02.py','UNKNOWN_ROWS02.jsonl','universal09.py','UNIVERSAL_PROTOCOL09.md','UNIVERSAL_INDEPENDENT_DRAFT09.md'])
 run('universal_curves_and_paths',OUT/g/'universal09.py')
 same_output(g,['UNIVERSAL_INPUTS09.json','UNIVERSAL_ROWS09.jsonl','UNIVERSAL_RETROSPECTIVE09.json','UNIVERSAL_PATHS09.jsonl.gz','UNIVERSAL_ERRORS09.json'])
 same_summary(g,'UNIVERSAL_SUMMARY09.json',['status','counts','retrospective_independent_cases','r0_DAG_cases','retrospective_overlap','retrospective_statuses','r0_statuses','policy_paths','oracle_states','outputs'])
 copyfiles(g,['scope11.py','UNIVERSAL_SCOPE_PROTOCOL11.md']);run('scope_boundaries',OUT/g/'scope11.py')
 same_output(g,['SCOPE_ROWS11.jsonl']);same_summary(g,'SCOPE_SUMMARY11.json',['status','counts','rows_sha256','root_frontier_widths'])
 copyfiles(g,['erased12.py','ERASED_PROTOCOL12.md']);run('universal_observation_counterexample',OUT/g/'erased12.py')
 same_output(g,['ERASED_POLICY_ROWS12.jsonl','ERASED_ROOT_ROWS12.json']);same_summary(g,'ERASED_SUMMARY12.json',['status','roots','policy_trees','admissible_policy_trees','rejected_protection','interpreted_paths','hashes'])
 values=dict(observation_roots=4,erased_policy_trees=8672,admitted_erased_trees=4,observation_policy_paths=102122,fixed_roots=647,policy_paths=34814,oracle_states=188690,scope_roots=36,retrospective_independent_roots=117,retrospective_r0_DAG_roots=237,retrospective_overlap=39)
else:
 g='universal_independent_native_01';copyfiles(g,['check01.py','INPUTS.json','RAW01.jsonl']);run('saved_native_events',OUT/g/'check01.py')
 same_output(g,['CHECK_ROWS01.jsonl','CURVE_MAXIMA01.json','MUTATION_RESULTS01.json','CHECK_ERRORS01.json'])
 same_summary(g,'SUMMARY01.json',['status','denominator','statuses','wrapper_pairs','curve_groups','budget_coordinates','cheap_failures','cached_calls','tree_bin_executions','mutation_statuses'])
 values=dict(saved_native_executions=20384,wrapper_pairs=10192,curve_groups=512,budget_coordinates=2464,tree_bin_executions=4092,cheap_failures=24168,cached_calls=108576,expected_corruption_rejections=12)
summary=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,steps=steps,**values,new_native_runs=0,new_timing_samples=0,new_evaluation_population=False,independent_reproduction=False,scope='Exact fixed mathematics and saved native event reconstruction. All-program and source/JMM arguments are not mechanically certified.')
with(OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

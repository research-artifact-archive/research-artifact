"""Replay fixed general-retry populations and saved native event semantics."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;SOURCE=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);assert __debug__ and STAGE in ['general-retry','one-retry-native']
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
 src=source(f);h=hashlib.sha256()
 opener=gzip.open if str(src).endswith('.gz') and not str(f).endswith('.gz') else open
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
 with(OUT/(label+'.stdout')).open('xb') as out,(OUT/(label+'.stderr')).open('xb') as err:
  p=subprocess.run([sys.executable,'-B',str(script)],stdout=out,stderr=err,timeout=180)
 assert p.returncode==0,(label,p.returncode)
 steps.append(dict(step=label,returncode=p.returncode,seconds=time.monotonic()-start))
if STAGE=='general-retry':
 g='joint_work_general_r_01'
 copyfiles('joint_work_01',['known_frontiers01.jsonl'])
 copyfiles(g,['check01.py','FINITE_PROTOCOL01.md']);run('full_retained_frontier',OUT/g/'check01.py')
 same_output(g,['ROWS01.jsonl','FAILURES01.json']);same_summary(g,'SUMMARY01.json',['status','counts','input_count','by_n','visited','r0_archive_comparison','hashes'])
 copyfiles(g,['unknown02.py','UNKNOWN_PROTOCOL02.md']);run('unknown_budget_curves',OUT/g/'unknown02.py')
 same_output(g,['UNKNOWN_ROWS02.jsonl','UNKNOWN_FAILURES02.json','UNKNOWN_WITNESSES02.json']);same_summary(g,'UNKNOWN_SUMMARY02.json',['status','counts','frontier_widths','interpreted_paths','visited_states','hashes'])
 copyfiles(g,['one_write03.py','ONE_WRITE_RETRY03.md']);run('one_write_retry_projection',OUT/g/'one_write03.py')
 same_output(g,['ONE_WRITE_ROWS03.jsonl','ONE_WRITE_FAILURES03.json']);same_summary(g,'ONE_WRITE_SUMMARY03.json',['status','counts','by_r','hashes'])
 copyfiles(g,['independent05.py','INDEPENDENT_ALL_RETRIES05.md']);run('closed_frontier_projection',OUT/g/'independent05.py')
 same_output(g,['INDEPENDENT_ROWS05.jsonl','INDEPENDENT_FAILURES05.json']);same_summary(g,'INDEPENDENT_SUMMARY05.json',['status','counts','scope_counts','scope_overlap','hashes'])
 copyfiles(g,['independent06.py','PROSPECTIVE_INDEPENDENT06.md']);run('prospective_independent_paths',OUT/g/'independent06.py')
 same_output(g,['INDEPENDENT_INPUTS06.json','INDEPENDENT_ROWS06.jsonl','INDEPENDENT_PATHS06.jsonl','INDEPENDENT_RIGIDITY06.json','INDEPENDENT_FAILURES06.json']);same_summary(g,'INDEPENDENT_SUMMARY06.json',['status','counts','interpreted_paths','rigidity_cases','rigidity_success','result_hashes'])
 copyfiles(g,['simplified08.py','SIMPLIFIED_PROTOCOL08.md']);run('simplified_policy_paths',OUT/g/'simplified08.py')
 same_output(g,['SIMPLIFIED_ROWS08.jsonl','SIMPLIFIED_BOUNDARIES08.jsonl','SIMPLIFIED_PATHS08.jsonl.gz','SIMPLIFIED_ERRORS08.json']);same_summary(g,'SIMPLIFIED_SUMMARY08.json',['status','counts','boundary_counts','paths','boundary_paths','outside_promise_fixture','outputs'])
 values=dict(general_roots=96795,unknown_roots=713,retrospective_unique_roots=33804,independent_input_roots=13850,paths_per_policy_variant=540230,simplified_boundary_cases=9240,simplified_boundary_paths=481995)
else:
 g='one_retry_native_01';copyfiles(g,['check01.py','INPUTS.json','RAW01.jsonl']);run('saved_native_events',OUT/g/'check01.py')
 same_output(g,['CHECK_ROWS01.jsonl','MAXIMA01.json','CHECK_ERRORS01.json']);same_summary(g,'SUMMARY01.json',['status','denominator','statuses','wrapper_pairs','groups','cheap_failures','cached_calls','tree_bin_executions','unissued_late_writes','saved_differs_live'])
 values=dict(saved_native_executions=12224,wrapper_pairs=6112,tree_bin_executions=4336,cheap_failures=304,cached_calls=1056,retained_unissued_late_writes=1848)
summary=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-START,steps=steps,**values,new_native_runs=0,new_timing_samples=0,new_evaluation_population=False,independent_reproduction=False,scope='Exact fixed finite reruns and saved Java event reconstruction. Full-program and source/JMM proofs are not mechanically certified.')
with(OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

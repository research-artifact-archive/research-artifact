"""Replay cap/toll equations and the fixed per-update Roslyn comparison."""
from pathlib import Path
import hashlib,json,math,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=HERE/'evidence/RESUMED_20260910_0343';OUT=Path(sys.argv[2])
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(script,label,cap=180):
 with (OUT/(label+'.stdout')).open('xb') as stdout,(OUT/(label+'.stderr')).open('xb') as stderr:
  r=subprocess.run([sys.executable,'-B',str(script)],stdout=stdout,stderr=stderr,timeout=cap)
 assert r.returncode==0,(label,r.returncode)
def copy(source,dest,names):
 dest.mkdir(parents=True)
 for name in names:shutil.copyfile(source/name,dest/name)
def same(a,b,ignored=(),floating=False):
 if isinstance(a,dict):
  assert isinstance(b,dict) and set(a)==set(b)
  for k in a:
   if k not in ignored:same(a[k],b[k],ignored,floating)
 elif isinstance(a,list):
  assert isinstance(b,list) and len(a)==len(b)
  for x,y in zip(a,b):same(x,y,ignored,floating)
 elif floating and isinstance(a,float):assert isinstance(b,(int,float)) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(a,b)
 else:assert a==b,(a,b)
def contracts():
 summaries={}
 for folder,roots in [('full_kernel_toll_01',42084),('local_shared_caps_01',35796)]:
  source=BASE/folder;dest=OUT/folder;copy(source,dest,['PLAN.md','PROOF.md','run01.py']);run(dest/'run01.py',folder)
  for name in ['INPUTS.json','RAW.jsonl']:assert sha(dest/'run01'/name)==sha(source/'run01'/name),name
  fresh=read(dest/'run01/SUMMARY.json');old=read(source/'run01/SUMMARY.json');same(fresh,old,{'utc','seconds','peak_RSS_bytes'});assert fresh['status']=='PASS' and fresh['roots']==roots;summaries[folder]=fresh
 return dict(root_checks=77880,full_kernel_toll_roots=42084,local_shared_cap_roots=35796,known_local_cap_checks=8928,corruption_controls=8,summaries=summaries,scope='Fresh finite arithmetic corroboration. Broad program-class guarantees come from the operation-level proofs. No native run, new population or calibrated time model.')
def native_saved():
 source=BASE/'roslyn_per_job_01';dest=OUT/'roslyn_per_job_01';copy(source,dest,['PLAN.md','check01.py','semantic_base_check.py','analyze01.py'])
 shutil.copytree(source/'harness01',dest/'harness01');(dest/'run01').mkdir()
 for p in sorted((source/'run01').glob('p*/stdout.jsonl')):
  target=dest/'run01'/p.parent.name;target.mkdir();shutil.copyfile(p,target/p.name)
 run(dest/'check01.py','native_record_checker');new=read(dest/'run01/check01/RECEIPT.json');old=read(source/'run01/check01/RECEIPT.json');same(new,old,{'utc'});assert new['status']=='PASS' and new['planned_units']==3072
 assert sha(dest/'run01/check01/DETAILS.json')==sha(source/'run01/check01/DETAILS.json')
 run(dest/'analyze01.py','native_analysis');a=read(dest/'analysis01/SUMMARY.json');b=read(source/'analysis01/SUMMARY.json');same(a,b,{'utc','seconds'},floating=True)
 assert sha(dest/'analysis01/CELLS.tsv')==sha(source/'analysis01/CELLS.tsv');assert a['status']=='PASS' and len(a['cells'])==32 and len(a['paired_ratios'])==96
 rows=read(source/'figure01/SOURCE_ROWS.json');expected=[x for metric in ['foreground_us','writer_response_median_us','writer_service_median_us'] for x in a['paired_ratios'] if x['numerator']==['three',2] and x['denominator']==['two',2] and x['metric']==metric];same(rows,expected,floating=True)
 return dict(saved_native_units=3072,measurement=2560,warmup=512,source_native_seconds=237.83972600000197,per_update_counter_records=86016,corruption_controls=12,cells=32,paired_intervals=96,figure_points=12,float_tolerance='1e-12 relative/absolute for derived bootstrap statistics only; raw/checker/count outputs exact',scope='Recheck and reanalysis of unchanged native timeline records. Does not rerun native software or collect timing samples. Different cap scopes have different total-call contracts; policy-end write counts are not a shared causal intervention.')
if not __debug__:raise SystemExit('Assertions must be enabled.')
start=time.monotonic();stage=sys.argv[1];result={'cap-contracts':contracts,'roslyn-per-job':native_saved}[stage]()
summary=dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,replay_only=True,new_native_runs=0,new_timing_samples=0,**result)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

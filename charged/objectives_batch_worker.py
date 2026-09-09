"""Recompute two partial objectives and check all saved batch-rebase outcomes."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=HERE/'evidence/RESUMED_20260910_0343';OUT=Path(sys.argv[2])
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(p,label):
 r=subprocess.run([sys.executable,'-B',str(p)],capture_output=True,text=True,timeout=180)
 (OUT/(label+'.stdout')).write_text(r.stdout);(OUT/(label+'.stderr')).write_text(r.stderr)
 assert r.returncode==0,(label,r.returncode,r.stderr[-2000:])
def compare(a,b,ignored):
 assert set(a)==set(b)
 for k in b:
  if k not in ignored:assert a[k]==b[k],k
def objectives():
 compact=OUT/'partial_repair_compact_01';compact.mkdir()
 source=BASE/'partial_repair_compact_01'
 for name in ['compact01.py','compact02.py']:shutil.copyfile(source/name,compact/name)
 for folder,file in [('run01','outcomes.jsonl'),('extra01','OUTCOMES.json')]:
  (compact/folder).mkdir();shutil.copyfile(source/folder/file,compact/folder/file)
 checked=[]
 for name in ['partial_repair_regret_01','partial_repair_call_toll_01']:
  source=BASE/name;dest=OUT/name;dest.mkdir()
  for p in source.iterdir():
   if p.is_file() and p.suffix in ['.py','.md']:shutil.copyfile(p,dest/p.name)
  run(dest/'check01.py',name)
  receipt=read(dest/'run01/RECEIPT.json');assert receipt['status']=='PASS'
  compare(receipt,read(source/'run01/RECEIPT.json'),{'utc','seconds'})
  for p in (source/'run01').glob('*.json'):
   if p.name not in ['INPUT_RECEIPT.json','RECEIPT.json']:assert sha(dest/'run01'/p.name)==sha(p),(name,p.name)
  checked.append(receipt)
 return dict(regret_rows=4220,toll_profiles=16844,toll_known_budget_values=143226,toll_ratio_rows=33688,controls=15,studies=checked,scope='Exact recomputation against direct dirty-set games on retained constructed inputs, with regenerated profiles. No new native cost calibration or timing samples.')
def batch():
 source=BASE/'roslyn_rebase_batch_01/native01';n=read(source/'SUMMARY.json');assert n['status']=='SUCCESS'
 receipts={}
 for label,files in [('semantic_check',['check01.py']),('compiler_check',['check01.py','UNITS.tsv'])]:
  old=source/label;dest=OUT/label;dest.mkdir();(dest/'run01').mkdir()
  for f in files:shutil.copyfile(old/f,dest/f)
  if (old/'harness01').exists():shutil.copytree(old/'harness01',dest/'harness01')
  for p in (old/'run01').glob('*/stdout.jsonl'):
   target=dest/'run01'/p.parent.name/p.name;target.parent.mkdir();shutil.copyfile(p,target)
  run(dest/'check01.py',label);a=read(dest/'run01/check01/RECEIPT.json');b=read(old/'run01/check01/RECEIPT.json');assert a['status']=='PASS'
  compare(a,b,{'utc','checker_sha256','raw_sha256'});receipts[label]=a
 assert receipts['semantic_check']['units']==236 and receipts['compiler_check']['planned']==96
 reentries=[]
 for p in sorted((source/'logs').glob('reentry-*/stdout.txt')):
  rows=[json.loads(x) for x in p.read_text().splitlines()]
  if p.parent.name.startswith('reentry-error-'):
   assert len(rows)==1;x=rows[0];assert x['status']=='SUCCESS' and x['observed_exception']=='ArgumentException' and x['name_calls']==x['notifications']==1 and x['target_present'] is False and x['background']=='background revised from the error-name hook'
  else:
   assert len(rows)==2 and rows[0]=={'phase':'before_same_text_reentry','notifications':1};x=rows[-1];assert x['phase']=='terminal' and x['status']=='SUCCESS' and x['notifications']==x['completed_reentries']==1 and x['same_text_identity'] is True
  reentries.append(p.parent.name)
 assert len(reentries)==23
 old=BASE/'roslyn_rebase_batch_01/arrivals01';dest=OUT/'arrivals01';dest.mkdir();(dest/'harness01').mkdir();(dest/'run01').mkdir()
 for name in ['check01.py','analyze01.py']:shutil.copyfile(old/name,dest/name)
 for p in (old/'harness01').iterdir():
  if p.suffix=='.tsv' or p.name=='PROCESS_ORDER.json':shutil.copyfile(p,dest/'harness01'/p.name)
 for folder in sorted((old/'run01').glob('p*')):
  if not folder.is_dir():continue
  target=dest/'run01'/folder.name;target.mkdir()
  for name in ['RESULT.json','stdout.jsonl']:shutil.copyfile(folder/name,target/name)
 run(dest/'check01.py','arrivals-check');a=read(dest/'run01/check01/RECEIPT.json');assert a['status']=='PASS'
 compare(a,read(old/'run01/check01/RECEIPT.json'),{'utc','checker_sha256','raw_sha256'})
 run(dest/'analyze01.py','arrivals-analysis');b=read(dest/'analysis01/SUMMARY.json');assert b['status']=='PASS'
 compare(b,read(old/'analysis01/SUMMARY.json'),{'utc','source_checker_sha256','analysis_seconds'})
 assert sha(dest/'analysis01/CELLS.tsv')==sha(old/'analysis01/CELLS.tsv')
 return dict(semantic_units=236,reentry_processes=23,compiler_cases=96,arrival_batches=1728,warmup=288,measurement=1440,arrival_processes=36,arrival_controls=len(a['controls']),comparison_cells=len(b['comparisons']),native_receipts=receipts,scope='Every saved native projection and all arrival cells rechecked. Mixed and adverse timings preserved; observed protected spans exclude acquisition/release. This stage does not build Roslyn or rerun timing campaigns.')
if not __debug__:raise SystemExit('Assertions must be enabled.')
start=time.monotonic();stage=sys.argv[1];assert stage in ['partial-objectives','roslyn-batch']
result=(objectives if stage=='partial-objectives' else batch)()
summary=dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,replay_only=True,new_timing_samples=0,**result)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

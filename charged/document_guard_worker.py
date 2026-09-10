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
def document_guard():
 source=BASE/'roslyn_document_guard_01/native01';n=read(source/'SUMMARY.json');assert n['status']=='SUCCESS'
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
 old=BASE/'roslyn_rebase_batch_01/native01/compiler_check/run01'
 new=BASE/'roslyn_document_guard_01/native01/compiler_check/run01'
 changed=[];pairs=0
 for p in sorted(new.glob('u*/stdout.jsonl')):
  a=read(old/p.parent.name/'stdout.jsonl');b=read(p)
  assert [a[k] for k in ['id','mode','r','scenario','cache']]==[b[k] for k in ['id','mode','r','scenario','cache']]
  for label in ['initial','background','final']:
   assert next(x for x in a['snapshots'] if x['label']==label)['actual']==next(x for x in b['snapshots'] if x['label']==label)['actual']
  row={k:b[k] for k in ['id','mode','r','scenario','cache']}
  row.update(before_counters=a['counters'],after_counters=b['counters'],initial_background_final_projections_equal=True)
  if a['counters']!=b['counters']:changed.append(row)
  pairs+=1
 saved=read(BASE/'roslyn_document_guard_01/COMPARISON.json')
 assert pairs==saved['paired_cases']==96 and changed==saved['changed_resource_rows'] and len(changed)==4
 assert receipts['compiler_check']['counts']['project_projections']==2552
 return dict(semantic_units=236,reentry_processes=23,compiler_cases=96,compiler_project_projections=2552,changed_counter_cases=4,shared_snapshot_projections=288,native_receipts=receipts,scope='Saved native semantics and narrowed document-state guard rechecked; paired source-comparator outputs match. No new native build, timing samples, weakest-guard proof or native resource-price calibration.')
if not __debug__:raise SystemExit('Assertions must be enabled.')
start=time.monotonic();stage=sys.argv[1];assert stage=='roslyn-document-guard'
summary=dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,replay_only=True,new_timing_samples=0,**document_guard())
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)

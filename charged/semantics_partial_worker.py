"""Portable replay of fixed source semantics, retained failures, and partial-repair equations."""
from pathlib import Path
import copy,datetime,hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[2]);BASE=HERE/'evidence/RESUMED_20260910_0343'
PROVENANCE={r['path']:r for r in json.loads((HERE/'PROVENANCE.json').read_text())['files']}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def binding(p,h):
 row=PROVENANCE[str(p.relative_to(HERE))];assert row['source_sha256']==h and row['public_sha256']==sha(p),(p,'original/public binding')
def run(argv,cap=180):
 result=subprocess.run(argv,capture_output=True,text=True,timeout=cap)
 assert result.returncode==0,(argv,result.stdout[-1800:],result.stderr[-1800:]);return result
def clone_checker_inputs(d,dest):
 dest.mkdir();shutil.copyfile(d/'check01.py',dest/'check01.py');(dest/'harness01').mkdir();(dest/'run01').mkdir()
 for p in (d/'harness01').iterdir():
  if p.is_file() and (p.suffix=='.tsv' or p.name=='PROCESS_ORDER.json'):shutil.copyfile(p,dest/'harness01'/p.name)
 for p in (d/'run01').glob('*/stdout.jsonl'):
  target=dest/'run01'/p.parent.name/p.name;target.parent.mkdir();shutil.copyfile(p,target)
 result=run([sys.executable,'-B',str(dest/'check01.py')],120);(dest/'checker_stdout.txt').write_text(result.stdout);(dest/'checker_stderr.txt').write_text(result.stderr)
 new=read(dest/'run01/check01/RECEIPT.json');old=read(d/'run01/check01/RECEIPT.json');assert new['status']==old['status']=='PASS'
 # Every unmodified scientific field must agree; transport and wall-clock metadata are regenerated.
 for k in old:
  if k not in ['utc','checker_sha256','raw_sha256']:assert new[k]==old[k],(d,k)
 return new

def semantics():
 checked=[]
 for label,relative,expected in [('patch03','roslyn_semantics_01',178),('patch04','roslyn_patch04_01/semantics01',178),('rebase','roslyn_rebase_01/semantics01',236)]:
  r=clone_checker_inputs(BASE/relative,OUT/label);assert r['units']==expected
  checked.append(dict(version=label,units=r['units'],counts=r['counts'],controls=len(r['corruption_controls'])))
 write(OUT/'CHECKED.json',checked)
 return dict(units=592,groups=3,versions=checked,scope='All fixed source event/publication/payload/unchanged-state projections and native assertions, plus raw corruption controls; no arbitrary-host proof or new native timing samples.')

def check_error(row):
 assert row['status']=='SUCCESS' and row['observed_exception']=='ArgumentException'
 assert row['name_calls']==row['notifications']==1 and row['target_present'] is False
 assert row['background']=='background revised from the error-name hook'
def check_same(rows):
 assert len(rows)==2 and rows[0]=={'phase':'before_same_text_reentry','notifications':1}
 row=rows[1];assert row['phase']=='terminal' and row['status']=='SUCCESS'
 assert row['notifications']==row['completed_reentries']==1 and row['same_text_identity'] is True
def reentry():
 groups=[('patch03_errors','roslyn_error_reentry_01/run01',14),('patch04_errors','roslyn_patch04_01/error_run01',14),('patch04_same','roslyn_patch04_01/same_text_run01',4),('rebase_errors','roslyn_rebase_01/reentry_controls01/error/run01',18),('rebase_same','roslyn_rebase_01/reentry_controls01/same/run01',5)]
 timeouts={'u05_two_r0_missing_before','u06_two_r0_removed_between','u08_two_r1_removed_between','u10_three_r0_removed_between'}
 checked=[];examples={}
 for label,relative,expected in groups:
  folders=sorted(p.parent for p in (BASE/relative).glob('*/RESULT.json'));assert len(folders)==expected,(relative,len(folders))
  for folder in folders:
   result=read(folder/'RESULT.json');raw=folder/'stdout.jsonl';rows=[json.loads(x) for x in raw.read_text().splitlines()];binding(raw,result['stdout_sha256'])
   stderr=next(folder.glob('stderr.*'));binding(stderr,result['stderr_sha256'])
   timeout=label=='patch03_errors' and folder.name in timeouts
   assert result['status']==('TIMEOUT' if timeout else 'SUCCESS'),(label,folder.name)
   if timeout:assert rows==[] and result['returncode']!=0
   elif label.endswith('same'):check_same(rows);examples['same']=rows
   else:assert len(rows)==1;check_error(rows[0]);examples['error']=rows[0]
   if isinstance(result.get('rows'),list):assert result['rows']==rows
   elif isinstance(result.get('rows'),int):assert result['rows']==len(rows)
   if 'record' in result:assert result['record']==rows
   checked.append({'group':label,'unit':folder.name,'original_status':result['status'],'raw_records':len(rows)})
 controls=[]
 for name in ['name_calls','notifications','target_present','observed_exception']:
  x=copy.deepcopy(examples['error']);x[name]=True if name=='target_present' else 'WrongException' if name=='observed_exception' else 2
  try:check_error(x);detected=False
  except (AssertionError,KeyError,TypeError):detected=True
  assert detected;controls.append(dict(name='error_'+name,detected=detected))
 x=copy.deepcopy(examples['same']);x[-1]['completed_reentries']=0
 try:check_same(x);detected=False
 except (AssertionError,KeyError,TypeError):detected=True
 assert detected;controls.append(dict(name='same_completion',detected=True))
 write(OUT/'CHECKED.json',checked);write(OUT/'CONTROLS.json',controls)
 return dict(processes=55,successes=51,retained_timeouts=4,controls=5,scope='Original failure receipts are preserved as TIMEOUT; repaired error-hook and same-text executions are checked separately. This is a saved-output replay, not a rerun or general host-reentrancy guarantee.')

def arrivals():
 groups=[('initial','roslyn_arrivals_01',864,'analyze01.py','analysis01'),('balanced','roslyn_arrivals_balanced_01',1728,'analyze01.py','analysis01'),('rebase','roslyn_rebase_01/arrivals01',3072,'analyze02.py','analysis02')]
 checked=[]
 for label,relative,expected,script,analysis in groups:
  d=BASE/relative;dest=OUT/label;r=clone_checker_inputs(d,dest);assert r['planned_units']==r['raw_units']==expected
  shutil.copyfile(d/script,dest/script);result=run([sys.executable,'-B',str(dest/script)],120);(dest/'analysis_stdout.txt').write_text(result.stdout)
  new=read(dest/analysis/'SUMMARY.json');old=read(d/analysis/'SUMMARY.json')
  for k in old:
   if k not in ['utc','source_checker_sha256']:assert new[k]==old[k],(label,k)
  assert sha(dest/analysis/'CELLS.tsv')==sha(d/analysis/'CELLS.tsv')
  checked.append(dict(label=label,units=expected,measurement=new['measurement'],warmup=new['warmup'],cells=len(new['cells']),controls=len(r['controls'])))
 write(OUT/'CHECKED.json',checked)
 return dict(units=5664,measurement=4720,warmup=944,studies=checked,scope='Every fixed raw unit, publication timeline, resource counter, cell and per-fork descriptive statistic is replayed. Initial order confounding and rebase protected merge work remain explicit. No new timing data or calibrated total-work model.')

def partial():
 results=[]
 for label,relative,expected_i,expected_r in [('zero_baseline','partial_repair_01',3495,160080),('common_baseline','partial_repair_baseline_01',1046,20920)]:
  d=BASE/relative;dest=OUT/label;dest.mkdir()
  for name in ['PLAN.md','check01.py']:shutil.copyfile(d/name,dest/name)
  r=run([sys.executable,'-B',str(dest/'check01.py')],180);(dest/'stdout.txt').write_text(r.stdout);(dest/'stderr.txt').write_text(r.stderr)
  new=read(dest/'run01/RECEIPT.json');old=read(d/'run01/RECEIPT.json')
  assert new['status']==old['status']=='PASS' and new['instances']==expected_i and new['rows']==expected_r
  for p in (d/'run01').glob('*.json*'):
   if p.name not in ['RECEIPT.json','INPUT_RECEIPT.json']:assert sha(dest/'run01'/p.name)==sha(p),(label,p.name)
  results.append(dict(label=label,instances=expected_i,rows=expected_r,strict_improvement_rows=new.get('strict_improvement_rows'),source_controls=new['controls']))
 write(OUT/'CHECKED.json',results)
 return dict(studies=results,scope='Exact arithmetic recomputation in two distinct partial-repair interfaces. Original deterministic policies, all ties and counterexamples retained. Some source controls are algebra/schema checks, not independent raw mutation tests. No mechanical proof, native calibration or novelty certification.')

if not __debug__:raise SystemExit('Assertions must be enabled.')
stage=sys.argv[1];start=time.monotonic();result={'roslyn-semantics':semantics,'roslyn-reentry':reentry,'roslyn-arrivals':arrivals,'partial-repair':partial}[stage]()
summary=dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,quick=False,replay_only=True,new_evaluation_samples=0,**result);write(OUT/'SUMMARY.json',summary);print(json.dumps(summary),flush=True)

"""Portable replay of fixed resumed-session evidence; no new native timing samples."""
from pathlib import Path
from collections import Counter,defaultdict
import ast,copy,hashlib,json,shutil,statistics,subprocess,sys,time
HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[2]);BASE=HERE/'evidence/RESUMED_20260909_1413';PROVENANCE={r['path']:r for r in json.loads((HERE/'PROVENANCE.json').read_text())['files']}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def binding(p,original_hash):
 row=PROVENANCE[str(p.relative_to(HERE))]
 assert row['source_sha256']==original_hash and row['public_sha256']==sha(p),(p,'source/public binding')
def run(argv,cap=180):
 result=subprocess.run(argv,capture_output=True,text=True,timeout=cap)
 assert result.returncode==0,(argv,result.stdout[-1200:],result.stderr[-1800:]);return result

def adaptive():
 d=BASE/'universal_adaptive_work_01';fresh=OUT/'fresh';fresh.mkdir()
 for name in ['study.py','OBSERVED_INPUTS.json']:shutil.copyfile(d/name,fresh/name)
 run([sys.executable,'-B',str(fresh/'study.py')],120)
 result=read(fresh/'SUMMARY.json');old=read(d/'SUMMARY.json')
 assert result['status']=='SUCCESS' and result['roots']==176608 and result['cases']==5519 and result['counts']==old['counts']
 assert sha(fresh/'RESULTS.jsonl')==sha(d/'RESULTS.jsonl')
 return dict(cases=5519,roots=176608,scope='Exact finite equations within the global-threshold family; no arbitrary-program optimum or new native measurement')

def probe():
 d=BASE/'probe_blocking_01';source=d/'check_and_analyze_v2.py'
 # Import the original pure validators/reference functions, without the NumPy-only descriptive bootstrap driver.
 module=ast.parse(source.read_text());chosen=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['key','validate','reference']]
 assert {n.name for n in chosen}=={'key','validate','reference'};ns={};exec(compile(ast.Module(body=chosen,type_ignores=[]),str(source),'exec'),ns)
 key,validate,reference=(ns[n] for n in ['key','validate','reference']);raw=[];pairs=defaultdict(dict)
 for name,h in read(d/'INPUT_RECEIPT.json')['files'].items():binding(d/name,h)
 for fork in range(1,4):
  rows=[json.loads(x) for x in (d/f'fork{fork}/stdout.jsonl').read_text().splitlines()];units=read(d/f'FORK{fork}_UNITS.json');planned={key(x) for x in units}
  assert len(planned)==len(units)==len(rows)==1920 and {key(x) for x in rows}==planned
  assert [x['sequence'] for x in rows]==list(range(len(rows))) and all(a['process_elapsed_ns']<b['process_elapsed_ns'] for a,b in zip(rows,rows[1:]))
  for x in rows:
   assert x['status']=='SUCCESS' and not validate(x),(key(x),validate(x));raw.append(x)
   pair=pairs[key(x)[:-1]];assert x['policy'] not in pair;pair[x['policy']]=x
 refs={f'{s}:{r}':reference(s,r) for s in [64,2048,65536,2097152] for r in range(3)}
 assert refs==read(d/'recheck02/SEQUENTIAL_REFERENCE.json')
 for x in raw:assert x['seeds']==refs[f"{x['scale']}:{x['r']}"]
 for pair in pairs.values():assert set(pair)=={'two','three'} and pair['two']['seeds']==pair['three']['seeds']
 sample=next(x for x in raw if x['layout']=='same_bin' and x['policy']=='three');assert not validate(sample)
 mutations=[('wrong_L',lambda x:x.update(L=1)),('wrong_Q',lambda x:x.update(Q=100)),('wrong_versions',lambda x:x.update(versions=[-1]*4)),('missing_probe',lambda x:x['probes'].pop()),('early_entry',lambda x:x['probes'][0].update(entry_ns=x['probes'][0]['body_end_ns']-1)),('wrong_interval',lambda x:x.update(wait_sum_ns=-1)),('hidden_inside_kernel',lambda x:x.update(kernel_in_ns=1))]
 def overlap(x):
  x['probes'][1]=dict(x['probes'][0],job=1);x['wait_sum_ns']=sum(p['wait_ns'] for p in x['probes']);x['wait_max_ns']=max(p['wait_ns'] for p in x['probes'])
 mutations.append(('cross_job_overlap',overlap))
 for field in ['setup_ns','kernel_out_ns','process_elapsed_ns','foreground_ns']:mutations.append(('negative_'+field,lambda x,field=field:x.update({field:-1})))
 controls=[]
 for name,change in mutations:
  x=copy.deepcopy(sample);change(x);errors=validate(x);assert errors,name;controls.append({'name':name,'rejected':True,'errors':errors})
 original=read(d/'recheck02/SUMMARY.json');cells=[]
 for old in original['cells']:
  xs=[p for k,p in pairs.items() if k[1]=='measure' and k[3]==old['scale'] and k[4]==old['r'] and k[5]==old['layout']];assert len(xs)==old['pairs']==90
  a=statistics.median(p['two']['wait_sum_ns'] for p in xs);b=statistics.median(p['three']['wait_sum_ns'] for p in xs);diff=statistics.median(p['two']['wait_sum_ns']-p['three']['wait_sum_ns'] for p in xs)
  assert (a,b,diff,a/b)==(old['two_median_ns'],old['three_median_ns'],old['paired_difference_median_ns'],old['two_over_three_ratio_of_medians'])
  for f in old['forks']:
   sub=[p for p in xs if p['two']['fork']==f['fork']];assert len(sub)==f['pairs']==30
   for name,values in [('two_median_ns',[p['two']['wait_sum_ns'] for p in sub]),('three_median_ns',[p['three']['wait_sum_ns'] for p in sub]),('paired_difference_median_ns',[p['two']['wait_sum_ns']-p['three']['wait_sum_ns'] for p in sub])]:assert statistics.median(values)==f[name]
  for policy,fields in old['secondary'].items():
   for field,value in fields.items():assert statistics.median(p[policy][field] for p in xs)==value
  cells.append({'scale':old['scale'],'r':old['r'],'layout':old['layout'],'two_median_ns':a,'three_median_ns':b,'paired_difference_median_ns':diff})
 write(OUT/'REFERENCE.json',refs);write(OUT/'CONTROLS.json',controls);write(OUT/'MEDIANS.json',cells)
 return dict(measured=4320,warmup=1440,measured_probes=17280,paired_invocations=2160,cells=24,controls=12,scope='Original validator/reference functions and complete fixed raw/median reconstruction. NumPy bootstrap interval bytes are provenance-verified but not recomputed by this standard-library stage; no timing rerun.')

def roslyn():
 d=BASE/'roslyn_source_01';checkers=OUT/'checkers';checkers.mkdir();shutil.copyfile(d/'check_native.py',checkers/'check_native.py')
 source=d/'check_repository01.py';s=source.read_text();old_manifest_hash=PROVENANCE[str((d/'repository_inputs02/MANIFEST.json').relative_to(HERE))]['source_sha256']
 needle="hashlib.sha256(manifest.read_bytes()).hexdigest():issues.append({'manifest_binding':x['id']})"
 assert s.count(needle)==1
 adapted=s.replace(needle,repr(old_manifest_hash)+":issues.append({'manifest_binding':x['id']})");(checkers/'check_repository01.py').write_text(adapted)
 write(OUT/'TRANSPORT_ADAPTER.json',{'source_checker_public_sha256':sha(source),'adapted_sha256':sha(checkers/'check_repository01.py'),'change':'Compare native-record source_manifest_sha256 to the original manifest hash, authenticated by public provenance, because only author-local path prefixes were projected in the published manifest. No semantic predicate or denominator changed.','original_manifest_sha256':old_manifest_hash,'public_manifest_sha256':sha(d/'repository_inputs02/MANIFEST.json')})
 jobs=[]
 for version in ['development01','development03']:
  for mode,runs in [('baseline','BASELINE_RUNS.tsv'),('patched','DEVELOPMENT_RUNS.tsv')]:jobs.append((version+'/'+mode,d/version/mode/'stdout.jsonl',d/'harness01'/runs,'check_native.py'))
 for mode,runs in [('baseline','BASELINE_RUNS.tsv'),('patched','DEVELOPMENT_RUNS.tsv')]:jobs.append(('repository_development01/'+mode,d/'repository_development01'/mode/'stdout.jsonl',d/'harness_repo01'/runs,'check_repository01.py'))
 for version,checker in [('measurement01','check_native.py'),('repository_measurement01','check_repository01.py')]:
  for f in range(1,4):jobs.append((version+f'/fork{f}',d/version/f'fork{f}/stdout.jsonl',d/version/f'FORK{f}_RUNS.tsv',checker))
 checked=[]
 for label,raw,runs,checker in jobs:
  target=OUT/label;target.mkdir(parents=True);shutil.copyfile(raw,target/'stdout.jsonl');shutil.copyfile(runs,target/'RUNS.tsv')
  r=run([sys.executable,'-B',str(checkers/checker),'--runs',str(target/'RUNS.tsv'),'--raw',str(target/'stdout.jsonl'),'--out',str(target/'check')],60)
  (target/'checker_stdout.txt').write_text(r.stdout);receipt=read(target/'check/CHECK_RECEIPT.json');assert receipt['status']=='PASS' and receipt['observed']==receipt['expected']
  checked.append({'label':label,'rows':receipt['observed'],'controls':len(receipt['controls']),'scope':'zero-writer unmodified-library content/count/order control; no trace/mutation check' if label.endswith('baseline') else 'Original semantic checker with documented event-payload and SourceText-only limitations'})
 for version,summary in [('measurement01','SUMMARY_RECONSTRUCTED.json'),('repository_measurement01','SUMMARY.json')]:
  run([sys.executable,'-B',str(d/'summarize_measurements.py'),str(OUT/version),'--output',str(OUT/version/'SUMMARY.json')],60)
  new,old=read(OUT/version/'SUMMARY.json'),read(d/version/summary)
  for key in ['all_units','measured_units','warmup_units','counts','aggregate','foreground_paired_median_signs','cells','comparisons']:assert new[key]==old[key],(version,key)
 reentry=[]
 for version in ['reentry_outcomes01','reentry_outcomes02']:
  for mode in ['baseline','original','two','three']:
   target=d/version/mode;r=read(target/'RESULT.json');raw=[json.loads(x) for x in (target/'stdout.jsonl').read_text().splitlines()];binding(target/'stdout.jsonl',r['stdout_sha256'])
   expected='TIMEOUT' if version=='reentry_outcomes01' and mode=='two' else 'SUCCESS';assert r['status']==expected and r['rows']==raw
   if expected=='TIMEOUT':assert raw==[{'phase':'before_same_text_reentry','notifications':1}]
   else:
    x=raw[-1];assert x['phase']=='terminal' and x['status']=='SUCCESS' and x['notifications']==1 and x['completed_reentries']==1 and x['same_text_identity'] is True
   reentry.append({'version':version,'mode':mode,'original_status':expected})
 write(OUT/'CHECKED_GROUPS.json',checked);write(OUT/'REENTRY_OUTCOMES.json',reentry)
 return dict(native_records=sum(x['rows'] for x in checked),groups=len(checked),reentry_records=8,retained_reentry_timeouts=1,authored_measured=3960,repository_measured=990,scope='Complete original trace/checker and descriptive-summary replay, with source/public manifest transport binding. SourceText identities are asserted by the native harness; event payloads and arbitrary host/reentrant equivalence are not established. No native execution or new timing samples.')

def tail(native=False):
 d=BASE/'protected_tail_01';fresh=OUT/'fresh';fresh.mkdir()
 for name in ['study.py','INPUTS.json','check_native.py','NATIVE_INPUTS.json']:shutil.copyfile(d/name,fresh/name)
 if not native:
  run([sys.executable,'-B',str(fresh/'study.py')],240);result=read(fresh/'SUMMARY.json');original=read(d/'SUMMARY.json')
  assert result['status']=='SUCCESS' and result['roots']==176640 and result['strict_W_improvements_by_r']==original['strict_W_improvements_by_r']
  assert sha(fresh/'RESULTS.jsonl')==sha(d/'RESULTS.jsonl');raw=d/'native01/native/stdout.txt'
 else:
  import os
  classes=OUT/'classes';classes.mkdir();java=os.environ.get('JAVA_BIN','java');javac=os.environ.get('JAVAC_BIN','javac')
  run([javac,'--release','17','-d',str(classes),str(d/'TailProbe.java')],60)
  r=run([java,'-cp',str(classes),'TailProbe',str(d/'NATIVE_RUNS.tsv')],180);raw=OUT/'native.jsonl';raw.write_text(r.stdout)
 run([sys.executable,'-B',str(fresh/'check_native.py'),'--raw',str(raw),'--out',str(OUT/'native-check')],60)
 checked=read(OUT/'native-check/CHECK_RECEIPT.json');assert checked['status']=='PASS' and checked['expected_units']==2552 and checked['groups']==144
 assert sha(OUT/'native-check/MAXIMA.json')==sha(d/'native01/check01/MAXIMA.json')
 return dict(equation_roots=0 if native else 176640,equation_inputs=0 if native else 5520,native_paths=2552,groups=144,controls=8,strict_equation_improvements=285,scope='Fixed equations plus all saved native branches' if not native else 'New JDK executions of fixed authored branches; no timing-campaign samples or new population',general_W_optimality=False)

if not __debug__:raise SystemExit('Assertions must be enabled.')
stage=sys.argv[1];start=time.monotonic()
result={'adaptive-work':adaptive,'probe-blocking':probe,'roslyn-source':roslyn,'protected-tail':tail,'protected-tail-java':lambda:tail(True)}[stage]()
summary=dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,quick=False,replay_only=True,new_evaluation_samples=0,**result);write(OUT/'SUMMARY.json',summary);print(json.dumps(summary),flush=True)

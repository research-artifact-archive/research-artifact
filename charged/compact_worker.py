"""Portable replays of preserved compact evidence; no new timing population."""
from pathlib import Path
import collections,copy,gzip,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
HERE=Path(__file__).resolve().parent
DATA=HERE/'evidence/RESUMED_20260909_0056'
OUT=Path(sys.argv[2]);QUICK='--quick' in sys.argv[3:]
_PROVENANCE=None
def provenance():
 global _PROVENANCE
 if _PROVENANCE is None:
  rows=json.loads((HERE/'PROVENANCE.json').read_text())['files']
  _PROVENANCE={r.get('logical_path',r['path']):r for r in rows}
  assert len(_PROVENANCE)==len(rows)
 return _PROVENANCE
def read(p):
 p=Path(p)
 try:relative=str(p.relative_to(HERE))
 except ValueError:relative=None
 record=provenance().get(relative) if relative and p.name!='PROVENANCE.json' else None
 if record and record.get('storage_encoding')=='gzip':
  assert not p.exists(),'unexpected unlisted file shadows compressed logical input'
  encoded=(HERE/record['path']).read_bytes()
  assert len(encoded)==record['public_bytes'] and hashlib.sha256(encoded).hexdigest()==record['public_sha256']
  decoded=gzip.decompress(encoded)
  assert len(decoded)==record['decoded_bytes'] and hashlib.sha256(decoded).hexdigest()==record['decoded_sha256']
  return json.loads(decoded)
 return json.loads(p.read_text())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def save(name,x):
 with (OUT/name).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 sys.path.insert(0,str(p.parent));spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def select(rows,n=12):return rows[:n] if QUICK else rows
def indexed(rows):
 x={r['id']:r for r in rows};assert len(x)==len(rows);return x
def compact():
 core=DATA/'charged_compact_03';prior=DATA/'charged_compact_02';binding=read(core/'SEMANTIC_SOURCE_BINDING.json')
 for name,item in binding['unchanged'].items():assert sha(core/name)==sha(prior/name)==item['sha256']
 for original_path,digest in binding['evidence'].items():
  prefix='RESEARCH_RESTART_20260905/';assert original_path.startswith(prefix)
  path='evidence/'+original_path[len(prefix):];record=provenance()[path]
  assert record['source_sha256']==digest and sha(HERE/record['path'])==record['public_sha256'],path
 constructor=load('compact',core/'compact.py');checker=load('verify',core/'verify.py');runtime=load('runtime',core/'runtime.py')
 conf=load('compact_conformance',prior/'conformance.py')
 assert conf.compact is constructor and conf.verify is checker and conf.Policy is runtime.Policy
 inputs=read(prior/'conformance01/INPUTS.json');old=indexed(lines(prior/'conformance01/RAW.jsonl'));assert len(inputs)==len(old)==19485 and {i['id'] for i in inputs}==set(old)
 results=[];branches=0;routes=collections.Counter();reference=constructor.general_constructor().compiler
 with (OUT/'RESULTS.jsonl').open('x') as out:
  for item in select(inputs):
   case=item['case'];artifact=checker.loads(json.dumps(constructor.compile_case(case)));checked=checker.check(artifact,case)
   oracle=reference.compile_case(case);profile=conf.profile(artifact)
   assert profile==oracle['curves'][oracle['full']]
   policy=runtime.Policy(artifact,case);totals,count=conf.policy_check(policy)
   previous=old[item['id']]
   assert previous['status']=='SUCCESS' and artifact['route']==previous['route']
   assert json.loads(json.dumps(profile))==previous['whole_profile'] and totals==previous['policy_totals'] and count==previous['policy_branches']
   row=dict(id=item['id'],status='SUCCESS',route=artifact['route'],policy_totals=totals,branches=count,check=checked)
   out.write(json.dumps(row,separators=(',',':'))+'\n');results.append(row);branches+=count;routes[artifact['route']]+=1
 controls=conf.controls();assert len(controls)==29 and all(r['met'] for r in controls)
 save('CONTROLS.json',controls)
 cli_dir=core/'cli_conformance01';units=read(cli_dir/'MANIFEST.json')['units'];cli_results=[]
 assert len(units)==14
 for u in units:
  argv=[sys.executable,'-B',str(DATA/u['version']/'cli.py'),u['command']]
  if u['command']=='compile':argv+=['--out',str(OUT/(u['id']+'_artifact.json'))]
  else:argv+=['--artifact',str(cli_dir/'artifact.json')]
  if u['command']=='query':argv+=['--budgets','0','1','2']
  if u['input']!='omitted':argv+=['--input',str(cli_dir/(u['input']+'.json'))]
  result=subprocess.run(argv,capture_output=True,text=True,timeout=3)
  (OUT/(u['id']+'.stdout')).write_text(result.stdout);(OUT/(u['id']+'.stderr')).write_text(result.stderr)
  assert (result.returncode==0)==u['accept'],u
  if not u['accept']:
   expected=(cli_dir/(u['id']+'.stderr')).read_text().splitlines()[-1]
   assert result.returncode==1 and result.stderr.splitlines()[-1]==expected,u['id']
  cli_results.append(dict(id=u['id'],version=u['version'],returncode=result.returncode,expected_accept=u['accept'],met=True,argv=argv))
 save('CLI_CONTROLS.json',cli_results)
 if not QUICK:assert branches==527409 and dict(routes)=={'compatible_reduced':16770,'charged_all_ideals':2715}
 return dict(retained_inputs=19485,replayed=len(results),routes=dict(routes),policy_branches=branches,controls=29,cli_controls=14,prior_null_acceptances_retained=2,core_semantic_identity=True,new_evaluation_samples=0)

def compact_native(java=False):
 d=DATA/'charged_compact_native_01';attempt=d/'attempt01';causal=load('causal',d/'causal.py')
 model=causal.model;sequence=causal.sequence_checker
 cases=indexed(read(attempt/'CASES.json'));runs=read(attempt/'RUNS.json');runmap=indexed(runs)
 retained=indexed(lines(attempt/'RAW.jsonl'));assert len(retained)==len(runs)==610 and len(cases)==26
 assert set(retained)==set(runmap);raw=retained
 if java:
  java_bin=os.environ.get('JAVA_BIN','java');javac=os.environ.get('JAVAC_BIN','javac')
  removed=['JDK_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVAC_OPTIONS']
  java_env={k:v for k,v in os.environ.items() if k not in removed}
  save('JAVA_ENVIRONMENT_POLICY.json',dict(removed_launcher_environment_names=removed,removed_present=[k for k in removed if k in os.environ],values_not_recorded=True))
  version=subprocess.check_output([java_bin,'-version'],stderr=subprocess.STDOUT,text=True,env=java_env);assert 'version "17.' in version,'native replay requires Java17'
  target=OUT/'java-input';target.mkdir();classes=OUT/'classes';classes.mkdir()
  for p in attempt.glob('*.tsv'):shutil.copy2(p,target/p.name)
  shutil.copy2(d/'CompactChargedCallbacks.java',target/'CompactChargedCallbacks.java')
  comp=subprocess.run([javac,'--release','17','-d',str(classes),str(target/'CompactChargedCallbacks.java')],capture_output=True,timeout=30,env=java_env)
  (OUT/'javac.stdout').write_bytes(comp.stdout);(OUT/'javac.stderr').write_bytes(comp.stderr);assert comp.returncode==0
  with (OUT/'NEW_NATIVE_RAW.jsonl').open('xb') as out,(OUT/'java.stderr').open('xb') as err:
   result=subprocess.run([java_bin,'-ea','-cp',str(classes),'CompactChargedCallbacks',str(target)],stdout=out,stderr=err,timeout=180,env=java_env)
  assert result.returncode==0;raw=indexed(lines(OUT/'NEW_NATIVE_RAW.jsonl'));assert set(raw)==set(runmap)
  save('JAVA_VERSION.json',dict(version=version,source_sha256=sha(target/'CompactChargedCallbacks.java')))
 chosen=select([r for r in runs if not r['control']])+[r for r in runs if r['control']];results=[];groups={};expected_groups=collections.Counter()
 for r in runs:
  if not r['control'] and r['kind']=='replay':expected_groups[r['case'],r['budget'],r['layout']]+=1
 with (OUT/'VERIFICATION.jsonl').open('x') as output,(OUT/'CERTIFICATES.jsonl').open('x') as certificates:
  for r in chosen:
   row=raw[r['id']];assert row['status']=='SUCCESS';v=causal.verify(cases[r['case']],r,row)
   assert v['accepted']==r['expected_accept'],(r['id'],v)
   if 'certificate' in v:
    certificate=v.pop('certificate');certificates.write(json.dumps(dict(id=r['id'],certificate=certificate),separators=(',',':'))+'\n')
    v['certificate_sha256']=model.digest(certificate)
   v.update(id=r['id'],expected_accept=r['expected_accept']);output.write(json.dumps(v,separators=(',',':'))+'\n');results.append(v)
   if not r['control'] and r['kind']=='replay':
    key=r['case'],r['budget'],r['layout'];g=groups.setdefault(key,dict(count=0,maximum=0,ceiling=v['static']['ceiling']));g['count']+=1;g['maximum']=max(g['maximum'],v['static']['cost'])
 if not QUICK:
  assert len(groups)==208
  for key,g in groups.items():assert g['count']==expected_groups[key] and g['maximum']==g['ceiling'],(key,g)
 # Fixed adversarial controls always replay their retained raw source; they are
 # not replaced with a different concurrent schedule from the optional Java run.
 record_controls=[]
 for item in read(attempt/'RECORD_CONTROLS.json'):
  r=item['run'];v=causal.verify(cases[r['case']],r,item['row'])
  assert v['accepted']==item['expected_accept'] and v['status']==item['expected_status']
  if not item['expected_accept']:assert v.get('layer')==item['expected_layer'] and v.get('reason')==item['result'].get('reason')
  v.pop('certificate',None);record_controls.append(dict(id=item['id'],result=v))
 target=read(attempt/'CONTROL_TARGETS.json')['cached_failure'];r=runmap[target];program=model.build(cases[r['case']],r,retained[target]);seq=[]
 for item in read(attempt/'SEQUENCE_CONTROLS.json'):
  try:sequence.check(program,item['certificate']);accepted=True
  except AssertionError:accepted=False
  assert accepted==item['expected_accept'];seq.append(dict(id=item['id'],accepted=accepted))
 parser=[]
 for item in read(attempt/'PARSER_CONTROLS.json'):
  if java:
   directory=attempt/'parser_inputs'/item['id'];result=subprocess.run([java_bin,'-ea','-cp',str(classes),'CompactChargedCallbacks',str(directory)],capture_output=True,text=True,timeout=3,env=java_env)
   stdout,stderr,code=result.stdout,result.stderr,result.returncode
   (OUT/('parser_'+item['id']+'.stdout')).write_text(stdout);(OUT/('parser_'+item['id']+'.stderr')).write_text(stderr)
  else:
   stdout=(attempt/('parser_'+item['id']+'.stdout')).read_text();stderr=(attempt/('parser_'+item['id']+'.stderr')).read_text();code=item['returncode']
  if item['expected_accept']:assert code==0 and not stdout and not stderr
  else:assert code==1 and not stdout and stderr.splitlines()[0]==item['expected_error']
  parser.append(dict(id=item['id'],returncode=code,expected_accept=item['expected_accept'],native_reexecuted=java))
 assert len(record_controls)==8 and len(seq)==5 and len(parser)==9
 save('RECORD_CONTROLS.json',record_controls);save('SEQUENCE_CONTROLS.json',seq);save('PARSER_CONTROLS.json',parser)
 save('REPLAY_CELLS.json',[dict(case=k[0],budget=k[1],layout=k[2],**v) for k,v in groups.items()])
 return dict(retained_runs=610,retained_primary=606,replayed_records=len(results),replay_cells=len(groups),record_controls=8,sequence_controls=5,parser_controls=9,parser_native_reexecuted=java,new_native_replay_records=len(raw) if java else 0,new_evaluation_samples=0,scope='Original-price fixed-order policy plus existential ordering under the fixed source model; no original causal certificate is reused for new native records.')

def compact_scale():
 core=DATA/'charged_compact_03';load('compact',core/'compact.py');checker=load('verify',core/'verify.py');runtime=load('runtime',core/'runtime.py')
 expected_scopes={'PACK':'ALL_BUDGET_ORIGINAL_CHARGED_CURSOR_POLICY','ROOT':'REDUCTION_AWARE_ALL_BUDGET_ROOT_VALUE_ONLY_NO_INDEPENDENT_CERTIFICATE','ALL':'ALL_BUDGET_ALL_REACHABLE_UNFINISHED_SETS_POLICY','PEAK':'REQUESTED_ROOT_VALUES','DP':'VALUES_ONLY_NO_INDEPENDENT_CERTIFICATE'}
 reports=[];all_checks=[]
 for study,count in [('charged_compact_scale_01',420),('charged_compact_scale_02',180)]:
  d=DATA/study;attempt=d/'attempt01';raw=lines(attempt/'RAW.jsonl');units=read(attempt/'UNITS.json');unitmap=indexed(units)
  cases=indexed(read(attempt/'CASES.json'));rowmap=indexed(raw);assert len(raw)==len(units)==count and set(rowmap)==set(unitmap)
  point=load(study+'_point',d/'point_checker.py');certified={};shared={};full_roots={};checks=[];status_counts=collections.Counter();reasons=collections.Counter();services=collections.Counter()
  summary=read(attempt/('SUMMARY.json' if study.endswith('_01') else 'SUMMARY_RECOVERED_01.json'))
  assert dict(collections.Counter(r['status'] for r in raw))==summary['statuses']
  for method in ['PACK','ROOT','ALL','PEAK','DP']:
   assert dict(collections.Counter(r['status'] for r in raw if r['method']==method))==summary['by_method'][method]['statuses']
  for row in raw:
   u=unitmap[row['id']];status_counts[row['status']]+=1
   assert all(row[k]==u[k] for k in ['case_id','method','budgets','seconds_cap'])
   assert row==read(attempt/'runs'/row['id']/'PROCESS.json')
   if row['status']!='SUCCESS':reasons[row.get('reason','')]+=1;continue
   result=row['worker_result'];assert result==read(attempt/'runs'/row['id']/'RESULT.json')
   assert result['status']=='SUCCESS' and result['budgets']==u['budgets']
   assert result['method']==u['method'] and result['certificate_scope']==expected_scopes[u['method']]
   assert result['baseline']==sum(w+min(v,g+r) for w,p,g,v,r in u['case']['jobs'])
   assert len(result['values'])==len(u['budgets']);services[result['certificate_scope']]+=1
   for b,v in zip(u['budgets'],result['values']):
    key=u['case_id'],b
    assert key not in shared or shared[key]==v,(study,key)
    shared[key]=v
   if study.endswith('_02'):
    c=cases[u['case_id']];n,M,A=c['n'],c['copies'],c['scale'];expected=[]
    for b in u['budgets']:
     q,r=divmod(min(b,n*(M+1)),M+1);expected.append(A*((M+1)*q*(2*n-q+1)-q+2*(n-q)*r))
    assert expected==u['expected_values']==result['values'] and result['baseline']==c['expected_baseline']
   method=row['method'];do_check=not QUICK or sum(x['method']==method for x in checks)<4
   if not do_check:continue
   path=attempt/'runs'/row['id']/('VALUES.json' if method=='DP' else 'ARTIFACT.json')
   artifact=read(path);assert path.stat().st_size==result['certificate_bytes']
   if method in ['PACK','ALL']:
    assert artifact['input']==u['case'];policy=runtime.Policy(artifact,u['case']);vs=[policy.excess(b) for b in u['budgets']]
    if method=='ALL':assert artifact['route']=='charged_all_ideals'
    assert [policy.choose(b) for b in u['budgets']]==result['initial_actions']
    for b,v in zip(u['budgets'],vs):certified[u['case_id'],b]=v
    if method=='PACK':
     assert artifact['route']=='compatible_reduced';full_roots[u['case_id']]=artifact['backend']['value_slopes']
     if study.endswith('_02'):
      expected_runs=[]
      for j in range(n,0,-1):expected_runs.extend([[2*j*A,M],[(2*j-1)*A,1]])
      assert artifact['backend']['value_slopes']==expected_runs
   elif method=='PEAK':
    assert artifact['input']==u['case'] and artifact['budgets']==u['budgets'];vs=point.check(artifact)['values']
   elif method=='ROOT':
    assert artifact['input']==u['case'] and artifact['baseline']==result['baseline'] and artifact['schema']=='charged-reduced-root-value-only-v1'
    vs=[]
    for b in u['budgets']:
     left=b;area=0
     for height,length in artifact['value_slopes']:
      assert type(height) is int and height>0 and type(length) is int and length>0
      used=min(left,length);area+=used*height;left-=used
      if not left:break
     vs.append(area)
   else:vs=artifact['values']
   assert vs==result['values'];checks.append(dict(id=row['id'],method=method,values=vs,service=result['certificate_scope']))
  if not QUICK:
   assert all(certified.get(k)==v for k,v in shared.items())
   assert len([r for r in checks if r['method']=='PACK'])==summary['by_method']['PACK']['units']
   for row in raw:
    if row['status']=='SUCCESS' and row['method']=='ROOT':assert read(attempt/'runs'/row['id']/'ARTIFACT.json')['value_slopes']==full_roots[row['case_id']]
  if study.endswith('_02'):
   shapes=read(attempt/'ANALYTICAL_CHECKS.json');assert not shapes['value_disagreements'] and len(shapes['whole_profile_checks'])==36 and all(r['equal'] for r in shapes['whole_profile_checks'])
   assert summary['original_process_exit']==1 and summary['measurements_rerun']==0
  report=dict(study=study,retained=count,original_status_counts=dict(status_counts),failure_reasons=dict(reasons),services=dict(services),artifacts_rechecked=dict(collections.Counter(r['method'] for r in checks)),shared_saved_values=len(shared),independently_certified_requested_values=len(certified),closed_form_checked=study.endswith('_02'),original_aggregation_failure_retained=study.endswith('_02'))
  reports.append(report);save(study+'_CHECKS.json',checks);all_checks.extend(checks)
 return dict(campaigns=reports,retained_units=600,artifacts_rechecked=len(all_checks),new_timing_samples=0,scope='Preserved outcome partitions, policy/point certificates, stored values and analytic stress fixture; ROOT/DP keep their original weaker services.')

def main():
 if not __debug__:raise SystemExit('Assertions must be enabled.')
 stage=sys.argv[1];start=time.monotonic()
 result={'compact':compact,'compact-native':compact_native,'compact-native-java':lambda:compact_native(True),'compact-scale':compact_scale}[stage]()
 result.update(stage=stage,replay_seconds=time.monotonic()-start,quick=QUICK,new_timing_samples=0)
 save('SUMMARY.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()

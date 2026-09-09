"""Replay preserved price and resource studies, without new evaluation samples."""
from pathlib import Path
from functools import lru_cache
import collections,copy,hashlib,importlib.util,json,os,shutil,subprocess,sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
HERE=Path(__file__).resolve().parent
DATA=HERE/'evidence/RESUMED_20260909_0056'
OUT=Path(sys.argv[2]);QUICK='--quick' in sys.argv[3:]
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def save(name,x):
 with (OUT/name).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 sys.path.insert(0,str(p.parent));spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def indexed(rows):
 d={r['id']:r for r in rows};assert len(d)==len(rows);return d
def select(rows):return rows[:12] if QUICK else rows
def direct(jobs,bmax):
 size=1<<len(jobs);d2=[[0]*size for _ in range(bmax+1)];d3=[[0]*size for _ in range(bmax+1)]
 prices=[(w+min(v,g+r),p+g+r-min(v,g+r),g+r-min(v,g+r),w+p) for w,p,g,v,r in jobs]
 for b in range(1,bmax+1):
  for mask in range(1,size):
   x=[];y=[]
   for i,(c,p,d,s) in enumerate(prices):
    if not mask>>i&1:continue
    child=mask^(1<<i)
    x.append(min(p+d2[b][child],max(d2[b][child],c+d2[b-1][mask])))
    y.append(min(p+d3[b][child],max(d3[b][child],c+d3[b-1][mask]),d+max(d3[b][child],s+d3[b-1][child])))
   d2[b][mask]=min(x);d3[b][mask]=min(y)
 return [r[-1] for r in d2],[r[-1] for r in d3]
def price_bounds():
 core=DATA/'charged_compact_03';compiler=load('compact',core/'compact.py');checker=load('verify',core/'verify.py');reports=[]
 with (OUT/'VALUES.jsonl').open('x') as out:
  for name,count in [('charged_price_bound_01',13302),('charged_price_bound_02',1866)]:
   d=DATA/name;data=read(d/'INPUTS.json');old=indexed(lines(d/'attempt01/RAW.jsonl'));first=name.endswith('_01')
   units=[(r,data['budgets'],False) for r in data['cases']]+[(r,r['budgets'],True) for r in data['family']] if first else [(r,list(range(r['saturation_bound']+1)),False) for r in data['cases']]
   assert len(units)==len(old)==count and {r['id'] for r,b,f in units}==set(old)
   roots=extra=0;routes=collections.Counter()
   for r,bs,family in select(units):
    case=r['input'];jobs=case['jobs'];assert not case['edges'];prev=old[r['id']];assert prev['status']=='SUCCESS'
    if not first:
     saturation=sum((p+g+k-min(v,g+k)+w+min(v,g+k)-1)//(w+min(v,g+k)) for w,p,g,v,k in jobs)
     assert saturation==r['saturation_bound']==prev['saturation_bound']
    else:assert prev['budgets']==bs
    a3=compiler.compile_case(case);checker.check(a3,case)
    cp=dict(cp=[[w+min(v,g+k),p+g+k-min(v,g+k)] for w,p,g,v,k in jobs],edges=[])
    a2=compiler.packing.pack(cp,compiler.packing.order_if_compatible(cp));checker.root_cap.check(a2)
    if a3['route']=='compatible_reduced':at3=checker.root_cap.Curve(a3['backend']['value_slopes']).value
    else:
     curve=a3['backend']['curves'][a3['backend']['full']];at3=lambda b:checker.general.value(curve,b)
    if family:
     n,m=r['n'],r['M'];p=r['lam'][0];assert len(jobs)==n and all(j==[1,p,0,m,m] for j in jobs)
     two=[min(n*p,b*(m+1)) for b in bs];three=[min(n*p,b*(p+1)) for b in bs]
    else:
     x,y=direct(jobs,max(bs));two=[x[b] for b in bs];three=[y[b] for b in bs]
    packed2=[compiler.packing.value(a2,b) for b in bs];packed3=[at3(b) for b in bs]
    assert two==packed2==prev['two']==prev['packed_two'] and three==packed3==prev['three']==prev['packed_three']
    A=sum(w+min(v,g+k) for w,p,g,v,k in jobs);assert A==prev['baseline']
    assert all(0<=y<=x and (A+2*x-y)**2<=2*(A+y)**2 for x,y in zip(two,three))
    if family or not first:
     assert json.loads(json.dumps(a2))==read(d/'attempt01'/(r['id']+'-two.json')) and json.loads(json.dumps(a3))==read(d/'attempt01'/(r['id']+'-three.json'))
    tail=[]
    if not first:
     premium=sum(p+g+k-min(v,g+k) for w,p,g,v,k in jobs);assert two[-1]==three[-1]==prev['premium']==premium
     tail=[dict(budget=b,two=compiler.packing.value(a2,b),three=at3(b)) for b in data['extra_budgets']]
     assert tail==prev['extra'] and all(t['two']==t['three']==premium for t in tail);extra+=len(tail)
    roots+=len(bs);routes[a3['route']]+=1
    out.write(json.dumps(dict(study=name,id=r['id'],baseline=A,budgets=bs,two=two,three=three,tail=tail,family_closed_form=family),separators=(',',':'))+'\n')
   reports.append(dict(study=name,retained_units=count,replayed=len(select(units)),roots=roots,extra_queries=extra,routes=dict(routes)))
 return dict(studies=reports,proof_by_finite_tests=False,new_evaluation_samples=0)
def resource_frontier():
 d=DATA/'charged_resource_frontier_01';data=read(d/'INPUTS.json');old=indexed(lines(d/'attempt01/RAW.jsonl'))
 assert len(data['cases'])==len(old)==5421 and set(old)=={r['id'] for r in data['cases']};roots=0
 with (OUT/'VALUES.jsonl').open('x') as out:
  for c in select(data['cases']):
   works=c['works'];n=len(works);full=(1<<n)-1;rows=[]
   @lru_cache(None)
   def solve(mask,b,r,three):
    if mask==0 or b==0:return 0
    choices=[]
    for i,w in enumerate(works):
     if not mask>>i&1 or any(v==i and mask>>u&1 for u,v in c['edges']):continue
     child=mask^(1<<i);success=solve(child,b,r,three);choices.append(w+success)
     if r>0:choices.append(max(success,solve(mask,b-1,r-1,three)))
     if three:choices.append(max(success,w+solve(child,b-1,r,three)))
    return min(choices)
   for b in data['budgets']:
    for r in data['slacks']:
     a=sum(c['works']) if b>r else 0;z=sum(sorted(c['works'],reverse=True)[:min(max(b-r,0),len(c['works']))])
     x=solve(full,b,r,False);y=solve(full,b,r,True);assert x==a and y==z;rows.append([b,r,x,y,a,z])
   assert old[c['id']]['status']=='SUCCESS' and rows==old[c['id']]['roots'];roots+=len(rows)
   out.write(json.dumps(dict(id=c['id'],roots=rows),separators=(',',':'))+'\n')
 return dict(retained_inputs=5421,replayed=len(select(data['cases'])),roots=roots,scope='finite original-mode minimax; not an all-program proof',new_evaluation_samples=0)
def resource_native(frontier=False,java=False):
 name='charged_resource_frontier_native_01' if frontier else 'charged_resource_vector_native_01';d=DATA/name;attempt=d/'attempt01'
 causal=load('causal',d/'causal.py');model=causal.model;sequence=causal.sequence_checker
 resource=load('resource_check',d/'resource_check.py');tablecheck=load('table_check',d/'table_check.py');fixed=load('fixed_policy',d/'fixed_policy.py')
 strict=load('resource_strict',DATA/'charged_resource_vector_recheck_02/strict.py')
 cases=indexed(read(attempt/'CASES.json'));runs=read(attempt/'RUNS.json');runmap=indexed(runs);retained=indexed(lines(attempt/'RAW.jsonl'));raw=retained
 counts=(128,9314,1024) if frontier else (96,2442,576)
 assert (len(cases),len(runs))==counts[:2] and set(raw)==set(runmap)
 tables=[];path_groups={}
 for case in cases.values():
  t=read(attempt/('table_'+case['id']+'.json'));assert t['case']==case;values={int(k):v for k,v in t['values'].items()}
  checked=tablecheck.check(case,values) if frontier else strict.check(case,values,tablecheck)
  tables.append(dict(id=case['id'],result=checked));f,choose,paths=fixed.ordinary(case);full=(1<<len(case['jobs']))-1
  for b in ([0,1,2,3] if frontier else [0,1,2]):
   possibilities=list(paths(full,b));assert len({p for p,t,c in possibilities})==len(possibilities)
   for layout in ['distinct','colliding']:path_groups[case['id'],b,layout]=possibilities
 save('TABLE_CHECKS.json',tables)
 if not frontier:
  correction=DATA/'charged_resource_vector_recheck_02';toy=read(correction/'LEGACY_TAIL_COUNTEREXAMPLE.json');tab={int(k):v for k,v in toy['table'].items()}
  tablecheck.check(toy['case'],tab);rejected=False
  try:strict.check(toy['case'],tab,tablecheck)
  except AssertionError:rejected=True
  assert rejected
  controls=[]
  for x in read(correction/'AGGREGATION_CONTROLS.json'):
   actual=strict.native_control_met(x['input'],False,'SUCCESS');assert actual==x['expected'];controls.append(dict(id=x['id'],met=True))
  save('CORRECTION_CONTROLS.json',dict(legacy_counterexample_rejected=True,aggregation_controls=controls))
 group_runs=collections.defaultdict(list)
 for r in runs:
  if r['kind']=='replay' and not r['control']:group_runs[r['case'],r['budget'],r['layout']].append(r)
 assert set(group_runs)==set(path_groups)
 for key,rs in group_runs.items():
  expected=path_groups[key];actual=[(r['outcomes'],r['expected_trace'],r['expected_cost']//8) for r in rs]
  assert actual==expected and all(r['expected_cost']%8==0 for r in rs)
  assert all(r['expected_resources']==resource.from_trace(cases[r['case']],r['expected_trace']) for r in rs)
 if java:
  java_bin=os.environ.get('JAVA_BIN','java');javac=os.environ.get('JAVAC_BIN','javac');removed=['JDK_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVAC_OPTIONS'];env={k:v for k,v in os.environ.items() if k not in removed}
  version=subprocess.check_output([java_bin,'-version'],stderr=subprocess.STDOUT,text=True,env=env);assert 'version "17.' in version
  classname='FrontierChargedCallbacks' if frontier else 'VectorChargedCallbacks';source=d/(classname+'.java')
  target=OUT/'java-input';target.mkdir();classes=OUT/'classes';classes.mkdir()
  for p in attempt.glob('*.tsv'):shutil.copy2(p,target/p.name)
  shutil.copy2(source,target/source.name)
  c=subprocess.run([javac,'--release','17','-d',str(classes),str(target/source.name)],capture_output=True,timeout=30,env=env)
  (OUT/'javac.stdout').write_bytes(c.stdout);(OUT/'javac.stderr').write_bytes(c.stderr);assert c.returncode==0
  with (OUT/'NEW_NATIVE_RAW.jsonl').open('xb') as out,(OUT/'java.stderr').open('xb') as err:
   c=subprocess.run([java_bin,'-ea','-cp',str(classes),classname,str(target)],stdout=out,stderr=err,timeout=180,env=env)
  assert c.returncode==0;raw=indexed(lines(OUT/'NEW_NATIVE_RAW.jsonl'));assert set(raw)==set(runmap)
  save('JAVA_VERSION.json',dict(version=version,source_sha256=sha(source),removed_launcher_environment_names=removed))
 chosen=select([r for r in runs if not r['control']])+[r for r in runs if r['control']];groups={}
 with (OUT/'VERIFICATION.jsonl').open('x') as out,(OUT/'CERTIFICATES.jsonl').open('x') as cf:
  for r in chosen:
   row=raw[r['id']];v=causal.verify(cases[r['case']],r,row)
   assert strict.native_control_met(v,r['expected_accept'],row['status']),(r['id'],v)
   if v['accepted']:
    vector=resource.check(cases[r['case']],r,row);v['resources']=vector
    if not r['control'] and r['kind']=='replay':
     key=r['case'],r['budget'],r['layout'];g=groups.setdefault(key,dict(count=0,W=0,L=0,Q=0,cost=0));g['count']+=1
     for k in ['W','L','Q','cost']:g[k]=max(g[k],vector[k])
   if 'certificate' in v:
    cert=v.pop('certificate');cf.write(json.dumps(dict(id=r['id'],certificate=cert),separators=(',',':'))+'\n');v['certificate_sha256']=model.digest(cert)
   out.write(json.dumps(dict(id=r['id'],result=v),separators=(',',':'))+'\n')
 planned=read(attempt/'MODEL_GROUPS.json');assert len(planned)==counts[2]
 if not QUICK:
  assert len(groups)==counts[2]
  for p in planned:
   g=groups[p['case'],p['budget'],p['layout']];assert g['count']==p['paths'] and g['cost']==p['expected_cost_ceiling'] and all(g[k]==p['expected_maxima'][k] for k in ['W','L','Q'])
   if frontier:assert g['L']==p['frontier_lbound'] and g['Q']<=len(cases[p['case']]['jobs'])+p['slack']
 target=read(attempt/'CONTROL_TARGETS.json')['cached_failure'];r=runmap[target];case=cases[r['case']];controls=[]
 for item in read(attempt/'RECORD_CONTROLS.json'):
  v=causal.verify(case,r,item['row']);prev=item['result']
  assert all(v.get(k)==prev.get(k) for k in ['accepted','status','layer','reason']) and v['accepted']==item['expected_accept']
  if v['accepted']:resource.check(case,r,item['row'])
  v.pop('certificate',None);controls.append(dict(id=item['id'],result=v))
 program=model.build(case,r,retained[target]);seq=[]
 for item in read(attempt/'SEQUENCE_CONTROLS.json'):
  try:sequence.check(program,item['certificate']);accepted=True
  except AssertionError:accepted=False
  assert accepted==item['expected_accept'];seq.append(dict(id=item['id'],accepted=accepted))
 parser=[]
 for item in read(attempt/'PARSER_CONTROLS.json'):
  if java:
   c=subprocess.run([java_bin,'-ea','-cp',str(classes),classname,str(attempt/'parser_inputs'/item['id'])],capture_output=True,text=True,timeout=3,env=env);stdout,stderr,code=c.stdout,c.stderr,c.returncode
   (OUT/('parser_'+item['id']+'.stdout')).write_text(stdout);(OUT/('parser_'+item['id']+'.stderr')).write_text(stderr)
  else:stdout=(attempt/('parser_'+item['id']+'.stdout')).read_text();stderr=(attempt/('parser_'+item['id']+'.stderr')).read_text();code=item['returncode']
  if item['expected_accept']:assert code==0 and not stdout and not stderr
  else:assert code==1 and not stdout and stderr.splitlines()[0]=='Exception in thread "main" java.lang.IllegalArgumentException: '+item['expected_error']
  parser.append(dict(id=item['id'],returncode=code,native_reexecuted=java))
 assert len(controls)==8 and len(seq)==5 and len(parser)==4
 save('RECORD_CONTROLS.json',controls);save('SEQUENCE_CONTROLS.json',seq);save('PARSER_CONTROLS.json',parser)
 save('REPLAY_GROUPS.json',[dict(case=k[0],budget=k[1],layout=k[2],**v) for k,v in groups.items()])
 return dict(retained_runs=counts[1],replayed_records=len(chosen),tables=len(tables),replay_groups=len(groups),source_paths_checked=sum(len(v) for v in path_groups.values()),record_controls=8,sequence_controls=5,parser_controls=4,new_native_replay_records=len(raw) if java else 0,new_evaluation_samples=0,scope='finite source-event counters and causal feasibility; no timing or fee calibration')
if __name__=='__main__':
 if not __debug__:raise SystemExit('Assertions must be enabled.')
 stage=sys.argv[1]
 if stage=='price-bounds':summary=price_bounds()
 elif stage=='resource-frontier':summary=resource_frontier()
 elif stage in ['resource-vector','resource-vector-java']:summary=resource_native(java=stage.endswith('-java'))
 elif stage in ['resource-frontier-native','resource-frontier-java']:summary=resource_native(frontier=True,java=stage.endswith('-java'))
 else:raise SystemExit('unknown stage')
 save('SUMMARY.json',dict(status='SUCCESS',stage=stage,quick=QUICK,**summary));print(json.dumps(summary),flush=True)

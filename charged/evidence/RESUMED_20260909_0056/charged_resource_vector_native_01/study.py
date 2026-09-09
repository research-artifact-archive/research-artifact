from pathlib import Path
from collections import Counter
import copy,datetime,hashlib,json,os,signal,subprocess,sys,time,traceback
import fixed_policy,table_check,resource_check,causal,model,sequence_checker
P=Path(__file__).resolve().parent;OUT=P/'attempt01'
JAVA='/opt/homebrew/opt/openjdk@17/bin/java';JAVAC='/opt/homebrew/opt/openjdk@17/bin/javac'
PARAMS=dict(budgets=[0,1,2],layouts=['distinct','colliding'],kappa=[0,2],policies=fixed_policy.POLICIES,concurrent_budget=2,seeds=[11,23],
 shapes=[dict(id='common-two-chain',w=[1,2],edges=[[0,1]]),dict(id='equal-two-independent',w=[1,1],edges=[]),dict(id='three-independent',w=[1,2,3],edges=[]),dict(id='three-chain',w=[1,2,3],edges=[[0,1],[1,2]]),dict(id='five-independent',w=[1,2,3,4,5],edges=[]),dict(id='five-chain',w=[1,2,3,4,5],edges=[[0,1],[1,2],[2,3],[3,4]]),dict(id='five-branch',w=[1,2,3,4,5],edges=[[0,1],[0,2],[1,3],[2,4]]),dict(id='five-decreasing-chain',w=[5,4,3,2,1],edges=[[0,1],[1,2],[2,3],[3,4]])],
 record_controls=['unchanged','wrong_W','wrong_L_counter','wrong_Q_counter','wrong_inside','wrong_failure_epoch','wrong_selected_mode','coordinated_counter_cost'],sequence_controls=['unchanged','missing_step','duplicate_step','wrong_raw_binding','wrong_input_binding'],parser_controls=['unchanged','unknown_policy','wrong_p','missing_curve'])

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def write(p,s):
 with p.open('x') as f:f.write(s)
def sourcefiles():return sorted(x for x in P.iterdir() if x.suffix in ['.py','.java','.md','.json','.patch'])
def prepare():
 OUT.mkdir();save(OUT/'PARAMETERS.json',dict(utc=utc(),parameters=PARAMS,sources={str(x):sha(x) for x in sourcefiles()},native_executions=0))
 cases=[];case_lines=[];runs=[];run_lines=[];tables=[];groups=[]
 def add(case,layout,kind,b,path,seed=0,mutant='none',control=False,trace=None,cost=None):
  rid='vector-run-%06d'%len(runs);row=dict(id=rid,case=case['id'],layout=layout,kind=kind,budget=b,outcomes=path,seed=seed,mutant=mutant,control=control,expected_accept=mutant=='none')
  if trace is not None:row.update(expected_trace=trace,expected_cost=8*cost,expected_resources=resource_check.from_trace(case,trace))
  runs.append(row);run_lines.append('\t'.join(map(str,[rid,case['id'],layout,kind,b,path or '-',seed,mutant])))
 for shape in PARAMS['shapes']:
  for k in PARAMS['kappa']:
   for policy in PARAMS['policies']:
    case=dict(id=shape['id']+'-k%d-'%k+policy,base=shape['id'],kappa=k,policy=policy,jobs=[[w,w,0,k,k] for w in shape['w']],edges=shape['edges'])
    f,choose,paths=fixed_policy.ordinary(case);n=len(case['jobs']);full=(1<<n)-1;table={mask:[f(mask,b) for b in range(n+1)] for mask in range(1<<n)};checked=table_check.check(case,table)
    file='table_'+case['id']+'.tsv';encoded=[]
    for mask,values in table.items():encoded.append(str(mask)+'\t'+';'.join('%d:%d:%d'%(b,y,values[b+1]-y if b<n else 0) for b,y in enumerate(values)))
    write(OUT/file,'\n'.join(encoded)+'\n');save(OUT/('table_'+case['id']+'.json'),dict(case=case,values=table,check=checked))
    cols=[','.join(str(row[i]) for row in case['jobs']) for i in range(5)];pred=[sum(1<<a for a,b in case['edges'] if b==i) for i in range(n)]
    line='\t'.join([case['id']]+cols+[','.join(map(str,pred)),file,policy]);case_lines.append(line);cases.append(case);tables.append(dict(id=case['id'],check=checked,transport=file,sha256=sha(OUT/file)))
    baseline=sum(w+min(v,g+r) for w,p,g,v,r in case['jobs'])
    for b in PARAMS['budgets']:
     possibilities=list(paths(full,b));assert max(z[2] for z in possibilities)==baseline+f(full,b)
     vectors=[resource_check.from_trace(case,z[1]) for z in possibilities];maxima={key:max(v[key] for v in vectors) for key in ['W','L','Q']}
     if policy in ['qn_three','cached_all','protected_all']:assert maxima['Q']==n
     for layout in PARAMS['layouts']:
      groups.append(dict(case=case['id'],base=case['base'],kappa=k,policy=policy,budget=b,layout=layout,paths=len(possibilities),expected_maxima=maxima,expected_cost_ceiling=8*(baseline+f(full,b))))
      for path,trace,cost in possibilities:add(case,layout,'replay',b,path,trace=trace,cost=cost)
    for layout in PARAMS['layouts']:
     for seed in PARAMS['seeds']:add(case,layout,'concurrent',2,'',seed=seed)
 target=next(c for c in cases if c['id']=='common-two-chain-k2-scalar_three');f,choose,paths=fixed_policy.ordinary(target);path=next(p for p,t,c in paths(3,1) if 'F' not in p)
 for mutant in ['none','live_parent']:add(target,'colliding','postwrite',1,path,mutant=mutant,control=True)
 cf=next(r for r in runs if r['case']==target['id'] and r['layout']=='distinct' and r['kind']=='replay' and r['budget']==1 and r['outcomes']=='FS')
 save(OUT/'CONTROL_TARGETS.json',dict(cached_failure=cf['id'],parser_case=target['id']))
 write(OUT/'CASES.tsv','\n'.join(case_lines)+'\n');write(OUT/'RUNS.tsv','\n'.join(run_lines)+'\n');save(OUT/'CASES.json',cases);save(OUT/'RUNS.json',runs);save(OUT/'MODEL_GROUPS.json',groups);save(OUT/'TABLE_CHECKS.json',tables)
 parser=[];line=next(x for x in case_lines if x.startswith(target['id']+'\t'));file=line.split('\t')[7];blob=(OUT/file).read_text()
 for name in PARAMS['parser_controls']:
  fields=line.split('\t');newblob=blob
  if name=='unknown_policy':fields[8]='unsupported'
  elif name=='wrong_p':values=fields[2].split(',');values[0]=str(int(values[0])+1);fields[2]=','.join(values)
  elif name=='missing_curve':newblob='\n'.join(blob.splitlines()[:-1])+'\n'
  dest=OUT/'parser_inputs'/name;dest.mkdir(parents=True);write(dest/'CASES.tsv','\t'.join(fields)+'\n');write(dest/file,newblob);write(dest/'RUNS.tsv','')
  parser.append(dict(id=name,directory=str(dest),expected_accept=name=='unchanged',expected_error={'unknown_policy':'policy','wrong_p':'vector prices','missing_curve':'missing curve'}.get(name)))
 save(OUT/'PARSER_UNITS.json',parser)
 envvars=['JDK_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVAC_OPTIONS'];sources={str(x):sha(x) for x in sourcefiles()};sources.update({str(Path(x).resolve()):sha(Path(x).resolve()) for x in [JAVA,JAVAC,sys.executable]})
 manifest=dict(utc=utc(),shapes=8,price_configurations=16,selectors=6,configured_cases=len(cases),runs=len(runs),ordinary_runs=sum(not r['control'] for r in runs),replay_runs=sum(r['kind']=='replay' for r in runs),concurrent_runs=sum(r['kind']=='concurrent' for r in runs),native_controls=2,replay_cells=len(groups),sources=sources,inputs={str(x):sha(x) for x in OUT.rglob('*') if x.is_file()},parameters=PARAMS,compile_argv=[JAVAC,'-d',str(OUT/'classes'),str(P/'VectorChargedCallbacks.java')],run_argv=[JAVA,'-cp',str(OUT/'classes'),'VectorChargedCallbacks',str(OUT)],java_version=subprocess.check_output([JAVA,'-version'],stderr=subprocess.STDOUT,text=True),filtered_java_environment=envvars,native_cap=180,check_cap=300,per_search_seconds=2)
 save(OUT/'MANIFEST.json',manifest);print(json.dumps({k:manifest[k] for k in ['shapes','price_configurations','selectors','configured_cases','runs','ordinary_runs','replay_runs','concurrent_runs','native_controls','replay_cells']}))

def bind():
 m=json.loads((OUT/'MANIFEST.json').read_text())
 assert all(sha(Path(p))==h for section in ['sources','inputs'] for p,h in m[section].items())
 return m
def execute():
 m=bind();env=dict(os.environ)
 for key in m['filtered_java_environment']:env.pop(key,None)
 save(OUT/'RUN_STARTED.json',dict(utc=utc(),manifest_sha256=sha(OUT/'MANIFEST.json')));start=time.monotonic();c=subprocess.run(m['compile_argv'],capture_output=True,text=True,timeout=30,env=env);write(OUT/'COMPILE.stdout',c.stdout);write(OUT/'COMPILE.stderr',c.stderr);save(OUT/'COMPILE_RECEIPT.json',dict(returncode=c.returncode,seconds=time.monotonic()-start,classes={str(x):sha(x) for x in (OUT/'classes').glob('*.class')}))
 if c.returncode:save(OUT/'EXECUTION_RECEIPT.json',dict(status='COMPILE_FAILURE',native_started=False));return
 start=time.monotonic()
 with (OUT/'RAW.jsonl').open('x') as stdout,(OUT/'RUN.stderr').open('x') as stderr:
  proc=subprocess.Popen(m['run_argv'],stdout=stdout,stderr=stderr,env=env,start_new_session=True)
  try:code=proc.wait(timeout=180);status='COMPLETED' if code==0 else 'FAILURE'
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait();status='TIMEOUT'
 save(OUT/'EXECUTION_RECEIPT.json',dict(utc=utc(),status=status,returncode=code,seconds=time.monotonic()-start,raw_sha256=sha(OUT/'RAW.jsonl')));print(json.dumps(dict(status=status,returncode=code)))

def controls(cases,runs,raw,certs):
 target=json.loads((OUT/'CONTROL_TARGETS.json').read_text())['cached_failure'];run=next(r for r in runs if r['id']==target);case=cases[run['case']];records=[]
 for name in PARAMS['record_controls']:
  row=copy.deepcopy(raw[target])
  if name=='wrong_W':row['work']-=1
  elif name=='wrong_L_counter':row['protected_calls'][0]-=1
  elif name=='wrong_Q_counter':row['callbacks'][0]-=1
  elif name=='wrong_inside':next(e for e in row['events'] if e['kind']=='K' and e['inside'])['inside']=False
  elif name=='wrong_failure_epoch':row['failures'][0][1]+=1
  elif name=='wrong_selected_mode':row['trace'][0]='0:P'
  elif name=='coordinated_counter_cost':row['callbacks'][0]-=1;row['cost']-=16
  result=causal.verify(case,run,row);expected=name=='unchanged';met=result['accepted']==expected and result['status']==('FEASIBLE' if expected else 'REJECTED')
  if result['accepted']:resource_check.check(case,run,row)
  result.pop('certificate',None);records.append(dict(id=name,expected_accept=expected,met=met,row=row,result=result))
 save(OUT/'RECORD_CONTROLS.json',records);seq=[]
 for name in PARAMS['sequence_controls']:
  cert=copy.deepcopy(certs[target]);program=model.build(case,run,raw[target])
  if name=='missing_step':cert['order'].pop()
  elif name=='duplicate_step':cert['order'].insert(0,cert['order'][0])
  elif name=='wrong_raw_binding':cert['raw_sha256']='0'*64
  elif name=='wrong_input_binding':cert['input_sha256']='0'*64
  try:sequence_checker.check(program,cert);accepted=True;error=None
  except AssertionError:accepted=False;error=traceback.format_exc()
  seq.append(dict(id=name,expected_accept=name=='unchanged',accepted=accepted,met=accepted==(name=='unchanged'),error=error,certificate=cert))
 save(OUT/'SEQUENCE_CONTROLS.json',seq);parsers=[];env=dict(os.environ)
 for name in ['JDK_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVAC_OPTIONS']:env.pop(name,None)
 for unit in json.loads((OUT/'PARSER_UNITS.json').read_text()):
  args=[JAVA,'-cp',str(OUT/'classes'),'VectorChargedCallbacks',unit['directory']]
  try:c=subprocess.run(args,env=env,capture_output=True,text=True,timeout=3);accepted=c.returncode==0;error=None
  except subprocess.TimeoutExpired:parsers.append(dict(id=unit['id'],met=False,status='TIMEOUT'));continue
  write(OUT/('parser_'+unit['id']+'.stdout'),c.stdout);write(OUT/('parser_'+unit['id']+'.stderr'),c.stderr)
  expected='Exception in thread "main" java.lang.IllegalArgumentException: '+str(unit['expected_error'])
  met=(c.returncode==0 and not c.stdout and not c.stderr) if unit['expected_accept'] else (c.returncode==1 and not c.stdout and bool(c.stderr.splitlines()) and c.stderr.splitlines()[0]==expected)
  parsers.append(dict(id=unit['id'],met=met,returncode=c.returncode,accepted=accepted,expected_accept=unit['expected_accept'],expected_error=unit['expected_error']))
 save(OUT/'PARSER_CONTROLS.json',parsers)
 return records,seq,parsers

def check():
 m=bind();runs=json.loads((OUT/'RUNS.json').read_text());cases={c['id']:c for c in json.loads((OUT/'CASES.json').read_text())};allowed={r['id'] for r in runs};raw={};input_errors=[]
 for no,line in enumerate((OUT/'RAW.jsonl').read_text().splitlines(),1):
  try:
   row=json.loads(line);rid=row['id'];assert rid in allowed and rid not in raw;raw[rid]=row
  except Exception:input_errors.append(dict(line=no,error=traceback.format_exc()))
 save(OUT/'RAW_INPUT_CHECK.json',dict(errors=input_errors,recorded=len(raw),planned=len(runs)));start=time.monotonic();rows=[];certs={};vectors={};groups={}
 with (OUT/'VERIFICATION.jsonl').open('x') as out,(OUT/'CERTIFICATES.jsonl').open('x') as cf:
  for index,run in enumerate(runs):
   row=raw.get(run['id'])
   if row is None or time.monotonic()-start>=300:result=dict(status='NOT_RUN',accepted=None)
   elif row['status']!='SUCCESS':result=dict(status=row['status'],accepted=None)
   else:result=causal.verify(cases[run['case']],run,row)
   if result.get('accepted'):
    try:vector=resource_check.check(cases[run['case']],run,row);vectors[run['id']]=vector;result['resources']=vector
    except Exception:result=dict(status='RESOURCE_CHECK_FAILURE',accepted=False,error=traceback.format_exc())
   if 'certificate' in result:
    cert=result.pop('certificate');certs[run['id']]=cert;cf.write(json.dumps(dict(id=run['id'],certificate=cert),separators=(',',':'))+'\n');cf.flush()
   met=result.get('accepted')==run['expected_accept'] and row is not None and row['status']=='SUCCESS';terminal='SUCCESS' if met else result['status'] if result['status'] in ['TIMEOUT','INVALID','NOT_RUN'] else 'FAILURE';result.update(id=run['id'],expected_accept=run['expected_accept'],control=run['control'],met=met,terminal=terminal)
   if not met and not (OUT/'FIRST_ADVERSE.json').exists():save(OUT/'FIRST_ADVERSE.json',dict(case=cases[run['case']],run=run,row=row,result=result))
   if met and not run['control'] and run['kind']=='replay':
    key=(run['case'],run['budget'],run['layout']);g=groups.setdefault(key,dict(count=0,W=0,L=0,Q=0,cost=0));g['count']+=1
    for q in ['W','L','Q','cost']:g[q]=max(g[q],vectors[run['id']][q])
   rows.append(result);out.write(json.dumps(result,separators=(',',':'))+'\n');out.flush()
   if (index+1)%500==0:print(json.dumps(dict(checked=index+1,total=len(runs),adverse=sum(not r['met'] for r in rows))),flush=True)
 save(OUT/'RESOURCE_RECORDS.json',vectors);group_rows=[]
 for planned in json.loads((OUT/'MODEL_GROUPS.json').read_text()):
  key=(planned['case'],planned['budget'],planned['layout']);observed=groups.get(key);met=observed is not None and observed['count']==planned['paths'] and observed['cost']==planned['expected_cost_ceiling'] and all(observed[k]==planned['expected_maxima'][k] for k in ['W','L','Q'])
  group_rows.append(dict(**planned,observed=observed,met=met))
 save(OUT/'REPLAY_GROUPS.json',group_rows)
 try:rc,sc,pc=controls(cases,runs,raw,certs)
 except Exception:rc=sc=pc=[];save(OUT/'CONTROL_FAILURE.json',dict(error=traceback.format_exc()))
 counts=Counter(r['terminal'] for r in rows);summary=dict(utc=utc(),status='SUCCESS' if not input_errors and all(r['met'] for r in rows+group_rows+rc+sc+pc) and len(rc)==8 and len(sc)==5 and len(pc)==4 else 'FAILURE',native_runs=len(runs),ordinary_runs=m['ordinary_runs'],native_controls=2,recorded=len(raw),status_counts=dict(counts),replay_groups=len(group_rows),replay_groups_met=sum(r['met'] for r in group_rows),record_controls_met=sum(r['met'] for r in rc),sequence_controls_met=sum(r['met'] for r in sc),parser_controls_met=sum(r['met'] for r in pc),check_seconds=time.monotonic()-start,raw_sha256=sha(OUT/'RAW.jsonl'),interpretation='bounded native source-counter study; finite source-model feasibility; not latency or fee calibration')
 save(OUT/'SUMMARY.json',summary);print(json.dumps(summary,indent=2));raise SystemExit(0 if summary['status']=='SUCCESS' else 1)

if __name__=='__main__':
 action=sys.argv[1]
 if action=='prepare':prepare()
 elif action=='execute':execute()
 elif action=='check':check()
 else:raise SystemExit('prepare|execute|check')

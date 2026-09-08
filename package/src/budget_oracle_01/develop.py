from pathlib import Path
import collections,copy,datetime,hashlib,importlib.util,json,signal,sys,time,traceback
import oracle,value_certificate as checker
ROOT=Path(__file__).resolve().parent;S=ROOT.parent
spec=importlib.util.spec_from_file_location('independent_scalar_reference',S/'b2_contingent_comparator_01/checker.py');scalar=importlib.util.module_from_spec(spec);spec.loader.exec_module(scalar)
spec=importlib.util.spec_from_file_location('independent_allbudget_reference',S/'final_evaluation_dag_01/evaluate.py');validation=importlib.util.module_from_spec(spec);sys.path.insert(0,str(S/'final_evaluation_dag_01'));spec.loader.exec_module(validation)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,data):
 with (ROOT/name).open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def freeze():
 units=[];old={r['input_id']:r for r in map(json.loads,(S/'final_evaluation_dag_01/RAW.jsonl').read_text().splitlines())}
 for c in json.loads((S/'final_evaluation_dag_01/INPUTS.json').read_text()):
  row=old[c['id']];assert row['status']=='SUCCESS';normal=sum(x[0] for x in c['cp']);expected={str(x['b']):x['primitive']-normal for x in row['roots']}
  units.append(dict(id='semantic-'+c['id'],group='known_semantic',case=dict(cp=c['cp'],edges=c['edges']),budgets=[0,1,2,3,4],expected=expected))
 for c in json.loads((S/'b1_constraint_comparator_01/DEV_INPUTS.json').read_text()):
  if c['group']=='new_authored_relabel':units.append(dict(id='relabel-'+c['id'],group='known_case_new_budgets',case=c['case'],budgets=[0,1,2,4,8]))
 for scale in [1,2,7,101,1<<20,1<<40]:
  case=dict(cp=[[3,2*scale],[7,2*scale],[5,6*scale],[1,2*scale]],edges=[[0,1],[0,2],[1,3]])
  sat=sum((p+c-1)//c for c,p in case['cp'])
  units.append(dict(id=f'family-premium-scale-{scale}',group='authored_premium_only_scale',case=case,budgets=[0,1,2,8,sat//2,sat]))
 for ident,case in [('empty',dict(cp=[],edges=[])),('zero-premium',dict(cp=[[5,0],[1,0]],edges=[[0,1]])),('single-wide',dict(cp=[[3,1<<40]],edges=[]))]:
  units.append(dict(id=ident,group='boundary',case=case,budgets=[0,1,1<<40]))
 assert len(units)==4337;assert len({u['id'] for u in units})==len(units)
 if (ROOT/'INPUTS.json').exists():assert json.loads((ROOT/'INPUTS.json').read_text())==units
 else:save('INPUTS.json',units)
 files=[ROOT/x for x in ['PLAN_DRAFT.md','DEVELOPMENT_PLAN.md','oracle.py','value_certificate.py','develop.py','INPUTS.json']]
 for module in [oracle.hybrid,oracle.hybrid.curves,checker.packed_checker,scalar,validation,validation.hybrid,validation.packed,validation.bellman,validation.structure]:files.append(Path(module.__file__))
 unique=sorted(set(p.resolve() for p in files));save('MANIFEST.json',dict(utc=now(),units=len(units),roots=sum(len(u['budgets']) for u in units),groups=dict(collections.Counter(u['group'] for u in units)),files=[dict(path=str(p),sha256=sha(p)) for p in unique]))
 print('frozen',len(units),'units',sum(len(u['budgets']) for u in units),'roots')
def reference(case,budgets):
 if max(budgets,default=0)<=32:return {str(b):scalar.scalar(case,b)[0] for b in budgets}
 data=validation.hybrid.compile_case(case);data=json.loads(json.dumps(data))
 if data['route']=='ordered':report=validation.packed.check(data)
 else:
  validation.structure.check(data);report=validation.bellman.check(data)
 assert not report['violations'];loaded=validation.hybrid.load(data)
 return {str(b):validation.hybrid.value(loaded,b) for b in budgets}
def controls():
 case=dict(cp=[[3,2],[7,2],[5,6],[1,2]],edges=[[0,1],[0,2],[1,3]])
 valid=oracle.solve(case,2)['artifact'];assert checker.check(valid)['value']==8
 mutants=[]
 def add(ident,fn):
  x=copy.deepcopy(valid);fn(x);mutants.append(dict(id=ident,artifact=x))
 add('schema',lambda x:x.update(schema='wrong'))
 add('root-value',lambda x:x.update(root_value=x['root_value']+1))
 add('node-value',lambda x:x['nodes'][x['root']].update(value=x['root_value']+1))
 add('negative-budget',lambda x:x.update(budget=-1))
 add('wrong-root',lambda x:x.update(root='0:0'))
 add('extra-node',lambda x:x['nodes'].update({'0:999':dict(mask=0,budget=999,value=0,kind='zero')}))
 child=next(k for k in valid['nodes'] if k!=valid['root'])
 add('missing-node',lambda x:x['nodes'].pop(child))
 assert valid['nodes'][valid['root']]['kind']=='peak'
 add('peak-range',lambda x:x['nodes'][x['root']].update(peak=3))
 add('job-range',lambda x:x['nodes'][x['root']].update(job=4))
 add('false-zero',lambda x:x['nodes'][x['root']].update(kind='zero'))
 add('cycle-input',lambda x:x['input']['edges'].append([1,0]))
 add('extra-field',lambda x:x.update(unchecked=True))
 bounds=[k for k,v in valid['nodes'].items() if v['kind']=='bound'];packs=list(valid['packed']);inapplicable=[]
 if bounds:add('bad-bound',lambda x:x['nodes'][bounds[0]].update(threshold=-1))
 else:inapplicable.append('bad-bound')
 if packs:add('bad-packing',lambda x:x['packed'][packs[0]]['value_slopes'].append([999,1]))
 else:inapplicable.append('bad-packing')
 save('CONTROL_INPUTS.json',dict(valid=valid,mutants=mutants,structurally_inapplicable=inapplicable));raw=[]
 for u in mutants:
  try:checker.check(u['artifact'])
  except (AssertionError,KeyError,ValueError,TypeError):raw.append(dict(id=u['id'],status='REJECTED'))
  else:raw.append(dict(id=u['id'],status='ACCEPTED_INVALID'))
 save('CONTROL_RAW.json',raw);assert all(r['status']=='REJECTED' for r in raw)
 return dict(valid=1,rejected=len(raw),structurally_inapplicable=inapplicable)
def alarm(sig,frame):raise TimeoutError('fixed development cap')
def run():
 m=json.loads((ROOT/'MANIFEST.json').read_text())
 for f in m['files']:assert sha(f['path'])==f['sha256'],f['path']
 save('RUN_STARTED.json',dict(utc=now(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
 units=json.loads((ROOT/'INPUTS.json').read_text());start=time.monotonic();counts=collections.Counter();roots=0;stats=collections.Counter();signal.signal(signal.SIGALRM,alarm)
 with (ROOT/'RAW.jsonl').open('x') as raw:
  for u in units:
   before=time.monotonic();left=180-(before-start)
   if left<=0:r=dict(id=u['id'],status='NOT_RUN')
   else:
    signal.setitimer(signal.ITIMER_REAL,min(5,left))
    try:
     expected=reference(u['case'],u['budgets'])
     if 'expected' in u:assert expected==u['expected']
     results=[]
     for b in u['budgets']:
      got=oracle.solve(u['case'],b);encoded=json.dumps(got['artifact'],sort_keys=True,separators=(',',':')).encode();report=checker.check(json.loads(encoded))
      assert got['value']==report['value']==expected[str(b)],(b,got['value'],expected[str(b)])
      results.append(dict(budget=b,value=got['value'],certificate_report=report,artifact_sha256=hashlib.sha256(encoded).hexdigest(),artifact_bytes=len(encoded),stats=got['stats']))
     r=dict(id=u['id'],status='SUCCESS',roots=results)
    except AssertionError:r=dict(id=u['id'],status='FAILURE',error=traceback.format_exc())
    except TimeoutError:r=dict(id=u['id'],status='TIMEOUT',error=traceback.format_exc())
    except Exception:r=dict(id=u['id'],status='INVALID',error=traceback.format_exc())
    finally:signal.setitimer(signal.ITIMER_REAL,0)
   r['seconds']=time.monotonic()-before;counts[r['status']]+=1;raw.write(json.dumps(r,separators=(',',':'))+'\n');raw.flush()
   if r['status']=='SUCCESS':
    roots+=len(r['roots'])
    for x in r['roots']:
     for k,v in x['stats'].items():stats[k]=max(stats[k],v)
 control=controls();result=dict(utc=now(),units=len(units),roots=roots,counts=dict(counts),max_stats=dict(stats),control=control,seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'RAW.jsonl'));save('SUMMARY.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()

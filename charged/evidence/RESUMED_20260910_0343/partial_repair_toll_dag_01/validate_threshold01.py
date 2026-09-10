from pathlib import Path
from functools import lru_cache
import collections,copy,datetime,hashlib,itertools,json,resource,time
from threshold_compile import compile_thresholds,run_certificate_policy
from threshold_check import check_certificate
P=Path(__file__).resolve().parent;O=P/'threshold_validation01';O.mkdir();start=time.perf_counter()
def dump(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old_inputs=json.loads((P/'run02/INPUTS.json').read_text());old_raw=[json.loads(x) for x in (P/'run02/RAW.jsonl').read_text().splitlines()]
assert len(old_raw)==len(old_inputs['units'])==37248
def prof(weights,fs):
 dist={0:0}
 for k in range(1,len(weights)+1):
  for word in itertools.product(fs,repeat=k):
   d=0
   for f in word:d|=f
   dist.setdefault(d,k)
 obs=[dict(mask=d,c=k,w=sum(w for i,w in enumerate(weights) if d>>i&1)) for d,k in sorted(dist.items())]
 G=[max(o['w'] for o in obs if o['c']<=b) for b in range(len(weights)+1)]
 return dict(weights=list(weights),footprints=list(fs),observations=obs,G=G,W=G[-1],sigma=next(i for i,x in enumerate(G) if x==G[-1]))
new=[]
for weights in [(2,2,2),(2,4,6)]:
 for fs in [[1,2,7],[1,2,4,7]]:
  for edges in [[(0,1)],[(1,0)]]:
   for r in range(3):
    for k in [1,2,4,6,12]:new.append(dict(id=len(new),jobs=[prof(weights,fs),prof([2],[1])],edges=edges,retries=r,toll=k))
assert len(new)==120
dump(O/'NEW_INPUTS.json',dict(integer_scale=2,units=new))
files=['run02/INPUTS.json','run02/RAW.jsonl','run02/SUMMARY.json','THRESHOLD_CERTIFICATE_PROOF.md','HISTORY_COUNT_CORRECTION.md','THRESHOLD_VALIDATION_PLAN.md','threshold_compile.py','threshold_check.py','validate_threshold01.py']
dump(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_hashes={name:sha(P/name) for name in files},new_inputs_sha256=sha(O/'NEW_INPUTS.json'),expected_existing=37248,expected_new=120,existing_outcomes_already_observed=True))
counts=collections.Counter();totals=collections.Counter();failures=[];exports=[]
with (O/'RAW.jsonl').open('x') as raw:
 for u,prior in zip(old_inputs['units'],old_raw):
  row=dict(kind='existing',id=u['id'],status='INVALID')
  if time.perf_counter()-start>570:row.update(status='TIMEOUT',reason='campaign clock cap')
  else:
   try:
    assert prior['input']==u['id'] and prior['status']=='SUCCESS'
    jobs=[old_inputs['types'][j] for j in u['jobs']]
    export=u['id'] in [15578,15596,31555]
    result=compile_thresholds(jobs,u['edges'],u['r'],u['kappa'],known_curve=prior['curve'],export=export)
    okay=result['exists']==prior['simultaneous_exists']
    if export:
     cert=result.pop('certificate');name=f"existing_{u['id']}.json";dump(O/name,cert);checked=check_certificate(cert);assert checked['common_optimum_exists']==result['exists'];exports.append(dict(file=name,check=checked))
    row.update(status='SUCCESS' if okay else 'FAILURE',root_margin=result['root_margin'],exists=result['exists'],threshold_states=result['threshold_states'],reference_existence_states=prior['existence_states'])
    totals['existing_threshold_states']+=result['threshold_states'];totals['existing_reference_states']+=prior['existence_states']
   except Exception as ex:row.update(status='INVALID',error=repr(ex))
  counts[row['status']]+=1
  if row['status']!='SUCCESS':failures.append(dict(kind=row['kind'],id=row['id'],status=row['status']))
  raw.write(json.dumps(row)+'\n')
  if (u['id']+1)%4096==0:raw.flush();print(json.dumps(dict(existing_done=u['id']+1,seconds=time.perf_counter()-start,statuses=dict(counts))),flush=True)
 for u in new:
  row=dict(kind='new',id=u['id'],status='INVALID')
  if time.perf_counter()-start>570:row.update(status='TIMEOUT',reason='campaign clock cap')
  else:
   try:
    result=compile_thresholds(u['jobs'],u['edges'],u['retries'],u['toll'],export=True)
    cert=result.pop('certificate');name=f"new_{u['id']:03}.json";dump(O/name,cert);checked=check_certificate(cert);exports.append(dict(file=name,check=checked))
    jobs=u['jobs'];n=len(jobs);full=(1<<n)-1;r=u['retries'];k=u['toll'];E=result['ceiling'];curve=result['curve'];pred=[sum(1<<a for a,b in u['edges'] if b==i) for i in range(n)]
    @lru_cache(None)
    def win(s,t,e,a):
     if not s:return a<=curve[min(e,E)]
     for i in range(n):
      if not(s>>i&1) or pred[i]&s:continue
      if all(win(s^(1<<i),t,e+o['c'],a+k+o['w']) or (t and win(s,t-1,e+o['c'],a+k)) for o in jobs[i]['observations']):return True
     return False
    exact=bool(win(full,r,0,0));okay=result['exists']==exact==checked['common_optimum_exists']
    row.update(status='SUCCESS' if okay else 'FAILURE',curve=curve,root_margin=result['root_margin'],exists=exact,threshold_states=result['threshold_states'],reference_states=win.cache_info().currsize,partial_min_count_exceeds_sigma=any(o['c']>j['sigma'] for j in jobs for o in j['observations']))
    totals['new_threshold_states']+=result['threshold_states'];totals['new_reference_states']+=win.cache_info().currsize
   except Exception as ex:row.update(status='INVALID',error=repr(ex))
  counts[row['status']]+=1
  if row['status']!='SUCCESS':failures.append(dict(kind=row['kind'],id=row['id'],status=row['status']))
  raw.write(json.dumps(row)+'\n')
base=json.loads((O/'existing_31555.json').read_text());controls=[]
for label in ['threshold','job','curve','ceiling']:
 c=copy.deepcopy(base)
 if label=='threshold':c['thresholds'][0]['value']+=1
 elif label=='job':next(x for x in c['thresholds'] if x['state']==c['root'])['job']=99
 elif label=='curve':c['curve'][0]+=1
 else:c['ceiling']+=1
 try:check_certificate(c);caught=False
 except (AssertionError,KeyError,ValueError):caught=True
 controls.append(dict(kind=label,detected=caught))
paths=[]
for name in ['existing_15578.json','existing_31555.json']:
 cert=json.loads((O/name).read_text());table={tuple(row['state']):row for row in cert['thresholds']};case=[]
 def visit(prefix):
  result=run_certificate_policy(cert,prefix)
  if result['completed']:
   e=sum(x['min_writes'] for x in result['trace']);assert result['cost']<=cert['curve'][min(e,cert['ceiling'])];assert len(prefix)<=len(cert['jobs'])+cert['retries'];case.append(result);return
  state=result['trace'][-1]['after'][:3] if prefix else cert['root'];job=table[tuple(state)]['job']
  for o in cert['jobs'][job]['observations']:visit(prefix+[o['mask']])
 visit([]);dump(O/(name.removesuffix('.json')+'_EXECUTABLE_PATHS.json'),case);paths.append(dict(certificate=name,terminal_paths=len(case),maximum_calls=max(len(x['trace']) for x in case),all_costs_match=True))
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if counts=={'SUCCESS':37368} and all(x['detected'] for x in controls) else 'FAIL',seconds=time.perf_counter()-start,expected_existing=37248,expected_new=120,statuses=dict(counts),counts=dict(totals),independent_export_checks=len(exports),negative_controls=controls,executable_policy_checks=paths,failures=failures,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,new_native_runs=0,scope='representation/checker validation on observed grid plus120 new mathematical profile cases')
dump(O/'EXPORT_CHECKS.json',exports);dump(O/'SUMMARY.json',result);print(json.dumps(result),flush=True)

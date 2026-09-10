from pathlib import Path
from functools import lru_cache
import collections,copy,datetime,hashlib,itertools,json,resource,time
P=Path(__file__).resolve().parent;O=P/'run01';O.mkdir();start=time.perf_counter()
def dump(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
units=[]
for n in range(1,4):
 es=list(itertools.combinations(range(n),2))
 for weights in itertools.product([2,4,8],repeat=n):
  for bits in range(1<<len(es)):
   edges=[list(e) for k,e in enumerate(es) if bits>>k&1]
   for r in range(4):
    for toll in [0,1,2,4,8,16]:
     units.append(dict(id=len(units),weights=list(weights),edges=edges,retries=r,toll=toll,budgets=list(range(n+r+3))))
assert len(units)==5688 and sum(len(u['budgets']) for u in units)==42084
dump(O/'INPUTS.json',dict(integer_scale=2,units=units))
dump(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),expected_conditions=5688,expected_roots=42084,source_hashes={n:sha(P/n) for n in ['PLAN.md','PROOF.md','run01.py']},input_sha256=sha(O/'INPUTS.json'),post_review_hypothesis=True,new_native_runs=0))
def equations(weights,edges,r,kappa):
 n=len(weights);full=(1<<n)-1;pred=[sum(1<<a for a,b in edges if b==i) for i in range(n)]
 def ready(s):return [i for i in range(n) if s>>i&1 and not(pred[i]&s)]
 @lru_cache(None)
 def known(s,b,t):
  if not s:return 0
  choices=[]
  for i in ready(s):
   child=s^(1<<i);w=weights[i]
   choices.append(kappa+w+known(child,b,t))
   cached=[kappa+known(child,b,t)]
   if b:cached.append(kappa+w+known(child,b-1,t))
   choices.append(max(cached))
   if t or b==0:
    cheap=[kappa+known(child,b,t)]
    if b:cheap.append(kappa+known(s,b-1,t-1))
    choices.append(max(cheap))
  return min(choices)
 @lru_cache(None)
 def threshold(s,b,t,select_max):
  if not s:return 0
  values=[]
  for i in ready(s):
   child=s^(1<<i);outs=[kappa+threshold(child,b,t,select_max)]
   if b:
    if t:outs.append(kappa+threshold(s,b-1,t-1,select_max))
    else:outs.append(kappa+weights[i]+threshold(child,b-1,t,select_max))
   values.append(max(outs))
  return (max if select_max else min)(values)
 return full,known,threshold
def verify(row):
 n=len(row['weights']);b=row['budget'];r=row['retries'];k=row['toll']
 F=sum(sorted(row['weights'],reverse=True)[:min(max(b-r,0),n)])
 expected=n*k+k*min(b,r)+F
 return row['threshold_min']==row['threshold_max']==expected and n*k+F<=row['known']<=expected and expected-row['known']<=k*min(b,r)
counts=collections.Counter();failures=[];total_states=collections.Counter();tight=0;examples=[]
with (O/'RAW.jsonl').open('x') as out:
 for u in units:
  full,known,threshold=equations(u['weights'],u['edges'],u['retries'],u['toll'])
  for b in u['budgets']:
   row=dict(input=u['id'],budget=b,status='INVALID')
   if time.perf_counter()-start>600:row.update(status='TIMEOUT',reason='campaign time cap')
   elif resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**3:row.update(status='INVALID',reason='observed RSS cap exceeded')
   else:
    try:
     row.update(weights=u['weights'],retries=u['retries'],toll=u['toll'],known=known(full,b,u['retries']),threshold_min=threshold(full,b,u['retries'],False),threshold_max=threshold(full,b,u['retries'],True))
     okay=verify(row)
     if len(u['weights'])==1 and b==u['retries']+1:
      okay=okay and row['known']==u['toll']+u['weights'][0] and row['threshold_max']-row['known']==u['retries']*u['toll'];tight+=1
     row['status']='SUCCESS' if okay else 'FAILURE'
     if u['weights']==[4] and u['retries']==1 and u['toll']==1:examples.append(copy.deepcopy(row))
    except Exception as ex:row.update(status='INVALID',error=repr(ex))
   counts[row['status']]+=1
   if row['status']!='SUCCESS':failures.append(row)
   out.write(json.dumps(row)+'\n')
  total_states['known']+=known.cache_info().currsize;total_states['threshold']+=threshold.cache_info().currsize
  if (u['id']+1)%1024==0:out.flush();print(json.dumps(dict(conditions=u['id']+1,statuses=dict(counts),seconds=time.perf_counter()-start)),flush=True)
base=next(x for x in examples if x['budget']==1);controls=[]
for name in ['threshold','comparator','toll','budget']:
 row=copy.deepcopy(base)
 if name=='threshold':row['threshold_min']+=1
 elif name=='comparator':row['known']=0
 elif name=='toll':row['toll']=3
 else:row['budget']=2
 controls.append(dict(kind=name,detected=not verify(row)))
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if counts=={'SUCCESS':42084} and all(x['detected'] for x in controls) else 'FAIL',seconds=time.perf_counter()-start,conditions=len(units),roots=sum(counts.values()),statuses=dict(counts),states=dict(total_states),tight_threshold_cases=tight,negative_controls=controls,one_job_examples=examples,failures=failures,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,new_native_runs=0,scope='Numerical corroboration in serial fresh-preparation subclass; the operation-level proof supplies the broader comparator lower bound. Threshold regret sharpness is not minimax regret across budget-unaware policies.')
dump(O/'SUMMARY.json',result);print(json.dumps(result),flush=True)

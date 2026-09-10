from pathlib import Path
from functools import lru_cache
import collections,copy,datetime,hashlib,itertools,json,resource,time
P=Path(__file__).resolve().parent;O=P/'run01';O.mkdir();start=time.perf_counter()
def dump(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
units=[]
for n in range(1,4):
 es=list(itertools.combinations(range(n),2));weights=list(itertools.product([1,2,4],repeat=n)) if n<3 else [(1,1,1),(1,2,4)]
 for w in weights:
  for local in itertools.product([0,1,2],repeat=n):
   for bits in range(1<<len(es)):
    edges=[list(e) for k,e in enumerate(es) if bits>>k&1]
    for s in range(sum(local)+1):
     for mode in [2,3]:units.append(dict(id=len(units),weights=list(w),local=list(local),shared=s,mode=mode,edges=edges,budgets=list(range(sum(local)+n+2))))
assert len(units)==4464 and sum(len(u['budgets']) for u in units)==35796
dump(O/'INPUTS.json',dict(units=units));dump(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256={n:sha(P/n) for n in ['PLAN.md','PROOF.md','run01.py']},input_sha256=sha(O/'INPUTS.json'),expected_conditions=4464,expected_roots=35796))
def make(u):
 w=u['weights'];n=len(w);pred=[sum(1<<a for a,b in u['edges'] if b==i) for i in range(n)];mode=u['mode'];full=(1<<n)-1
 def ready(S):return [i for i in range(n) if S>>i&1 and not(pred[i]&S)]
 def dec(t,i):return tuple(v-(j==i) for j,v in enumerate(t))
 @lru_cache(None)
 def direct(S,b,t,s,known):
  if not S:return 0
  choices=[]
  for i in ready(S):
   child=S^(1<<i);choices.append(w[i]+direct(child,b,t,s,known))
   if mode==3:choices.append(max([direct(child,b,t,s,known)]+([w[i]+direct(child,b-1,t,s,known)] if b else [])))
   if (t[i] and s) or (known and b==0):
    choices.append(max([direct(child,b,t,s,known)]+([direct(S,b-1,dec(t,i),s-1,known)] if b else [])))
  return min(choices)
 @lru_cache(None)
 def canonical(S,b,t,s,choose_max,count_calls):
  if not S:return 0
  choices=[]
  for i in ready(S):
   child=S^(1<<i);base=1 if count_calls else 0
   if t[i] and s:vals=[base+canonical(child,b,t,s,choose_max,count_calls)]+([base+canonical(S,b-1,dec(t,i),s-1,choose_max,count_calls)] if b else [])
   elif mode==2:vals=[base+(0 if count_calls else w[i])+canonical(child,b,t,s,choose_max,count_calls)]
   else:vals=[base+canonical(child,b,t,s,choose_max,count_calls)]+([base+(0 if count_calls else w[i])+canonical(child,b-1,t,s,choose_max,count_calls)] if b else [])
   choices.append(max(vals))
  return (max if choose_max else min)(choices)
 return full,direct,canonical
def activation(weights,costs,b):
 return max(sum(w for i,w in enumerate(weights) if bits>>i&1) for bits in range(1<<len(weights)) if sum(c for i,c in enumerate(costs) if bits>>i&1)<=b)
def verify(row):
 w=row['weights'];local=row['local'];s=row['shared'];b=row['budget'];mode=row['mode'];n=len(w)
 if mode==2:formula=max(activation(w,local,b),sum(w) if b>=s else 0)
 else:formula=max(activation(w,[r+1 for r in local],b),sum(sorted(w,reverse=True)[:max(0,b-s)]))
 okay=row['direct']==row['canonical_min']==row['canonical_max']==formula and row['calls_min']==row['calls_max']==n+min(b,s)
 if s==sum(local):
  known=activation(w,[r+1 for r in local],b) if mode==3 else activation(w,local,b-1) if b else 0
  okay=okay and row['known']==known
 return okay
counts=collections.Counter();states=collections.Counter();failures=[];examples=[];local_known=0
with (O/'RAW.jsonl').open('x') as out:
 for u in units:
  full,direct,canonical=make(u);local=tuple(u['local']);s=u['shared']
  for b in u['budgets']:
   row=dict(input=u['id'],budget=b,status='INVALID')
   if time.perf_counter()-start>600:row.update(status='TIMEOUT',reason='campaign time cap')
   elif resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**3:row.update(status='INVALID',reason='observed RSS cap')
   else:
    try:
     row.update(weights=u['weights'],local=u['local'],shared=s,mode=u['mode'],direct=direct(full,b,local,s,False),known=direct(full,b,local,s,True),canonical_min=canonical(full,b,local,s,False,False),canonical_max=canonical(full,b,local,s,True,False),calls_min=canonical(full,b,local,s,False,True),calls_max=canonical(full,b,local,s,True,True))
     row['status']='SUCCESS' if verify(row) else 'FAILURE'
     if s==sum(local):local_known+=1
     if u['weights']==[1,4] and u['local']==[0,2] and u['edges']==[]:examples.append(copy.deepcopy(row))
    except Exception as ex:row.update(status='INVALID',error=repr(ex))
   counts[row['status']]+=1
   if row['status']!='SUCCESS':failures.append(row)
   out.write(json.dumps(row)+'\n')
  states['direct']+=direct.cache_info().currsize;states['canonical']+=canonical.cache_info().currsize
  if (u['id']+1)%1024==0:out.flush();print(json.dumps(dict(conditions=u['id']+1,statuses=dict(counts),seconds=time.perf_counter()-start)),flush=True)
controls=[]
for kind in ['direct','local_cap','shared_cap','budget']:
 base=next(x for x in examples if x['mode']==3 and x['shared']==2 and x['budget']==2);row=copy.deepcopy(base)
 if kind=='direct':row['direct']+=1
 elif kind=='local_cap':row['local']=[0,0]
 elif kind=='shared_cap':row['shared']=0
 else:row['budget']=3
 controls.append(dict(kind=kind,detected=not verify(row)))
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if counts=={'SUCCESS':35796} and all(x['detected'] for x in controls) else 'FAIL',seconds=time.perf_counter()-start,conditions=len(units),roots=sum(counts.values()),statuses=dict(counts),states=dict(states),local_known_budget_checks=local_known,negative_controls=controls,examples=examples,failures=failures,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,new_native_runs=0,scope='Authored finite corroboration in serial fresh-preparation subclass; all-program lower bounds rely on the mathematical proof and operation restrictions, not numerical coverage.')
dump(O/'SUMMARY.json',result);print(json.dumps(result),flush=True)

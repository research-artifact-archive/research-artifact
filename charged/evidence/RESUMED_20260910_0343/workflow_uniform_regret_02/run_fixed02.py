from pathlib import Path
from functools import lru_cache
import collections,copy,datetime,hashlib,importlib.util,itertools,json,resource,time

P=Path(__file__).resolve().parent
O=P/'fixed02';O.mkdir()
start=time.monotonic();deadline=start+240
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def budget():
 if time.monotonic()>deadline:raise TimeoutError('240-second campaign cap')
 if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**3:raise MemoryError('2GiB peak RSS cap')
source=P.parent/'partial_repair_toll_dag_01/threshold_compile.py'
spec=importlib.util.spec_from_file_location('archived_thresholds',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def profile(weights,footprints):
 distances={0:0};queue=[0]
 for old in queue:
  for f in footprints:
   d=old|f
   if d not in distances:distances[d]=distances[old]+1;queue.append(d)
 obs=[dict(mask=d,c=c,w=sum(w for i,w in enumerate(weights) if d>>i&1)) for d,c in sorted(distances.items())]
 g=[max(o['w'] for o in obs if o['c']<=b) for b in range(len(weights)+1)]
 return dict(weights=weights,footprints=footprints,observations=obs,G=g,W=g[-1],sigma=next(i for i,v in enumerate(g) if v==g[-1]))
types=[profile([2],[1]),profile([6],[1]),profile([2,4],[1,2]),profile([2,2,4],[1,2,7])]
units=[]
for ids in itertools.product(range(4),repeat=2):
 for edges in [[],[(0,1)],[(1,0)]]:
  for k in [0,1,2,4,6]:units.append(dict(id=len(units),jobs=list(ids),edges=edges,r=2,kappa=k))
for ids in itertools.product(range(4),repeat=3):
 for mask in range(8):
  edges=[e for j,e in enumerate([(0,1),(0,2),(1,2)]) if mask>>j&1]
  for r in range(2):
   for k in [0,1,2,4,6]:units.append(dict(id=len(units),jobs=list(ids),edges=edges,r=r,kappa=k))
assert len(units)==5360
put(O/'INPUTS.json',dict(integer_scale=2,types=types,units=units))
put(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),units=5360,code_sha256=sha(Path(__file__)),inputs_sha256=sha(O/'INPUTS.json'),plan_sha256=sha(P/'FIXED_PLAN02.md'),proof_sha256=sha(P/'PROOF.md'),constructor_sha256=sha(source),new_native_runs=0,prior540_observed=True))

def enumerate_vectors(jobs,edges,r,k):
 n=len(jobs);full=(1<<n)-1
 pred=[sum(1<<a for a,b in edges if b==i) for i in range(n)]
 M=(n+r)*max(o['c'] for j in jobs for o in j['observations'])
 combinations=0;max_front=0
 def pareto(vectors):
  nonlocal max_front
  budget();front=[]
  for v in sorted(set(vectors),key=lambda v:(sum(v),v)):
   if not any(all(a<=b for a,b in zip(u,v)) for u in front):front.append(v)
  max_front=max(max_front,len(front));return tuple(front)
 @lru_cache(None)
 def policies(s,t):
  nonlocal combinations
  budget()
  if not s:return ((0,)*(M+1),)
  choices=[]
  for i in range(n):
   if not(s>>i&1) or pred[i]&s:continue
   partial=((-1,)*(M+1),)
   for o in jobs[i]['observations']:
    branches=[]
    for v in policies(s^(1<<i),t):branches.append(tuple(-1 if b<o['c'] else k+o['w']+v[b-o['c']] for b in range(M+1)))
    if t:
     for v in policies(s,t-1):branches.append(tuple(-1 if b<o['c'] else k+v[b-o['c']] for b in range(M+1)))
    branches=pareto(branches);combinations+=len(partial)*len(branches)
    partial=pareto(tuple(max(x,y) for x,y in zip(a,b)) for a in partial for b in branches)
   choices.extend(partial)
  return pareto(choices)
 vectors=policies(full,r)
 curve=[min(v[b] for v in vectors) for b in range(M+1)]
 regret=min(max(x-y for x,y in zip(v,curve)) for v in vectors)
 return dict(max_budget=M,vectors=vectors,curve=curve,regret=regret,policy_states=policies.cache_info().currsize,cartesian_combinations=combinations,max_frontier=max_front)

def emitted_policy_curve(certificate,delta,M):
 jobs=certificate['jobs'];n=len(jobs);E=certificate['ceiling'];k=certificate['toll'];rows={tuple(x['state']):x for x in certificate['thresholds']}
 @lru_cache(None)
 def play(s,t,e,paid,b):
  if not s:return paid
  i=rows[s,t,e]['job'];out=[]
  for o in jobs[i]['observations']:
   if o['c']>b:continue
   nxt=min(e+o['c'],E);after=s^(1<<i)
   if paid+k+o['w']<=rows[after,t,nxt]['value']+delta:
    out.append(play(after,t,nxt,paid+k+o['w'],b-o['c']))
   elif t and paid+k<=rows[s,t-1,nxt]['value']+delta:
    out.append(play(s,t-1,nxt,paid+k,b-o['c']))
   else:raise AssertionError('no shifted action')
  return max(out)
 curve=[play((1<<n)-1,certificate['retries'],0,0,b) for b in range(M+1)]
 return curve,play.cache_info().currsize

def check_claim(claim,vectors):
 M=len(vectors[0]);K=[min(v[b] for v in vectors) for b in range(M)]
 delta=min(max(v[b]-K[b] for b in range(M)) for v in vectors)
 assert claim['curve']==K and claim['regret']==delta
 assert claim['policy_curve']==claim['replayed_policy_curve']
 assert max(x-y for x,y in zip(claim['policy_curve'],K))==delta

counts=collections.Counter();totals=collections.Counter();examples=[];controls=[]
with (O/'RAW.jsonl').open('x') as raw:
 for u in units:
  row=dict(input=u['id'])
  try:
   budget();jobs=[types[i] for i in u['jobs']]
   direct=enumerate_vectors(jobs,u['edges'],u['r'],u['kappa'])
   result=module.compile_thresholds(jobs,u['edges'],u['r'],u['kappa'],export=True)
   E=result['ceiling'];K=direct['curve'];delta=-result['root_margin']
   checks=dict(informed_curve=K[:E+1]==result['curve'][:E+1],plateau=all(v==K[E] for v in K[E:]),loss=delta==direct['regret'],nonnegative=delta>=0,zero_iff=(delta==0)==result['exists'])
   pc,ps=emitted_policy_curve(result['certificate'],delta,direct['max_budget'])
   checks['policy_attains_loss']=max(x-y for x,y in zip(pc,K))==delta
   row.update(status='SUCCESS' if all(checks.values()) else 'FAILURE',checks=checks,regret=delta,root_margin=result['root_margin'],curve=K,policy_curve=pc,pareto_vectors=len(direct['vectors']),max_budget=direct['max_budget'],max_frontier=direct['max_frontier'],cartesian_combinations=direct['cartesian_combinations'],policy_states=direct['policy_states'],extraction_replay_states=ps,threshold_states=result['threshold_states'])
   put(O/('unit_%03d.json'%u['id']),dict(input=u,integer_scale=2,direct=direct,threshold=result['certificate'],claim=row))
   claim=dict(curve=K,regret=delta,policy_curve=pc,replayed_policy_curve=pc)
   check_claim(claim,direct['vectors'])
   if not controls:
    for mutation in ['lower_loss','higher_loss','changed_comparator','changed_policy']:
     bad=copy.deepcopy(claim)
     if mutation=='lower_loss':bad['regret']-=1
     elif mutation=='higher_loss':bad['regret']+=1
     elif mutation=='changed_comparator':bad['curve'][0]+=1
     else:bad['policy_curve'][0]+=1
     try:check_claim(bad,direct['vectors']);detected=False
     except AssertionError:detected=True
     controls.append(dict(mutation=mutation,detected=detected))
   for k in ['pareto_vectors','cartesian_combinations','policy_states','extraction_replay_states','threshold_states']:totals[k]+=row[k]
   totals['budget_coordinates']+=len(K);totals['positive_loss']+=int(delta>0);totals['zero_loss']+=int(delta==0)
   if delta>0 and len(examples)<12:examples.append(dict(input=u,regret=delta,curve=K,policy_curve=pc,vectors=direct['vectors']))
  except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
  except Exception as e:row.update(status='INVALID',error=repr(e))
  counts[row['status']]+=1;raw.write(json.dumps(row)+'\n');raw.flush()
  if (u['id']+1)%500==0:print(json.dumps(dict(done=u['id']+1,seconds=time.monotonic()-start,statuses=dict(counts))),flush=True)
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if counts=={'SUCCESS':5360} and all(x['detected'] for x in controls) else 'FAIL',all_units=5360,statuses=dict(counts),seconds=time.monotonic()-start,integer_scale=2,totals=dict(totals),controls=controls,examples=examples,new_native_runs=0,scope='Fixed5360 finite policy-vector comparison and shifted policy extraction; no native calibration or independent proof certification')
put(O/'SUMMARY.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='examples'}),flush=True)

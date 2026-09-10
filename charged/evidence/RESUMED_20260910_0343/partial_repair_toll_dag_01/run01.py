from pathlib import Path
from functools import lru_cache
import collections,copy,datetime,hashlib,itertools,json,resource,time
P=Path(__file__).resolve().parent;O=P/'run01';O.mkdir();start=time.perf_counter()
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
def dump(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def profile(weights,footprints):
 m=len(weights);cost={0:0};queue=[0]
 for union in queue:
  for footprint in footprints:
   nxt=union|footprint
   if nxt not in cost:cost[nxt]=cost[union]+1;queue.append(nxt)
 obs=[dict(mask=d,c=c,w=sum(w for i,w in enumerate(weights) if d>>i&1)) for d,c in sorted(cost.items())]
 G=[max(o['w'] for o in obs if o['c']<=b) for b in range(m+1)]
 return dict(weights=list(weights),footprints=list(footprints),observations=obs,G=G,W=G[-1],sigma=next(i for i,x in enumerate(G) if x==G[-1]))
def check(p):
 fs=p['footprints'];weights=p['weights'];dist={0:0}
 for k in range(1,len(weights)+1):
  for seq in itertools.product(fs,repeat=k):
   d=0
   for x in seq:d|=x
   dist.setdefault(d,k)
 expected=[dict(mask=d,c=c,w=sum(w for i,w in enumerate(weights) if d>>i&1)) for d,c in sorted(dist.items())]
 g=[max(o['w'] for o in expected if o['c']<=b) for b in range(len(weights)+1)]
 assert p['observations']==expected and p['G']==g and p['W']==g[-1] and p['sigma']==next(i for i,x in enumerate(g) if x==g[-1])
types=[profile([2*w],[1]) for w in [1,2,3]]
for ws in [(1,1),(1,2),(2,3)]:
 for mask in range(1,8):types.append(profile([2*w for w in ws],[f for i,f in enumerate([1,2,3]) if mask>>i&1]))
for i,p in enumerate(types):p['id']=i;check(p)
assert len(types)==24
rep=[0,2]+[p['id'] for p in types if p['weights'] in [[2,2],[2,4]] and p['footprints']==[1,2]]
assert len(rep)==4
inputs=[]
for ids in itertools.product(range(24),repeat=2):
 for edges in [[],[(0,1)],[(1,0)]]:
  for r in range(3):
   for toll in [1,2,4,6,8,12]:inputs.append(dict(id=len(inputs),jobs=list(ids),edges=edges,r=r,kappa=toll))
for ids in itertools.product(rep,repeat=3):
 for mask in range(8):
  edges=[e for i,e in enumerate([(0,1),(0,2),(1,2)]) if mask>>i&1]
  for r in range(2):
   for toll in [1,2,4,6,8,12]:inputs.append(dict(id=len(inputs),jobs=list(ids),edges=edges,r=r,kappa=toll))
assert len(inputs)==37248
dump(O/'INPUTS.json',dict(integer_scale=2,types=types,units=inputs,known_counterexample_already_observed=True))
dump(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),code_sha256=sha(Path(__file__)),inputs_sha256=sha(O/'INPUTS.json'),plan_sha256=sha(P/'PLAN.md'),proof_sha256=sha(P/'PROOF.md'),units=len(inputs),new_native_runs=0))
controls=[]
for field in ['G','W','sigma','observations']:
 p=copy.deepcopy(types[rep[-1]])
 if field=='G':p[field][0]+=1
 elif field=='observations':p[field][-1]['c']+=1
 else:p[field]+=1
 try:check(p);caught=False
 except AssertionError:caught=True
 controls.append(dict(field=field,detected=caught))
assert all(c['detected'] for c in controls)
counts=collections.Counter();states=collections.Counter();obligations=collections.Counter();separations=[];failures=[];examples=[]
with (O/'RAW.jsonl').open('x') as out:
 for u in inputs:
  row=dict(input=u['id'],status='INVALID')
  if time.perf_counter()-start>=570:row.update(status='TIMEOUT',reason='campaign clock cap, unit not started')
  else:
   try:
    jobs=[types[j] for j in u['jobs']];n=len(jobs);full=(1<<n)-1;r=u['r'];toll=u['kappa']
    pred=[sum(1<<a for a,b in u['edges'] if b==j) for j in range(n)]
    succ=[sum(1<<b for a,b in u['edges'] if a==j) for j in range(n)]
    @lru_cache(None)
    def ready(s):return tuple(i for i in range(n) if s>>i&1 and not pred[i]&s)
    @lru_cache(None)
    def aware(s,b,t):
     if not s:return 0
     return min(max(toll+min(o['w']+aware(s^(1<<i),b-o['c'],t),aware(s,b-o['c'],t-1) if t else float('inf')) for o in jobs[i]['observations'] if o['c']<=b) for i in ready(s))
    ceiling=sum(j['sigma'] for j in jobs)+r*max(j['sigma'] for j in jobs)
    curve=[aware(full,b,r) for b in range(ceiling+2)]
    cap=n*toll+sum(j['W'] for j in jobs)
    first=[0]*(ceiling+2)
    for j in jobs:
     prev=first
     first=[max(prev[b-k]+j['G'][min(k,len(j['G'])-1)] for k in range(b+1)) for b in range(ceiling+2)]
    first=[v+n*toll for v in first]
    @lru_cache(None)
    def win(s,t,e,cost):
     if not s:return cost<=curve[min(e,ceiling)]
     for i in ready(s):
      all_ok=True
      for o in jobs[i]['observations']:
       if win(s^(1<<i),t,e+o['c'],cost+toll+o['w']):continue
       if t and win(s,t-1,e+o['c'],cost+toll):continue
       all_ok=False;break
      if all_ok:return True
     return False
    exists=win(full,r,0,0);first_opt=first==curve
    checks=dict(nondecreasing=all(a<=b for a,b in zip(curve,curve[1:])),full_cap_by_ceiling=curve[ceiling]==curve[-1]==cap,first_is_upper=all(a<=f for a,f in zip(curve,first)),first_implies_exists=(not first_opt or exists))
    if r==0:checks['no_retries']=exists and first_opt;obligations['no_retries']+=1
    if toll>=max(j['W'] for j in jobs):checks['sufficient_every_DAG']=exists and first_opt;obligations['sufficient_every_DAG']+=1
    if r and not u['edges']:checks['independent_iff']=exists==(toll>=max(j['W'] for j in jobs));obligations['independent_iff']+=1
    if r and any(not succ[i] and jobs[i]['W']>toll for i in range(n)):checks['large_sink_impossible']=not exists;obligations['large_sink_impossible']+=1
    if exists and not first_opt:separations.append(u['id'])
    row.update(status='SUCCESS' if all(checks.values()) else 'FAILURE',curve=curve,first_accept_curve=first,simultaneous_exists=exists,first_accept_optimal=first_opt,checks=checks,ceiling=ceiling,known_states=aware.cache_info().currsize,existence_states=win.cache_info().currsize)
    states['known_budget_roots']+=len(curve);states['known_game_states']+=aware.cache_info().currsize;states['existence_states']+=win.cache_info().currsize;states['existence_tests']+=1
    if n==2 and [j['weights'] for j in jobs]==[[2,4],[2]] and [j['footprints'] for j in jobs]==[[1,2],[1]] and toll==4 and r==1:examples.append(dict(input=u,row=row))
    if row['status']=='FAILURE':failures.append(u['id'])
   except Exception as ex:row.update(status='INVALID',error=repr(ex));failures.append(u['id'])
  counts[row['status']]+=1;out.write(json.dumps(row)+'\n')
  if (u['id']+1)%1024==0:out.flush();print(json.dumps(dict(done=u['id']+1,seconds=time.perf_counter()-start,counts=dict(counts))),flush=True)
assert len(examples)==3 or counts['TIMEOUT'] or counts['INVALID']
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if counts=={'SUCCESS':len(inputs)} else 'FAIL',all_units=len(inputs),statuses=dict(counts),seconds=time.perf_counter()-start,integer_scale=2,counts=dict(states),theorem_obligations=dict(obligations),negative_controls=controls,already_observed_examples=examples,existence_without_always_accept=separations,failures=failures,new_native_runs=0,scope='bounded mathematical corroboration; author-generated inputs, not source calibration or observed human benefit')
dump(O/'SUMMARY.json',summary)
print(json.dumps(summary),flush=True)

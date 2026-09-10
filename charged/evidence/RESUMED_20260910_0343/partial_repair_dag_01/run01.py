from pathlib import Path
from functools import lru_cache
import collections,datetime,hashlib,itertools,json,signal,time,copy
P=Path(__file__).resolve().parent;O=P/'run01';O.mkdir();start=time.perf_counter()
def dump(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def profile(weights,footprints):
 m=len(weights);dist={0:0};queue=[0]
 for d in queue:
  for f in footprints:
   nd=d|f
   if nd not in dist:dist[nd]=dist[d]+1;queue.append(nd)
 vals={d:sum(w for j,w in enumerate(weights) if d>>j&1) for d in dist}
 g=[max(vals[d] for d in dist if dist[d]<=k) for k in range(m+1)]
 return dict(weights=list(weights),footprints=list(footprints),observations=[dict(mask=d,c=dist[d],w=vals[d]) for d in sorted(dist)],G=g,W=g[-1],sigma=next(k for k,v in enumerate(g) if v==g[-1]))
def verify_profile(p):
 w=p['weights'];fs=p['footprints'];m=len(w);all_unions={0:0}
 for k in range(1,m+1):
  for word in itertools.product(fs,repeat=k):
   union=0
   for f in word:union|=f
   all_unions.setdefault(union,k)
 expected={d:(k,sum(w[j] for j in range(m) if d>>j&1)) for d,k in all_unions.items()}
 assert {o['mask']:(o['c'],o['w']) for o in p['observations']}==expected
 g=[max(v for k,v in expected.values() if k<=b) for b in range(m+1)]
 assert p['G']==g and p['W']==max(g) and p['sigma']==next(i for i,x in enumerate(g) if x==max(g))
types=[]
for w in [1,2,3]:types.append(profile([w],[1]))
for weights in [(1,1),(1,2),(2,3)]:
 for mask in range(1,8):types.append(profile(weights,[f for bit,f in enumerate([1,2,3]) if mask>>bit&1]))
assert len(types)==24
for i,t in enumerate(types):t['id']=i;verify_profile(t)
rep=[0,2]+[t['id'] for t in types if t['weights'] in [[1,1],[1,2]] and t['footprints']==[1,2]]
assert len(rep)==4
inputs=[]
for ids in itertools.product(range(24),repeat=2):
 for edges in [[],[(0,1)],[(1,0)]]:
  for r in range(4):inputs.append(dict(id=len(inputs),jobs=list(ids),edges=edges,r=r,existence_check=r<=2))
for ids in itertools.product(rep,repeat=3):
 for mask in range(8):
  edges=[edge for bit,edge in enumerate([(0,1),(0,2),(1,2)]) if mask>>bit&1]
  for r in range(4):inputs.append(dict(id=len(inputs),jobs=list(ids),edges=edges,r=r,existence_check=r<=1))
assert len(inputs)==8960
dump(O/'INPUTS.json',dict(types=types,representatives=rep,units=inputs,known_example_already_observed=True))
dump(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs_sha256=sha(O/'INPUTS.json'),code_sha256=sha(Path(__file__)),plan_sha256=sha(P/'PLAN.md'),proof_sha256=sha(P/'PROOF.md'),expected_units=len(inputs),expected_existence=sum(u['existence_check'] for u in inputs),new_native_runs=0,no_exclusions=True))
controls=[]
for key in ['G','W','sigma','observations']:
 p=copy.deepcopy(types[rep[-1]])
 if key=='G':p[key][0]+=1
 elif key in ['W','sigma']:p[key]+=1
 else:p[key][-1]['c']+=1
 try:verify_profile(p);caught=False
 except AssertionError:caught=True
 controls.append(dict(name='corrupt_'+key,detected=caught))
assert all(c['detected'] for c in controls)
summary=collections.Counter();failed=[];known_roots=existence_total=states_known=states_unaware=0
with (O/'RAW.jsonl').open('x') as raw:
 for u in inputs:
  row=dict(input=u['id'],status='INVALID')
  if time.perf_counter()-start>585:
   row.update(status='TIMEOUT',reason='campaign time cap; unit not started')
  else:
   try:
    js=[types[i] for i in u['jobs']];n=len(js);r=u['r'];full=(1<<n)-1
    pred=[sum(1<<a for a,b in u['edges'] if b==i) for i in range(n)]
    @lru_cache(None)
    def ready(s):return tuple(i for i in range(n) if s>>i&1 and not(pred[i]&s))
    @lru_cache(None)
    def aware(s,b,t):
     if not s:return 0
     candidates=[]
     for i in ready(s):
      branch=[]
      for o in js[i]['observations']:
       if o['c']>b:continue
       a=o['w']+aware(s^(1<<i),b-o['c'],t)
       if t:a=min(a,aware(s,b-o['c'],t-1))
       branch.append(a)
      candidates.append(max(branch))
     return min(candidates)
    sigma=sum(j['sigma'] for j in js);wtotal=sum(j['W'] for j in js);bsat=sigma+r*max(j['sigma'] for j in js)
    curve=[aware(full,b,r) for b in range(bsat+2)];known_roots+=len(curve);states_known+=aware.cache_info().currsize
    sat=all(j['sigma']==1 for j in js)
    checks={'nondecreasing':all(a<=b for a,b in zip(curve,curve[1:])), 'zero_through_r':all(x==0 for x in curve[:r+1]),'first_full_at_bsat':curve[bsat]==wtotal and curve[bsat-1]<wtotal and curve[-1]==wtotal}
    if sat:
     weights=sorted([j['W'] for j in js],reverse=True);want=[sum(weights[:min(max(b-r,0),n)]) for b in range(bsat+2)]
     checks['saturated_curve']=curve==want
    elif r:checks['nonsaturated_separation']=curve[sigma+r]<wtotal
    if not r:
     convolution=[0]*(bsat+2)
     for j in js:
      old=convolution;convolution=[max(old[b-k]+j['G'][min(k,len(j['G'])-1)] for k in range(b+1)) for b in range(bsat+2)]
     checks['r0_convolution']=curve==convolution
    if u['existence_check']:
     def goal(e):return curve[min(e,bsat)]
     @lru_cache(None)
     def win(s,t,e,ell):
      if not s:return ell<=goal(e)
      for i in ready(s):
       ok=True
       for o in js[i]['observations']:
        if win(s^(1<<i),t,e+o['c'],ell+o['w']):continue
        if t and win(s,t-1,e+o['c'],ell):continue
        ok=False;break
       if ok:return True
      return False
     existence=win(full,r,0,0);existence_total+=1;states_unaware+=win.cache_info().currsize
     checks['quantified_one_policy_existence']=existence==(r==0 or sat)
     row.update(unaware_exists=existence,unaware_states=win.cache_info().currsize)
    row.update(status='SUCCESS' if all(checks.values()) else 'FAILURE',curve=curve,known_states=aware.cache_info().currsize,checks=checks,Sigma=sigma,W=wtotal,B_sat=bsat,all_one_write_saturated=sat)
    if row['status']!='SUCCESS':failed.append(row)
   except Exception as e:row.update(status='INVALID',error=repr(e));failed.append(row)
  summary[row['status']]+=1;raw.write(json.dumps(row)+'\n')
  if (u['id']+1)%512==0:
   raw.flush();print(json.dumps(dict(done=u['id']+1,statuses=dict(summary),seconds=time.perf_counter()-start)),flush=True)
exjs=[profile([1,1],[1,2]),profile([1],[1])]
# The fixed example is already present in the broad grid; retrieve all three order choices.
example_ids=[u['id'] for u in inputs if len(u['jobs'])==2 and [types[i]['weights'] for i in u['jobs']]==[[1,1],[1]] and [types[i]['footprints'] for i in u['jobs']]==[[1,2],[1]] and u['r']==1]
example=[]
for line in (O/'RAW.jsonl').read_text().splitlines():
 row=json.loads(line)
 if row['input'] in example_ids:example.append(row)
assert len(example)==3
example_ok=all(x.get('curve',[])[:6]==[0,0,1,2,2,3] for x in example)
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if summary=={'SUCCESS':len(inputs)} and example_ok else 'FAIL',seconds=time.perf_counter()-start,all_units=len(inputs),statuses=dict(summary),known_budget_roots=known_roots,known_states=states_known,quantified_existence_units=existence_total,quantified_existence_states=states_unaware,negative_controls=controls,already_observed_example_ids=example_ids,already_observed_example_match=example_ok,failures=failed,new_native_runs=0,scope='finite corroboration of a general proof; not new software population or native equivalence')
dump(O/'SUMMARY.json',result);print(json.dumps(result),flush=True)

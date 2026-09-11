from pathlib import Path
from functools import lru_cache
from itertools import product, permutations
import datetime, gzip, hashlib, json, time, traceback, os

P=Path(__file__).resolve().parent
O=P/'run02'; O.mkdir(exist_ok=False)
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(name,x): (O/name).write_text(json.dumps(x,indent=2)+'\n')
def top(xs,k): return sum(sorted(xs,reverse=True)[:k])
def graphs(n):
    base=[(0,1)]+[(1,i) for i in range(2,n)]
    candidates=[base]+[base+list(zip(order,order[1:])) for order in permutations(range(2,n))]
    return sorted(set(tuple(sorted(set(es))) for es in candidates))
inputs=[]
for family in ['heterogeneous','uniform']:
    for n in [4,5]:
        types=list(product([1,2,3],[0,1,3,8])) if n==4 else [(1,0),(1,1),(1,3),(1,8),(3,0),(3,3)]
        vectors=(product(types,repeat=n) if family=='heterogeneous'
                 else (tuple(zip(p,[h]*n)) for p in product([1,2],repeat=n) for h in [0,1,3,8]))
        for vector in vectors:
            inputs.append({'id':len(inputs),'family':family,'p':[x[0] for x in vector],
                           'h':[x[1] for x in vector],'graphs':graphs(n)})
assert len(inputs)==28704
assert sum(len(x['graphs']) for x in inputs)==117728
write('INPUTS.json',inputs)
sources=[P/'PROTOCOL01.md',P/'PROTOCOL02.md',P/'HYPOTHESIS02.md',P/'run01/SUMMARY.json',Path(__file__),O/'INPUTS.json']+[P.parent/x for x in [
 'charged_residual_01/PROOF03.md','charged_residual_01/check01.py',
 'charged_residual_01/AUTHOR_THRESHOLD_CHECK03.md','residual_safety_01/PROOF02.md']]
write('START.json',{'utc':stamp(),'pid':os.getpid(),'timeout_seconds':120,'planned_vectors':28704,
 'planned_games':117728,'sha256':{str(x.relative_to(P.parent)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sources}})
start=time.monotonic(); end=min(start+120,start+max(0,datetime.datetime(2026,9,11,4,18,tzinfo=datetime.timezone.utc).timestamp()-time.time()))
errors=[];comparisons=[];witnesses=[];statuses=[];counts={'games':0,'states':0,'uniform_states':0,'common_state_comparisons':0,'state_differences':0,'fresh_permission_differences':0,'prefix_value_differences':0}
timedout=False
with gzip.open(O/'STATES.jsonl.gz','wt') as raw:
 for inp in inputs:
  p=inp['p']; q=[x+y for x,y in zip(p,inp['h'])]; n=len(p); full=(1<<n)-1
  tables=[]
  for gi,edges in enumerate(inp['graphs']):
   if time.monotonic()>end:
    statuses.append({'id':inp['id'],'graph':gi,'status':'UNEXECUTED_AFTER_TIMEOUT'})
    timedout=True; continue
   try:
    pred=[0]*n
    for i,j in edges: pred[j]|=1<<i
    def ready(d): return [i for i in range(n) if not d>>i&1 and pred[i]&d==pred[i]]
    @lru_cache(None)
    def v(d,k):
     if d==full:return top(q,k)
     return max(x for i in ready(d) for x in [v(d|1<<i,k)-p[i],min(v(d|1<<i,k),v(d|1<<i,k+1)-q[i])])
    rows={}
    for d in range(full+1):
     if any(d>>i&1 and pred[i]&d!=pred[i] for i in range(n)): continue
     for k in range(d.bit_count()+1):
      value=v(d,k); c=top([q[i] for i in range(n) if d>>i&1],k)
      row={'input':inp['id'],'graph':gi,'D':d,'k':k,'V':value,'C':c,'candidate_A':top([q[i] if d>>i&1 else inp['h'][i] for i in range(n)],k),'actions':[
       {'job':i,'fresh_threshold':v(d|1<<i,k)-p[i],'cached_threshold':min(v(d|1<<i,k),v(d|1<<i,k+1)-q[i])} for i in ready(d)]}
      rows[d,k]=row; raw.write(json.dumps(row,separators=(',',':'))+'\n');counts['states']+=1
      if value!=row['candidate_A']:errors.append({'kind':'CANDIDATE_FALSIFIER','row':row})
      if value<c:errors.append({'kind':'insufficient_V','row':row})
      if inp['family']=='uniform':
       counts['uniform_states']+=1
       if value!=c:errors.append({'kind':'uniform_unequal','row':row})
    tables.append((gi,rows)); counts['games']+=1
    statuses.append({'id':inp['id'],'graph':gi,'status':'SUCCESS','states':len(rows)})
   except Exception:
    err={'id':inp['id'],'graph':gi,'status':'EXCEPTION','traceback':traceback.format_exc()};errors.append(err);statuses.append(err)
  record={'id':inp['id'],'family':inp['family'],'p':p,'h':inp['h'],'q':q,'prefix':{'D':1,'k':1,'ell':q[0],'target':1},'graphs':[]}
  for gi,rows in tables:
   row=rows[1,1]; f=rows[3,1]['V']-p[1]
   record['graphs'].append({'graph':gi,'edges':inp['graphs'][gi],'V_prefix':row['V'],'fresh_threshold':f,'fresh_safe':q[0]<=f})
  if len(tables)==len(inp['graphs']):
   if len(set(x['fresh_safe'] for x in record['graphs']))>1:
    witnesses.append(record); counts['fresh_permission_differences']+=1
   if len(set(x['V_prefix'] for x in record['graphs']))>1:counts['prefix_value_differences']+=1
   common=set.intersection(*(set(rows) for _,rows in tables))
   for state in common:
    counts['common_state_comparisons']+=1
    vals=[rows[state]['V'] for _,rows in tables]
    if len(set(vals))>1:counts['state_differences']+=1
  comparisons.append(record)
write('COMPARISONS.json',comparisons);write('WITNESSES.json',witnesses);write('ERRORS.json',errors);write('STATUSES.json',statuses)
witnesses.sort(key=lambda x:(len(x['p']),sum(x['q']),max(x['q']),x['p'],x['h']))
write('MINIMAL_IN_POPULATION.json',witnesses[:1])
summary={'status':'SUCCESS' if not errors and not timedout and counts['games']==117728 else 'FAILURE_OR_INCOMPLETE','counts':counts,'errors':len(errors),'timeout':timedout,'seconds':time.monotonic()-start,'finished_utc':stamp(),'witness':witnesses[:1]}
write('SUMMARY.json',summary);print(json.dumps(summary,indent=2))

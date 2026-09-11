from pathlib import Path
from functools import lru_cache
from itertools import product
import datetime,gzip,hashlib,json,time
P=Path(__file__).resolve().parent;O=P/'check01';O.mkdir(exist_ok=False)
start=time.monotonic();deadline=start+60

def top(q,k):return sum(sorted(q,reverse=True)[:max(0,k)])
def write(name,data):(O/name).write_text(json.dumps(data,indent=2)+'\n')
def population():
 for n in range(1,5):
  es=[(i,j) for i in range(n) for j in range(i+1,n)]
  for mask in range(1<<len(es)):
   edges=[e for j,e in enumerate(es) if mask>>j&1]
   for p in product((1,3,7),repeat=n):
    for h in (0,1,3):yield {'p':p,'h':[h]*n,'edges':edges,'family':'uniform'}
 for name,p,h in [('A',[1,1,990],[1,1,10]),('B',[1,1,999],[1,1,1]),('arbitrary_scaled',[1,1,2],[1,1,198])]:
  yield {'p':p,'h':h,'edges':[[0,1],[1,2]],'family':name}
inputs=list(population());assert len(inputs)==16266;write('INPUTS.json',inputs)
write('START.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'planned':len(inputs),'timeout':60,'hashes':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [Path(__file__),P/'PROTOCOL01.md',P/'HYPOTHESIS01.md',P/'HYPOTHESIS02_UNIFORM_AND_PAIR.md',O/'INPUTS.json']}})
errors=[];roots=[];counts={'roots':0,'uniform_states_physical_credit':0,'surplus_credit_equal':0,'surplus_credit_different':0,'conservative_actions':0};fixture_tables={}
with gzip.open(O/'STATES.jsonl.gz','wt') as raw:
 for idx,inp in enumerate(inputs):
  if time.monotonic()>deadline:errors.append({'timeout_at':idx});break
  p=inp['p'];q=tuple(x+y for x,y in zip(p,inp['h']));n=len(q);full=(1<<n)-1;pred=[0]*n
  for i,j in inp['edges']:pred[j]|=1<<i
  def ready(d):return [i for i in range(n) if not d>>i&1 and pred[i]&d==pred[i]]
  @lru_cache(None)
  def value(d,k):
   if d==full:return top(q,k)
   candidates=[]
   for i in ready(d):
    s=d|(1<<i)
    candidates.append(value(s,k)-p[i])
    candidates.append(min(value(s,k),value(s,k+1)-q[i]))
   return max(candidates)
  for d in range(full+1):
   if any(d>>i&1 and pred[i]&d!=pred[i] for i in range(n)):continue
   dq=[q[i] for i in range(n) if d>>i&1]
   for k in range(n+2):
    v=value(d,k);c=top(dq,k)
    if inp['family']=='uniform':
     if k<=len(dq):
      counts['uniform_states_physical_credit']+=1
      if v!=c:errors.append({'uniform_failure':idx,'d':d,'k':k,'value':v,'formula':c})
     else:counts['surplus_credit_equal' if v==c else 'surplus_credit_different']+=1
    acts=[]
    for i in ready(d):
     s=d|(1<<i);f=value(s,k)-p[i];cc=min(value(s,k),value(s,k+1)-q[i]);conservative=min(c,top(dq+[q[i]],k)-p[i])
     counts['conservative_actions']+=2
     if conservative>f or c>cc:errors.append({'unsafe_conservative':idx,'d':d,'k':k,'i':i,'fresh_limit':conservative,'true_fresh':f,'true_cached':cc,'C':c})
     acts.append({'i':i,'fresh_threshold':f,'cached_threshold':cc,'conservative_fresh_threshold':conservative})
    raw.write(json.dumps({'index':idx,'D':d,'k':k,'V':v,'Top_completed':c,'actions':acts},separators=(',',':'))+'\n')
  if inp['family']!='uniform':
   if inp['family'] in ('A','B'):
    d,k,ell,i=1,1,2,1;v=value(d,k);f=value(d|(1<<i),k)-p[i]
    fixture_tables[inp['family']]={'p':p,'q':q,'D':d,'k':k,'ell':ell,'V':v,'fresh_threshold':f,'fresh_permitted':ell<=f,'conservative_permitted':ell+p[i]<=top([q[0],q[1]],k)}
   else:fixture_tables[inp['family']]={'V':value(3,1),'ell':4,'Top_completed':top(q[:2],1),'outside_viable':value(3,1)>=4>top(q[:2],1)}
  roots.append({'index':idx,'family':inp['family'],'states':value.cache_info().currsize,'status':'SUCCESS'});counts['roots']+=1
# Independent direct traces of full policies, including exact write totals.
traces=[]
for name in ('A','B'):
 p=fixture_tables[name]['p'];q=fixture_tables[name]['q'];h=[b-a for a,b in zip(p,q)]
 def rec(job,k,ell,hist):
  if job==3:
   traces.append({'fixture':name,'writes':k,'protected':ell,'cap':top(q,k),'trace':hist})
   if ell>top(q,k):errors.append({'full_policy_violation':traces[-1]})
   return
  mode='fresh' if name=='A' and k>0 else 'cached'
  if mode=='fresh':rec(job+1,k,ell+p[job],hist+[(mode,job)])
  else:
   rec(job+1,k,ell,hist+[(mode,job,'match')]);rec(job+1,k+1,ell+q[job],hist+[(mode,job,'mismatch')])
 rec(0,0,0,[])
if not (fixture_tables.get('A',{}).get('fresh_permitted') and not fixture_tables.get('B',{}).get('fresh_permitted',True) and fixture_tables.get('arbitrary_scaled',{}).get('outside_viable')):errors.append({'fixture_failure':fixture_tables})
write('ROOTS.json',roots);write('FIXTURES.json',fixture_tables);write('TRACES.json',traces);write('DISCREPANCIES.json',errors)
summary={'status':'SUCCESS' if not errors and counts['roots']==len(inputs) else 'FAILURE_OR_INCOMPLETE','counts':counts,'discrepancies':len(errors),'fixtures':fixture_tables,'full_policy_paths':len(traces),'seconds':time.monotonic()-start,'native_measurements':0,'benchmark_optimality_claim':False}
write('SUMMARY.json',summary);print(json.dumps(summary,indent=2))

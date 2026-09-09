from pathlib import Path
from itertools import permutations
import collections,datetime,hashlib,json,random,signal,sys,time,traceback
import order,verify
P=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 with p.open('x') as f:json.dump(x,f,separators=(',',':'));f.write('\n')
def legal_orders(c):
 n=len(c['works'])
 for pi in permutations(range(n)):
  at={x:i for i,x in enumerate(pi)}
  if all(at[u]<at[v] for u,v in c['edges']):yield list(pi)
def prepare():
 old=P.parent/'charged_resource_frontier_01/INPUTS.json';cases=[]
 for c in read(old)['cases']:cases.append(dict(id=c['id'],works=c['works'],edges=c['edges'],origin='observed-frontier-case'))
 assert len(cases)==5421;rng=random.Random(20260909)
 for n in [5,6,7]:
  for density in [0,.15,.4,.75]:
   for z in range(8):
    w=[rng.randint(1,9) for _ in range(n)];pi=list(range(n));rng.shuffle(pi)
    e=[[pi[i],pi[j]] for i in range(n) for j in range(i+1,n) if rng.random()<density]
    cases.append(dict(id='order-new-%03d'%(len(cases)-5421),works=w,edges=e,origin='new-authored-seeded',density=density))
 cases += [dict(id='empty-degenerate',works=[],edges=[],origin='degenerate-control-input'),dict(id='known-123-illustration',works=[1,2,3],edges=[],origin='already-reasoned-illustration')]
 for c in cases:c['orders']=list(legal_orders(c));assert c['orders']
 save(P/'INPUTS.json',dict(cases=cases,budgets=read(P/'PLAN.json')['budgets'],slacks=read(P/'PLAN.json')['slacks'],observed_source_sha256=sha(old)))
 control=[]
 def add(name,c,a,expected):control.append(dict(id=name,input=c,artifact=a,expected_accept=expected))
 c=dict(works=[1,2],edges=[]);a=order.construct(c)
 for name,patch in [('wrong-hash',dict(input_sha256='0'*64)),('duplicate-job',dict(order=[0,0])),('missing-job',dict(order=[0])),('boolean-job',dict(order=[False,1])),('nonminimum-ready',dict(order=[1,0]))]:add(name,c,dict(a,**patch),False)
 c=dict(works=[2,1],edges=[[0,1]]);a=order.construct(c);add('nonready',c,dict(a,order=[1,0]),False)
 c=dict(works=[2,2],edges=[]);a=order.construct(c);add('equal-work-tie',c,dict(a,order=[1,0]),True)
 save(P/'CONTROLS.json',control)
 files=['PLAN.json','INPUTS.json','CONTROLS.json','order.py','verify.py','study.py','THEORY.md']
 save(P/'MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cases=len(cases),old_cases=5421,new_authored_cases=96,other_cases=2,orders=sum(len(c['orders']) for c in cases),pairs=len(cases)*32,order_pairs=sum(len(c['orders']) for c in cases)*32,files={f:sha(P/f) for f in files},cap_seconds=180))
 print(read(P/'MANIFEST.json'))
def direct(works,pi,bs,rs):
 n=len(pi);D=[[[0]*(n+1) for b in range(max(bs)+1)] for r in range(max(rs)+1)]
 for r in range(max(rs)+1):
  for b in range(max(bs)+1):
   for i in range(n-1,-1,-1):
    w=works[pi[i]];v=D[r][b][i+1]
    if b:v=max(v,D[r-1][b-1][i] if r else w+D[0][b-1][i+1])
    D[r][b][i]=w+v
 return [D[r][b][0] for r in rs for b in bs]
def closed(works,pi,bs,rs):
 if not works:return [0]*(len(bs)*len(rs))
 omega=sum(works);big=max(works);prefix=[];m=0;suffix=[]
 for i,j in enumerate(pi):m=max(m,works[j]);prefix.append(m);suffix.append(sorted([works[t] for t in pi[i:]],reverse=True))
 values=[]
 for r in rs:
  for b in bs:
   if not r:x=sum(sorted(works,reverse=True)[:b])
   elif b<=r:x=b*big
   else:x=max((r-1)*prefix[i]+works[j]+sum(suffix[i][:b-r]) for i,j in enumerate(pi))
   values.append(omega+x)
 return values

def evaluate(out,cap=180):
 data=read(P/'INPUTS.json');manifest=read(P/'MANIFEST.json');assert all(sha(P/k)==v for k,v in manifest['files'].items());out.mkdir();start=time.monotonic();counts=collections.Counter();casecounts=collections.Counter();totals=[];expired=False
 def timeout(a,b):raise TimeoutError('campaign cap')
 signal.signal(signal.SIGALRM,timeout);signal.alarm(cap)
 with (out/'ORDERS.jsonl').open('x') as raw:
  for c in data['cases']:
   case=dict(works=c['works'],edges=c['edges']);unit=dict(id=c['id']);minimum=None;allmet=True;artifact=None;greedy=None;unit_statuses=set()
   if not expired:
    try:artifact=order.construct(case);verify.check(case,artifact);greedy=direct(c['works'],artifact['order'],data['budgets'],data['slacks'])
    except TimeoutError:expired=True;artifact=None;unit.update(status='TIMEOUT',error=traceback.format_exc());allmet=False;unit_statuses.add('TIMEOUT')
    except Exception:artifact=None;unit.update(status='INVALID',error=traceback.format_exc());allmet=False;unit_statuses.add('INVALID')
   for ix,pi in enumerate(c['orders']):
    row=dict(case=c['id'],order_index=ix,order=pi)
    if expired:row['status']='UNSTARTED';allmet=False
    elif artifact is None:row['status']='INVALID';allmet=False
    else:
     try:
      d=direct(c['works'],pi,data['budgets'],data['slacks']);f=closed(c['works'],pi,data['budgets'],data['slacks']);met=d==f and all(g<=v for g,v in zip(greedy,d));row.update(status='SUCCESS' if met else 'FAILURE',direct_W=d,closed_W=f,greedy_dominates=all(g<=v for g,v in zip(greedy,d)));allmet &=met;minimum=d[:] if minimum is None else [min(a,b) for a,b in zip(minimum,d)]
     except TimeoutError:expired=True;allmet=False;row.update(status='TIMEOUT',error=traceback.format_exc())
     except Exception:allmet=False;row.update(status='INVALID',error=traceback.format_exc())
    counts[row['status']]+=1;unit_statuses.add(row['status']);raw.write(json.dumps(row,separators=(',',':'))+'\n')
   status=next((s for s in ['TIMEOUT','INVALID','FAILURE','UNSTARTED'] if s in unit_statuses),'SUCCESS' if allmet and minimum==greedy else 'FAILURE');unit.update(status=status,artifact=artifact,minimum_W=minimum,greedy_W=greedy if artifact else None,orders=len(c['orders']));casecounts[status]+=1;totals.append(unit)
 signal.alarm(0);controls=[]
 for c in read(P/'CONTROLS.json'):
  try:verify.check(c['input'],c['artifact']);accepted=True
  except AssertionError:accepted=False
  controls.append(dict(id=c['id'],accepted=accepted,expected_accept=c['expected_accept'],met=accepted==c['expected_accept']))
 save(out/'CASES.json',totals);save(out/'CONTROLS.json',controls)
 result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if counts['SUCCESS']==manifest['orders'] and casecounts['SUCCESS']==manifest['cases'] and all(c['met'] for c in controls) else 'FAILURE',seconds=time.monotonic()-start,cases=manifest['cases'],orders=manifest['orders'],order_pairs=manifest['order_pairs'],case_pairs=manifest['pairs'],order_status={k:counts[k] for k in ['SUCCESS','FAILURE','TIMEOUT','INVALID','UNSTARTED']},case_status={k:casecounts[k] for k in ['SUCCESS','FAILURE','TIMEOUT','INVALID','UNSTARTED']},controls=controls,native_measurements=0,raw_sha256=sha(out/'ORDERS.jsonl'))
 save(out/'SUMMARY.json',result);print(json.dumps(result),flush=True)
 return result
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='execute':evaluate(P/'attempt01')
 else:raise SystemExit('prepare|execute')

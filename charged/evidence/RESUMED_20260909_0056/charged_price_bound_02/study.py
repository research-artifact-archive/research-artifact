from pathlib import Path
from collections import Counter
import json,hashlib,datetime,time,signal,traceback,sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'charged_compact_03'));import compact,verify

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 with p.open('x') as f:json.dump(x,f,separators=(',',':'));f.write('\n')
def direct(jobs,bmax):
 n=len(jobs);size=1<<n;d2=[[0]*size for _ in range(bmax+1)];d3=[[0]*size for _ in range(bmax+1)]
 prices=[]
 for w,p,g,v,r in jobs:
  m=min(v,g+r);d=g+r-m;prices.append((w+m,p+d,d,w+p))
 members=[[i for i in range(n) if mask>>i&1] for mask in range(size)]
 for b in range(1,bmax+1):
  now2,prev2,now3,prev3=d2[b],d2[b-1],d3[b],d3[b-1]
  for mask in range(1,size):
   x=y=None
   for i in members[mask]:
    c,q,d,s=prices[i];child=mask^(1<<i)
    xx=min(q+now2[child],max(now2[child],c+prev2[mask]))
    yy=min(q+now3[child],max(now3[child],c+prev3[mask]),d+max(now3[child],s+prev3[child]))
    x=xx if x is None else min(x,xx);y=yy if y is None else min(y,yy)
   now2[mask]=x;now3[mask]=y
 return [x[-1] for x in d2],[x[-1] for x in d3]

def unit(row):
 case=row['input'];jobs=case['jobs'];sat=row['saturation_bound'];A=sum(w+min(v,g+r) for w,p,g,v,r in jobs);premium=sum(p+max(0,g+r-v) for w,p,g,v,r in jobs)
 a3=compact.compile_case(case);check3=verify.check(a3,case)
 cp=dict(cp=[[w+min(v,g+r),p+max(0,g+r-v)] for w,p,g,v,r in jobs],edges=[])
 a2=compact.packing.pack(cp,compact.packing.order_if_compatible(cp));check2=verify.root_cap.check(a2)
 if a3['route']=='compatible_reduced':
  curve=verify.root_cap.Curve(a3['backend']['value_slopes']);at3=curve.value
 else:
  curve=a3['backend']['curves'][a3['backend']['full']];at3=lambda b:verify.general.value(curve,b)
 two,three=direct(jobs,sat);budgets=list(range(sat+1));errors=[]
 packed2=[compact.packing.value(a2,b) for b in budgets];packed3=[at3(b) for b in budgets]
 if two!=packed2 or three!=packed3:errors.append('direct/compiled disagreement')
 if two[-1]!=premium or three[-1]!=premium:errors.append('saturation disagreement')
 bad=[dict(budget=b,two=x,three=y) for b,x,y in zip(budgets,two,three) if not(0<=y<=x and (A+2*x-y)**2<=2*(A+y)**2)]
 if bad:errors.append('sharp bound counterexample')
 extra=[dict(budget=b,two=compact.packing.value(a2,b),three=at3(b)) for b in DATA['extra_budgets']]
 if any(x['two']!=premium or x['three']!=premium for x in extra):errors.append('constant-tail disagreement')
 save(OUT/(row['id']+'-two.json'),a2);save(OUT/(row['id']+'-three.json'),a3)
 return dict(id=row['id'],status='FAILURE' if errors else 'SUCCESS',baseline=A,premium=premium,saturation_bound=sat,two=two,three=three,packed_two=packed2,packed_three=packed3,extra=extra,errors=errors,counterexamples=bad,route=a3['route'],p_delta_positive_jobs=sum(p>0 and v<g+r for w,p,g,v,r in jobs),checked_two=check2,checked_three=check3)

M=json.loads((P/'MANIFEST.json').read_text())
for row in M['files']:
 f=P.parent.parent/row['path'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256'],row['path']
DATA=json.loads((P/'INPUTS.json').read_text());OUT=P/'attempt01';OUT.mkdir();save(OUT/'RUN_INPUT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(P/'MANIFEST.json'),python=sys.version,argv=sys.argv))
start=time.monotonic();deadline=start+900;counts=Counter();routes=Counter();rows=[]
def timeout(signum,frame):raise TimeoutError('campaign cap')
signal.signal(signal.SIGALRM,timeout);signal.alarm(900)
with (OUT/'RAW.jsonl').open('x') as raw:
 for index,row in enumerate(DATA['cases']):
  if time.monotonic()>=deadline:r=dict(id=row['id'],status='UNSTARTED',reason='campaign cap')
  else:
   try:r=unit(row)
   except TimeoutError as e:r=dict(id=row['id'],status='TIMEOUT',error=str(e));deadline=0
   except Exception as e:r=dict(id=row['id'],status='INVALID',error=repr(e),traceback=traceback.format_exc())
  raw.write(json.dumps(r,separators=(',',':'))+'\n');raw.flush();rows.append(r);counts[r['status']]+=1
  if 'route' in r:routes[r['route']]+=1
  if (index+1)%100==0:print(json.dumps(dict(recorded=index+1,total=len(DATA['cases']),counts=dict(counts))),flush=True)
signal.alarm(0)
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,bases=DATA['bases'],cases=len(rows),direct_roots=M['direct_roots'],extra_queries=M['extra_queries'],status_counts={k:counts[k] for k in ['SUCCESS','FAILURE','TIMEOUT','INVALID','UNSTARTED']},route_counts=dict(routes),raw_sha256=sha(OUT/'RAW.jsonl'),independent_application_population=False,proof_by_finite_tests=False)
save(OUT/'SUMMARY.json',summary);print(json.dumps(summary,indent=2));raise SystemExit(0 if counts['SUCCESS']==len(rows) else 1)

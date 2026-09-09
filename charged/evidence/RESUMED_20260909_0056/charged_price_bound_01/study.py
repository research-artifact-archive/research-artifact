from pathlib import Path
from collections import Counter
import json,time,datetime,hashlib,traceback,signal,sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'charged_compact_03'))
import compact,verify

def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def direct(jobs,bmax):
 n=len(jobs);size=1<<n
 # Two and three original-mode Bellman tables. No compiler/checker calls.
 d2=[[0]*size for _ in range(bmax+1)];d3=[[0]*size for _ in range(bmax+1)]
 members=[[i for i in range(n) if mask>>i&1] for mask in range(size)]
 for b in range(1,bmax+1):
  now2,prev2,now3,prev3=d2[b],d2[b-1],d3[b],d3[b-1]
  for mask in range(1,size):
   v2=v3=None
   for i in members[mask]:
    w,p,g,v,r=jobs[i];assert g==0 and v==r
    c=w+v;s=w+p;child=mask^(1<<i)
    a2=min(p+now2[child],max(now2[child],c+prev2[mask]))
    a3=min(p+now3[child],max(now3[child],c+prev3[mask]),max(now3[child],s+prev3[child]))
    v2=a2 if v2 is None else min(v2,a2);v3=a3 if v3 is None else min(v3,a3)
   now2[mask]=v2;now3[mask]=v3
 return [row[-1] for row in d2],[row[-1] for row in d3]

def compiled(case):
 a3=compact.compile_case(case);check3=verify.check(a3,case)
 cp=dict(cp=[[w+v,p] for w,p,g,v,r in case['jobs']],edges=[])
 a2=compact.packing.pack(cp,compact.packing.order_if_compatible(cp));check2=verify.root_cap.check(a2)
 return a2,a3,check2,check3

def check_unit(row,budgets,family=False):
 case=row['input'];jobs=case['jobs'];a,d=row['lam'];k=row['kappa']
 assert not case['edges'] and all(p*d==a*w and g==0 and v==r==k for w,p,g,v,r in jobs)
 A=sum(w+k for w,p,g,v,r in jobs)
 a2,a3,check2,check3=compiled(case)
 root3=verify.root_cap.Curve(a3['backend']['value_slopes'])
 packed2=[compact.packing.value(a2,b) for b in budgets];packed3=[root3.value(b) for b in budgets]
 if family:
  n=row['n'];m=row['M'];lam=a
  two=[min(n*lam,b*(m+1)) for b in budgets];three=[min(n*lam,b*(lam+1)) for b in budgets]
 else:two,three=direct(jobs,max(budgets))
 errors=[]
 if packed2!=two:errors.append('two-mode direct/closed-form disagreement')
 if packed3!=three:errors.append('three-mode direct/closed-form disagreement')
 bad=[]
 for b,x,y in zip(budgets,two,three):
  if not (0<=y<=x and (A+2*x-y)**2<=2*(A+y)**2):bad.append(dict(budget=b,two=x,three=y,baseline=A))
 if bad:errors.append('sharp bound violation')
 light=sum(p<k for w,p,g,v,r in jobs);heavy=len(jobs)-light
 result=dict(id=row['id'],kind=row['kind'],status='FAILURE' if errors else 'SUCCESS',baseline=A,budgets=budgets,two=two,three=three,packed_two=packed2,packed_three=packed3,errors=errors,bound_counterexamples=bad,light=light,heavy=heavy,checked_two=check2,checked_three=check3)
 if family:
  save(OUT/(row['id']+'-two.json'),a2);save(OUT/(row['id']+'-three.json'),a3)
 return result

manifest=json.loads((P/'MANIFEST.json').read_text())
for record in manifest['files']:
 f=P.parent/record['path'];assert f.stat().st_size==record['bytes'] and sha(f)==record['sha256'],record['path']
data=json.loads((P/'INPUTS.json').read_text());OUT=P/'attempt01';OUT.mkdir()
save(OUT/'RUN_INPUT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(P/'MANIFEST.json'),python=sys.version,argv=sys.argv,limit_seconds=900))
started=time.monotonic();deadline=started+900;counts=Counter();rows=[]
work=[(row,data['budgets'],False) for row in data['cases']]+[(row,row['budgets'],True) for row in data['family']]
def timed_out(signum,frame):raise TimeoutError('900-second campaign cap')
signal.signal(signal.SIGALRM,timed_out);signal.alarm(900)
with (OUT/'RAW.jsonl').open('x') as f:
 for index,(row,budgets,family) in enumerate(work):
  if time.monotonic()>=deadline:r=dict(id=row['id'],kind=row['kind'],status='UNSTARTED',reason='campaign cap')
  else:
   try:r=check_unit(row,budgets,family)
   except TimeoutError as e:r=dict(id=row['id'],kind=row['kind'],status='TIMEOUT',error=str(e));deadline=0
   except Exception as e:r=dict(id=row['id'],kind=row['kind'],status='INVALID',error=repr(e),traceback=traceback.format_exc())
  f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush();rows.append(r);counts[r['status']]+=1
  if (index+1)%1000==0:print(json.dumps(dict(recorded=index+1,total=len(work),counts=dict(counts))),flush=True)
signal.alarm(0)
best=None
for r in rows:
 if 'two' not in r:continue
 for b,x,y in zip(r['budgets'],r['two'],r['three']):
  num=r['baseline']+x;den=r['baseline']+y
  if best is None or num*best['denominator']>best['numerator']*den:best=dict(id=r['id'],budget=b,numerator=num,denominator=den)
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started,total_units=len(work),direct_cases=len(data['cases']),direct_roots=len(data['cases'])*len(data['budgets']),family_units=len(data['family']),family_queries=sum(len(r['budgets']) for r in data['family']),status_counts={x:counts[x] for x in ['SUCCESS','FAILURE','TIMEOUT','INVALID','UNSTARTED']},max_observed_total_ratio=best,raw_sha256=sha(OUT/'RAW.jsonl'),proof=False,application_population=False,new_timing_comparison=False)
save(OUT/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)
raise SystemExit(0 if counts['SUCCESS']==len(work) else 1)

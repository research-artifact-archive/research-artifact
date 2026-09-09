from pathlib import Path
from functools import lru_cache
from itertools import product
from collections import Counter
import json,time,datetime,hashlib,traceback,signal,sys
P=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 with p.open('x') as f:json.dump(x,f,separators=(',',':'));f.write('\n')
def prepare():
 plan=json.loads((P/'PLAN.json').read_text());cases=[]
 for n in plan['sizes']:
  potential=[(u,v) for v in range(n) for u in range(v)]
  for works in product(plan['weights'],repeat=n):
   for bits in range(1<<len(potential)):
    edges=[list(e) for j,e in enumerate(potential) if bits>>j&1]
    cases.append(dict(id='frontier-%05d'%len(cases),works=works,edges=edges))
 save(P/'INPUTS.json',dict(cases=cases,budgets=plan['budgets'],slacks=plan['call_slacks']))
 save(P/'MANIFEST.json',dict(created=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs=len(cases),roots=len(cases)*len(plan['budgets'])*len(plan['call_slacks']),files={str(p):sha(p) for p in [P/'PLAN.json',P/'INPUTS.json',Path(__file__)]},cap_seconds=300,environment=sys.version))
 print('fixed',len(cases),'inputs')
def solve(c,three):
 works=c['works'];n=len(works);pred=[sum(1<<u for u,v in c['edges'] if v==i) for i in range(n)]
 @lru_cache(None)
 def val(mask,b,r):
  if not mask or b==0:return 0
  options=[]
  for i in range(n):
   if not mask>>i&1 or pred[i]&mask:continue
   child=mask^(1<<i);options.append(works[i]+val(child,b,r))
   if r:options.append(max(val(child,b,r),val(mask,b-1,r-1)))
   if three:options.append(max(val(child,b,r),works[i]+val(child,b-1,r)))
  return min(options)
 return val

def execute():
 m=json.loads((P/'MANIFEST.json').read_text());assert all(sha(Path(p))==h for p,h in m['files'].items());data=json.loads((P/'INPUTS.json').read_text());out=P/'attempt01';out.mkdir();start=time.monotonic();counts=Counter();mismatches=0
 def timeout(a,b):raise TimeoutError('campaign300s')
 signal.signal(signal.SIGALRM,timeout);signal.alarm(300)
 with (out/'RAW.jsonl').open('x') as raw:
  for c in data['cases']:
   try:
    two=solve(c,False);three=solve(c,True);rows=[]
    for b in data['budgets']:
     for r in data['slacks']:
      x=two((1<<len(c['works']))-1,b,r);y=three((1<<len(c['works']))-1,b,r)
      a=sum(c['works']) if b>r else 0;z=sum(sorted(c['works'],reverse=True)[:min(max(b-r,0),len(c['works']))]);rows.append([b,r,x,y,a,z])
    bad=[v for v in rows if v[2]!=v[4] or v[3]!=v[5]];mismatches+=len(bad);row=dict(id=c['id'],status='FAILURE' if bad else 'SUCCESS',roots=rows,errors=bad)
   except TimeoutError:row=dict(id=c['id'],status='TIMEOUT',error=traceback.format_exc())
   except Exception:row=dict(id=c['id'],status='INVALID',error=traceback.format_exc())
   counts[row['status']]+=1;raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
   if sum(counts.values())%500==0:print(dict(recorded=sum(counts.values()),counts=dict(counts)),flush=True)
 signal.alarm(0);summary=dict(created=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-start,inputs=m['inputs'],roots=m['roots'],counts={x:counts[x] for x in ['SUCCESS','FAILURE','TIMEOUT','INVALID','UNSTARTED']},mismatching_roots=mismatches,raw_sha256=sha(out/'RAW.jsonl'),scope='finite original-macro minimax protected-work equations; no native or full-interface proof claim');save(out/'SUMMARY.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':
 {'prepare':prepare,'execute':execute}[sys.argv[1]]()

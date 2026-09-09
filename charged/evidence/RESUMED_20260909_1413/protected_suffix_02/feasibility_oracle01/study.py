from pathlib import Path
from functools import lru_cache
from collections import Counter
import time,json,hashlib,datetime
D=Path(__file__).resolve().parent

def evaluate(w):
 n=len(w);globaltop=[0]
 for v in sorted(w,reverse=True):globaltop.append(globaltop[-1]+v)
 def bound(h):return globaltop[min(h,n)]
 @lru_cache(None)
 def oracle(S,h,ell,fixed):
  if not S:return ell<=bound(h)
  ids=[i for i in range(n) if S>>i&1]
  for i in (ids[:1] if fixed else ids):
   T=S^(1<<i)
   if oracle(T,h,ell+w[i],fixed) or (oracle(T,h,ell,fixed) and oracle(T,h+1,ell+w[i],fixed)):return True
  return False
 for S in range(1<<n):
  ts=[0]
  for v in sorted([v for i,v in enumerate(w) if S>>i&1],reverse=True):ts.append(ts[-1]+v)
  for h in range(n+1):
   for ell in range(sum(w)+1):
    certificate=all(ell+x<=bound(h+t) for t,x in enumerate(ts));arbitrary=oracle(S,h,ell,False);fixed=oracle(S,h,ell,True)
    yield S,h,ell,certificate,arbitrary,fixed

def main():
 inp=json.loads((D/'INPUTS.json').read_text());start=time.monotonic();counts=Counter();truth=Counter();first=[];states=0
 with (D/'RESULTS.jsonl').open('x') as out:
  for c in inp['cases']:
   for S,h,ell,cert,a,f in evaluate(c['works']):
    states+=1;status='TIMEOUT' if time.monotonic()-start>180 else 'SUCCESS' if cert==a==f else 'FAILURE';counts[status]+=1;truth[str(cert)]+=1
    row=[c['id'],S,h,ell,cert,a,f,status];out.write(json.dumps(row,separators=(',',':'))+'\n')
    if status!='SUCCESS' and len(first)<10:first.append(row)
 r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if counts=={'SUCCESS':states} else 'NON_SUCCESS',cases=len(inp['cases']),states=states,comparisons=2*states,counts=dict(counts),feasible=dict(truth),first_adverse=first,seconds=time.monotonic()-start,input_sha256=hashlib.sha256((D/'INPUTS.json').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results_sha256=hashlib.sha256((D/'RESULTS.jsonl').read_bytes()).hexdigest())
 (D/'SUMMARY.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
if __name__=='__main__':main()

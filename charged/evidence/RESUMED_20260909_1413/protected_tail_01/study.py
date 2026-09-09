from pathlib import Path
from functools import lru_cache
from collections import Counter
import datetime,hashlib,json,time
D=Path(__file__).resolve().parent

def vectors(works,edges,B,r,tail):
 n=len(works);pred=[0]*n
 for u,v in edges:pred[v]|=1<<u
 prefix=[0]
 for w in sorted(works,reverse=True):prefix.append(prefix[-1]+w)
 @lru_cache(None)
 def omega(S):return sum(w for i,w in enumerate(works) if S>>i&1)
 def plus(a,b):return tuple(x+y for x,y in zip(a,b))
 @lru_cache(None)
 def f(S,b,t,h,ell):
  if not S:return (0,0,0)
  if not t and tail and ell+omega(S)<=prefix[min(h,n)]:return (omega(S),omega(S),S.bit_count())
  i=min((i for i in range(n) if S>>i&1 and not pred[i]&S),key=lambda i:(works[i],i));wi=works[i];T=S^(1<<i)
  branches=[plus((wi,0,1),f(T,b,t,h,ell))]
  if b:
   if t:branches.append(plus((wi,0,1),f(S,b-1,t-1,h,ell)))
   else:branches.append(plus((2*wi,wi,1),f(T,b-1,0,h+1,ell+wi)))
  return tuple(max(x[j] for x in branches) for j in range(3))
 return f((1<<n)-1,B,r,0,0)

def main():
 inp=json.loads((D/'INPUTS.json').read_text());start=time.monotonic();rows=[];counts=Counter();improved=Counter();first=[]
 for c in inp['cases']:
  w=c['works'];n=len(w);prefix=[0]
  for v in sorted(w,reverse=True):prefix.append(prefix[-1]+v)
  for b in inp['budgets']:
   for r in inp['slacks']:
    x={'case':c['id'],'B':b,'r':r}
    if time.monotonic()-start>240:x['status']='TIMEOUT'
    else:
     try:
      threshold=vectors(w,c['edges'],b,r,False);tail=vectors(w,c['edges'],b,r,True);expectedL=prefix[min(max(b-r,0),n)];expectedQ=n+min(b,r) if n else 0
      valid=threshold[1:]==tail[1:]==(expectedL,expectedQ) and tail[0]<=threshold[0] and (r!=0 or tail[0]==sum(w)+prefix[min(b,n)])
      x.update({'threshold':threshold,'tail':tail,'expected_L':expectedL,'expected_Q':expectedQ,'status':'SUCCESS' if valid else 'FAILURE'})
      if tail[0]<threshold[0]:improved[r]+=1
     except Exception as e:x.update({'status':'INVALID','error':repr(e)})
    counts[x['status']]+=1;rows.append(x)
    if x['status']!='SUCCESS' and len(first)<20:first.append({'input':c,'result':x})
 with (D/'RESULTS.jsonl').open('x') as f:
  for x in rows:f.write(json.dumps(x,separators=(',',':'))+'\n')
 summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'SUCCESS' if counts=={'SUCCESS':len(rows)} else 'NON_SUCCESS','cases':len(inp['cases']),'roots':len(rows),'counts':dict(counts),'strict_W_improvements_by_r':dict(improved),'seconds':time.monotonic()-start,'first_adverse':first,'input_sha256':hashlib.sha256((D/'INPUTS.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results_sha256':hashlib.sha256((D/'RESULTS.jsonl').read_bytes()).hexdigest(),'claim':'Fixed-input equation checks and weak worst-W dominance within a stated adaptive-tail modification, not general W optimum.'}
 (D/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
 print(json.dumps([x for x in rows if x['case']=='observed-author-counterexample-tail-24411' and x['r']==1]),flush=True)
if __name__=='__main__':main()

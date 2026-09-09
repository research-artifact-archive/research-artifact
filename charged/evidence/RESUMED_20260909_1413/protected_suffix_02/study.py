from pathlib import Path
from functools import lru_cache
from collections import Counter
import datetime,hashlib,json,time,importlib.util
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tail',D.parent/'protected_tail_01/study.py');tail=importlib.util.module_from_spec(spec);spec.loader.exec_module(tail)
def vectors(w,edges,B,r):
 n=len(w);pred=[0]*n
 for u,v in edges:pred[v]|=1<<u
 @lru_cache(None)
 def tops(S):
  out=[0]
  for x in sorted([x for i,x in enumerate(w) if S>>i&1],reverse=True):out.append(out[-1]+x)
  return out
 alltop=tops((1<<n)-1)
 @lru_cache(None)
 def valid(S,h,ell):return all(ell+x<=alltop[min(h+t,n)] for t,x in enumerate(tops(S)))
 def plus(a,b):return tuple(x+y for x,y in zip(a,b))
 @lru_cache(None)
 def f(S,b,t,h,ell):
  if not S:return(0,0,0)
  i=min((i for i in range(n) if S>>i&1 and not pred[i]&S),key=lambda i:(w[i],i));wi=w[i];T=S^(1<<i)
  if not t:
   assert valid(S,h,ell)
   if valid(T,h,ell+wi):return plus((wi,wi,1),f(T,b,0,h,ell+wi))
  choices=[plus((wi,0,1),f(T,b,t,h,ell))]
  if b:
   if t:choices.append(plus((wi,0,1),f(S,b-1,t-1,h,ell)))
   else:choices.append(plus((2*wi,wi,1),f(T,b-1,0,h+1,ell+wi)))
  return tuple(max(x[j] for x in choices) for j in range(3))
 return f((1<<n)-1,B,r,0,0)
def main():
 inp=json.loads((D/'INPUTS.json').read_text());start=time.monotonic();counts=Counter();comparisons=Counter();first={};roots=0
 with (D/'RESULTS.jsonl').open('x') as out:
  for c in inp['cases']:
   w=c['works'];n=len(w);prefix=[0]
   for x in sorted(w,reverse=True):prefix.append(prefix[-1]+x)
   for b in inp['budgets']:
    for r in inp['slacks']:
     row={'case':c['id'],'B':b,'r':r};roots+=1
     if time.monotonic()-start>240:row['status']='TIMEOUT'
     else:
      try:
       th=tail.vectors(w,c['edges'],b,r,False);tl=tail.vectors(w,c['edges'],b,r,True);cert=vectors(w,c['edges'],b,r);expect=(prefix[min(max(b-r,0),n)],n+min(b,r) if n else 0)
       ok=th[1:]==tl[1:]==cert[1:]==expect and cert[0]<=th[0]
       row.update(threshold=th,tail=tl,certificate=cert,status='SUCCESS' if ok else 'FAILURE')
       key='less_than_tail' if cert[0]<tl[0] else 'greater_than_tail' if cert[0]>tl[0] else 'equal_to_tail';comparisons[key]+=1
       if cert[0]<th[0]:comparisons['less_than_threshold']+=1
       if key not in first and key!='equal_to_tail':first[key]={'input':c,'result':row.copy()}
      except Exception as e:row.update(status='INVALID',error=repr(e))
     counts[row['status']]+=1
     if row['status']!='SUCCESS' and row['status'] not in first:first[row['status']]={'input':c,'result':row.copy()}
     out.write(json.dumps(row,separators=(',',':'))+'\n')
 summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if counts=={'SUCCESS':roots} else 'NON_SUCCESS',roots=roots,cases=len(inp['cases']),counts=dict(counts),comparisons=dict(comparisons),first=first,seconds=time.monotonic()-start,input_sha256=hashlib.sha256((D/'INPUTS.json').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results_sha256=hashlib.sha256((D/'RESULTS.jsonl').read_bytes()).hexdigest())
 (D/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()

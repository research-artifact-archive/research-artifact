from pathlib import Path
from itertools import product
from functools import lru_cache
import datetime,hashlib,json,time
D=Path(__file__).resolve().parent

def put(n,x):
 with(D/n).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def top(w,k):return sum(sorted(w,reverse=True)[:max(0,k)])
def populations():
 for n in range(1,5):
  tuples=list(product((1,3,7),repeat=n)) if n<4 else [(1,2,4,8),(8,1,2,4),(3,3,3,3),(1,1,10,10)]
  es=[(i,j) for i in range(n) for j in range(i+1,n)]
  for mask in range(1<<len(es)):
   edges=[e for bit,e in enumerate(es) if mask>>bit&1]
   for w in tuples:yield dict(w=w,edges=edges)

def oracle(w,edges):
 n=len(w);full=(1<<n)-1;pred=[0]*n
 for i,j in edges:pred[j]|=1<<i
 def ready(mask):return [i for i in range(n) if not mask>>i&1 and pred[i]&mask==pred[i]]
 G=[top(w,k) for k in range(2*n+3)]
 @lru_cache(None)
 def can(mask,k,ell):
  if time.monotonic()>deadline:raise TimeoutError('fixed300s cap')
  if mask==full:return ell<=G[min(k,len(G)-1)]
  for i in ready(mask):
   if can(mask|1<<i,k,ell+w[i]):return True
   if can(mask|1<<i,k,ell) and can(mask|1<<i,k+1,ell+w[i]):return True
  return False
 return can,ready,pred

if __name__=='__main__':
 start=time.monotonic();deadline=start+300;inputs=list(populations());assert len(inputs)==493;put('INPUTS01.json',inputs)
 put('START01.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned_roots=493,total_cap_seconds=300,hashes={n:sha(D/n) for n in ['check01.py','PROTOCOL01.md','INPUTS01.json','HYPOTHESIS01.md']}))
 roots=[];issues=[];states=0;actions=0;controls={'global_cap_only':0,'off_by_one':0};sf_count=0;sf_examples=[];halt=False
 with(D/'STATES01.jsonl').open('x') as stream:
  for idx,inp in enumerate(inputs):
   if halt:roots.append(dict(index=idx,status='NOT_EXECUTED',reason='prior timeout'));continue
   w=inp['w'];n=len(w);edges=inp['edges'];can,ready,pred=oracle(w,edges);rootstates=0;rootactions=0;rootissues=0
   try:
    for mask in range(1<<n):
     if any(mask>>i&1 and pred[i]&mask!=pred[i] for i in range(n)):continue
     done=[w[i] for i in range(n) if mask>>i&1];remain=[w[i] for i in range(n) if not mask>>i&1]
     for k in range(n+2):
      min_gap=min(top(w,k+m)-top(remain,m) for m in range(len(remain)+1));right=top(done,k)
      if min_gap!=right:issues.append(dict(index=idx,kind='IDENTITY',mask=mask,k=k,lhs=min_gap,rhs=right));rootissues+=1
      for ell in range(sum(done)+2):
       value=can(mask,k,ell);formula=ell<=right;local=[];bad=[]
       if value!=formula:bad.append('STATE')
       controls['global_cap_only']+=int((ell<=top(w,k))!=value);controls['off_by_one']+=int((ell<=top(done,k+1))!=value)
       for i in ready(mask):
        nxt=mask|1<<i;fresh=can(nxt,k,ell+w[i]);cached=can(nxt,k,ell) and can(nxt,k+1,ell+w[i]);ff=ell+w[i]<=top(done+[w[i]],k);cf=formula
        if fresh!=ff:bad.append('FRESH')
        if cached!=cf:bad.append('CACHED')
        sf=ell+w[i]<=top(w,k) and ell+sum(remain)<=top(w,k+1)
        if formula and fresh and not sf:
         sf_count+=1
         if len(sf_examples)<30:sf_examples.append(dict(index=idx,input=inp,mask=mask,k=k,ell=ell,target=i))
        local.append(dict(i=i,fresh=fresh,fresh_formula=ff,cached=cached,cached_formula=cf,previous_SF=sf));actions+=2;rootactions+=2
       row=dict(root=idx,mask=mask,k=k,ell=ell,safe=value,formula=formula,top_completed=right,identity_min_gap=min_gap,actions=local)
       stream.write(json.dumps(row,separators=(',',':'))+'\n');states+=1;rootstates+=1
       if bad:
        issues.append(dict(index=idx,kind='ACTION_OR_STATE',errors=bad,row=row));rootissues+=1
    roots.append(dict(index=idx,status='SUCCESS' if rootissues==0 else 'DISCREPANCY',states=rootstates,actions=rootactions,oracle_cache=list(can.cache_info()),discrepancies=rootissues))
   except Exception as exc:
    halt=isinstance(exc,TimeoutError);roots.append(dict(index=idx,status='TIMEOUT' if halt else 'FAILURE',error=repr(exc),states=rootstates,actions=rootactions));issues.append(dict(index=idx,kind='EXECUTION',error=repr(exc)))
   finally:can.cache_clear()
 witness=None
 if not halt:
  w=[100,1,2,80,80,80];es=[(i,i+1) for i in range(5)];can,ready,pred=oracle(w,es);mask=3;k=1;ell=1;i=2
  witness=dict(w=w,edges=es,completed_mask=mask,k=k,ell=ell,target=i,safe=can(mask,k,ell),fresh_viable=can(mask|1<<i,k,ell+w[i]),formula=ell+w[i]<=top([w[j] for j in range(6) if (mask|1<<i)>>j&1],k),old_SF=(ell+w[i]<=top(w,k) and ell+sum(w[j] for j in range(6) if not mask>>j&1)<=top(w,k+1)),old_second_lhs=ell+sum(w[j] for j in range(6) if not mask>>j&1),old_second_rhs=top(w,k+1),new_lhs=ell+w[i],new_rhs=top([100,1,2],k),scope='one declared residual decision; no worst-W improvement claim')
  can.cache_clear()
 put('ROOTS01.json',roots);put('DISCREPANCIES01.json',issues);put('CONTROL_COUNTS01.json',controls);put('STRICT_SF01.json',dict(decisions=sf_count,first_examples=sf_examples,examples_truncated=sf_count>len(sf_examples)));put('WITNESS01.json',witness)
 counts={k:sum(x['status']==k for x in roots) for k in sorted({x['status'] for x in roots})}
 ok=counts=={'SUCCESS':493} and not issues and all(controls.values()) and witness and witness['safe'] and witness['fresh_viable'] and witness['formula'] and not witness['old_SF']
 result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if ok else 'FAILURE',counts=counts,states=states,actions=actions,discrepancies=len(issues),controls=controls,strict_safe_decisions_beyond_SF=sf_count,seconds=time.monotonic()-start,native_measurements=0,independent_reproduction=False,representative_population=False,proof_by_finite_check=False,outputs={n:sha(D/n) for n in ['ROOTS01.json','STATES01.jsonl','DISCREPANCIES01.json','CONTROL_COUNTS01.json','STRICT_SF01.json','WITNESS01.json']})
 put('SUMMARY01.json',result);print(json.dumps(result,indent=2),flush=True);raise SystemExit(not ok)

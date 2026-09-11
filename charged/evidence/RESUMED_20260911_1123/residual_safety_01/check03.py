from pathlib import Path
from itertools import product
from functools import lru_cache
import datetime,gzip,hashlib,importlib.util,json,time
D=Path(__file__).resolve().parent;O=D/'check03';O.mkdir(exist_ok=False)
start=time.monotonic();DEADLINE=start+90
prev=D.parent.parent/'RESUMED_20260910_1617'
def getmodule(name,p):
 spec=importlib.util.spec_from_file_location(name,p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.DEADLINE=DEADLINE;return mod
old=prev/'joint_work_general_r_01/unknown02.py';U=getmodule('prior_interpreter',old)
oldcheck=prev/'safe_fresh_suffix_01/check01.py';C=getmodule('prior_checker',oldcheck)
def put(n,v):
 with (O/n).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def top(w,k):return sum(sorted(w,reverse=True)[:max(0,k)])
def population():
 for n in range(1,5):
  es=[(i,j) for i in range(n) for j in range(i+1,n)]
  for mask in range(1<<len(es)):
   edges=[e for j,e in enumerate(es) if mask>>j&1]
   for w in product((1,3,7),repeat=n):
    for r in range(3):yield dict(kind='exhaustive',w=w,edges=edges,r=r)
 yield dict(kind='previous_distinct6',w=[62,83,15,84,30,31],edges=[[1,2],[3,4],[4,5]],r=3)
 yield dict(kind='previous_observation4',w=[5,1,1,2],edges=[[0,1],[1,2]],r=1)
 yield dict(kind='previous_unsafe_chain',w=[1,1,10],edges=[[0,1],[1,2]],r=0)
 yield dict(kind='new_strict_permission_chain',w=[100,1,2,80,80,80],edges=[[0,1],[1,2],[2,3],[3,4],[4,5]],r=1)
def build(w,pred,r,kind):
 n=len(w)
 @lru_cache(None)
 def rec(S,f,k,ell):
  if time.monotonic()>DEADLINE:raise TimeoutError('fixed90s')
  if not S:return ('done',)
  ready=[i for i in range(n) if S>>i&1 and not pred[i]&S]
  small=min(ready,key=lambda i:(w[i],i));large=max(ready,key=lambda i:(w[i],-i))
  if f<r:i=small;mode='cheap'
  elif kind=='baseline':i=small;mode='cached'
  elif k==0:i=large;mode='cached'
  else:
   if kind=='SF':allow=ell+w[large]<=top(w,k) and ell+sum(w[i] for i in range(n) if S>>i&1)<=top(w,k+1)
   else:allow=ell+w[large]<=top([w[i] for i in range(n) if not S>>i&1]+[w[large]],k)
   if allow:i=large;mode='fresh'
   else:i=small;mode='cached'
  S1=S^(1<<i)
  if mode=='fresh':return (mode,i,rec(S1,f,k,ell+w[i]))
  good=rec(S1,f,k,ell)
  bad=rec(S,f+1,k,ell) if mode=='cheap' else rec(S1,f,k+1,ell+w[i])
  return (mode,i,good,bad)
 return rec((1<<n)-1,0,0,0)
inputs=list(population());assert len(inputs)==16267;put('INPUTS.json',inputs)
put('START.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned=len(inputs),timeout_seconds=90,hashes={str(p):sha(p) for p in [Path(__file__),D/'PROTOCOL03.md',O/'INPUTS.json',old,oldcheck]}))
results=[];discrepancies=[];paths=0;stop=False;relations={'F_better_only':0,'F_worse_only':0,'crossing':0,'equal':0};interesting=[]
with gzip.open(O/'PATHS.jsonl.gz','wt') as raw,gzip.open(O/'TREES.jsonl.gz','wt') as trees:
 for idx,inp in enumerate(inputs):
  row=dict(index=idx,input=inp)
  if stop:row.update(status='NOT_EXECUTED',reason='fixed timeout')
  else:
   try:
    w=inp['w'];r=inp['r'];pred=[0]*len(w)
    for i,j in inp['edges']:pred[j]|=1<<i
    got={}
    for kind in ('baseline','SF','F'):
     tree=build(w,pred,r,kind);one,rs=C.inspect(tree,w,pred,r);other=U.interpret(tree,w,pred,r)
     assert all(one[k]==other[k] for k in ('W','L','paths','maximum_Q'))
     assert not one['violations'] and one['L']==[top(w,B-r) for B in range(len(w)+r+1)]
     for x in rs:raw.write(json.dumps(dict(index=idx,policy=kind,**x),separators=(',',':'))+'\n')
     paths+=len(rs);got[kind]=one;trees.write(json.dumps(dict(index=idx,policy=kind,tree=tree),separators=(',',':'))+'\n')
    assert all(a<=b for kind in ('SF','F') for a,b in zip(got[kind]['W'],got['baseline']['W']))
    better=[B for B,(a,b) in enumerate(zip(got['F']['W'],got['SF']['W'])) if a<b]
    worse=[B for B,(a,b) in enumerate(zip(got['F']['W'],got['SF']['W'])) if a>b]
    relation='crossing' if better and worse else 'F_better_only' if better else 'F_worse_only' if worse else 'equal'
    relations[relation]+=1;row.update(status='SUCCESS',results=got,relation=relation,better_budgets=better,worse_budgets=worse)
    if better or worse:interesting.append(row)
   except Exception as e:
    row.update(status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',error=repr(e));discrepancies.append(row);stop=isinstance(e,TimeoutError)
  results.append(row)
put('ROWS.json',results);put('DISCREPANCIES.json',discrepancies);put('DIFFERENCES.json',interesting)
counts={k:sum(x['status']==k for x in results) for k in sorted({x['status'] for x in results})}
summary=dict(status='SUCCESS' if counts=={'SUCCESS':len(inputs)} else 'INCOMPLETE_OR_FAILURE',counts=counts,relations=relations,paths=paths,seconds=time.monotonic()-start,last_four=results[-4:],new_representative_population=False,native_measurements=0)
put('SUMMARY.json',summary);print(json.dumps(summary,indent=2))

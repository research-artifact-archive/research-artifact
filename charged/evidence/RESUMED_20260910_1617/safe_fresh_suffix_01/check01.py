from pathlib import Path
from itertools import product
import datetime,hashlib,importlib.util,json,time
D=Path(__file__).resolve().parent
def put(n,v):
 with (D/n).open('x') as f:f.write(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(w,k):return sum(sorted(w,reverse=True)[:max(0,k)])
def build(w,pred,r,kind,S=None,f=0,k=0,ell=0):
 if time.monotonic()>DEADLINE:raise TimeoutError('60s fixed cap')
 if S is None:S=(1<<len(w))-1
 if not S:return ('done',)
 ready=[i for i in range(len(w)) if S>>i&1 and not pred[i]&S]
 small=min(ready,key=lambda i:(w[i],i));large=max(ready,key=lambda i:(w[i],-i))
 if f<r:i=small;mode='cheap'
 elif kind=='baseline':i=small;mode='cached'
 elif k==0:i=large;mode='cached'
 elif ell+w[large]<=bounds(w,k) and (kind=='unsafe' or ell+sum(w[i] for i in range(len(w)) if S>>i&1)<=bounds(w,k+1)):i=large;mode='fresh'
 else:i=small;mode='cached'
 if mode=='fresh':return (mode,i,build(w,pred,r,kind,S^(1<<i),f,k,ell+w[i]))
 good=build(w,pred,r,kind,S^(1<<i),f,k,ell)
 bad=build(w,pred,r,kind,S,f+1,k,ell) if mode=='cheap' else build(w,pred,r,kind,S^(1<<i),f,k+1,ell+w[i])
 return (mode,i,good,bad)
def inspect(tree,w,pred,r):
 n=len(w);H=n+r;rows=[];bad=[]
 def walk(t,C,d,Q,W,L,trace):
  if time.monotonic()>DEADLINE:raise TimeoutError('60s fixed cap')
  if L>bounds(w,d-r):bad.append(dict(kind='PROTECTION',d=d,L=L,cap=bounds(w,d-r),trace=trace))
  if Q>H:bad.append(dict(kind='CALL_CAP',Q=Q,cap=H,trace=trace))
  if t[0]=='done':
   assert C==(1<<n)-1
   rows.append(dict(d=d,Q=Q,W=W,L=L,trace=trace));return
  mode,i=t[:2];assert not C>>i&1 and pred[i]&C==pred[i]
  for fail in ([False] if mode=='fresh' else [False,True]):
   complete=not(mode=='cheap' and fail);C1=C|(1<<i) if complete else C
   dw=w[i]*(2 if mode=='cached' and fail else 1);dl=w[i] if mode=='fresh' or mode=='cached' and fail else 0
   event=[mode,i,'bad' if fail else 'fresh' if mode=='fresh' else 'match']
   walk(t[3 if fail else 2],C1,d+int(fail),Q+1,W+dw,L+dl,trace+[event])
 walk(tree,0,0,0,0,0,[])
 return dict(W=[max(x['W'] for x in rows if x['d']<=B) for B in range(H+1)],L=[max(x['L'] for x in rows if x['d']<=B) for B in range(H+1)],paths=len(rows),maximum_Q=max(x['Q'] for x in rows),violations=bad),rows
def population():
 for n in range(1,4):
  es=[(i,j) for i in range(n) for j in range(i+1,n)]
  for mask in range(1<<len(es)):
   edges=[e for j,e in enumerate(es) if mask>>j&1]
   for w in product((1,2,4),repeat=n):
    for r in range(3):yield dict(kind='overlapping_small',w=w,edges=edges,r=r)
 yield dict(kind='previous_distinct_order',w=[62,83,15,84,30,31],edges=[[1,2],[3,4],[4,5]],r=3)
 yield dict(kind='previous_observation',w=[5,1,1,2],edges=[[0,1],[1,2]],r=1)
 yield dict(kind='deliberate_safety_control',w=[1,1,10],edges=[[0,1],[1,2]],r=0)
if __name__=='__main__':
 start=time.monotonic();DEADLINE=start+60
 old=D.parent/'joint_work_general_r_01/unknown02.py';spec=importlib.util.spec_from_file_location('U',old);U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U);U.DEADLINE=DEADLINE
 inputs=list(population());assert len(inputs)==714;put('INPUTS01.json',inputs)
 put('START01.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),hashes={p.name:sha(p) for p in [Path(__file__),D/'PROTOCOL01.md',D/'INPUTS01.json',old]},planned=714,total_cap_seconds=60))
 results=[];trees=[];paths=0;strict=[];stop=False
 with (D/'PATHS01.jsonl').open('x') as stream:
  for idx,inp in enumerate(inputs):
   row=dict(index=idx,input=inp)
   if stop:row.update(status='NOT_EXECUTED',reason='prior timeout')
   else:
    try:
     w=inp['w'];r=inp['r'];pred=[0]*len(w)
     for i,j in inp['edges']:pred[j]|=1<<i
     got={}
     for kind in ['baseline','safe']:
      tree=build(w,pred,r,kind);one,rs=inspect(tree,w,pred,r);other=U.interpret(tree,w,pred,r)
      assert all(one[k]==other[k] for k in ['W','L','paths','maximum_Q'])
      assert not one['violations'] and one['L']==[bounds(w,B-r) for B in range(len(w)+r+1)]
      for x in rs:stream.write(json.dumps(dict(index=idx,policy=kind,**x),separators=(',',':'))+'\n')
      paths+=len(rs);got[kind]=one;trees.append(dict(index=idx,policy=kind,tree=tree))
     assert all(a<=b for a,b in zip(got['safe']['W'],got['baseline']['W']))
     improved=[B for B,(a,b) in enumerate(zip(got['safe']['W'],got['baseline']['W'])) if a<b]
     if improved:strict.append(dict(index=idx,input=inp,budgets=improved,safe=got['safe']['W'],baseline=got['baseline']['W']))
     row.update(status='SUCCESS',results=got,strict_budgets=improved)
    except Exception as e:row.update(status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',error=repr(e));stop=isinstance(e,TimeoutError)
   results.append(row)
 control=None
 if not stop:
  inp=inputs[-1];w=inp['w'];pred=[0,1,2];tree=build(w,pred,0,'unsafe');control,rs=inspect(tree,w,pred,0);put('CONTROL_TREE01.json',tree);put('CONTROL_PATHS01.json',rs)
 put('ROWS01.json',results);put('TREES01.json',trees);put('CONTROL01.json',control);put('STRICT01.json',strict)
 counts={k:sum(x['status']==k for x in results) for k in sorted({x['status'] for x in results})}
 status='SUCCESS' if counts=={'SUCCESS':714} and control and control['violations'] else 'FAILURE'
 put('SUMMARY01.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,counts=counts,interpreted_paths=paths,strictly_improved_roots=len(strict),control_violations=len(control['violations']) if control else None,seconds=time.monotonic()-start,new_independent_population=False,unrestricted_general_optimality_claim=False,new_native_measurements=0,outputs={n:sha(D/n) for n in ['ROWS01.json','TREES01.json','PATHS01.jsonl','CONTROL01.json','CONTROL_TREE01.json','CONTROL_PATHS01.json','STRICT01.json'] if (D/n).exists()}))
 print(json.dumps(dict(status=status,counts=counts,paths=paths,strict_roots=len(strict),last_three=results[-3:],control=control),indent=2));raise SystemExit(status!='SUCCESS')

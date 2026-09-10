from pathlib import Path
from functools import lru_cache
import datetime,hashlib,importlib.util,json,time
D=Path(__file__).resolve().parent;start=time.monotonic();deadline=start+55
spec=importlib.util.spec_from_file_location('u',D/'unknown02.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u);u.DEADLINE=deadline
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounded():
 if time.monotonic()>deadline:raise TimeoutError('55s internal bound')
@lru_cache(None)
def trees(i,n,r):
 if i==n:return (('done',),)
 results=[]
 for t in trees(i+1,n,r):results.extend([('fresh',i,t),('cached',i,t)])
 if r:
  for t0 in trees(i+1,n,r):
   for t1 in trees(i,n,r-1):results.append(('cheap',i,t0,t1))
 return tuple(results)
def interpret(t,w,r):
 n=len(w);H=n+r;Ws=[-1]*(H+1);Ls=[-1]*(H+1);Qs=[-1]*(H+1);paths=0;bad=None
 def visit(t,i,d,q,W,L,trace):
  nonlocal paths,bad
  bounded();mode=t[0]
  if mode=='done':
   assert i==n and q<=H;paths+=1
   if L>u.top(w,d-r) and bad is None:bad=dict(d=d,q=q,W=W,L=L,cap=u.top(w,d-r),trace=trace)
   for B in range(d,H+1):Ws[B]=max(Ws[B],W);Ls[B]=max(Ls[B],L);Qs[B]=max(Qs[B],q)
   return
  assert t[1]==i;v=w[i]
  if mode=='fresh':visit(t[2],i+1,d,q+1,W+v,L+v,trace+[(i,mode,'done')])
  else:
   visit(t[2],i+1,d,q+1,W+v,L,trace+[(i,mode,'match')])
   if mode=='cheap':visit(t[3],i,d+1,q+1,W+v,L,trace+[(i,mode,'failure')])
   else:visit(t[2],i+1,d+1,q+1,W+2*v,L+v,trace+[(i,mode,'mismatch')])
 visit(t,0,0,0,0,0,[])
 return dict(W=Ws,L=Ls,Q=Qs,paths=paths,first_violation=bad)
def candidate():
 def build(i,f,first,heavybad,lightbad):
  if i==4:return ('done',)
  if i==3 and first==1 and heavybad and lightbad:return ('fresh',i,build(i+1,f,first,heavybad,lightbad))
  if not f:return ('cheap',i,build(i+1,f,first,heavybad,lightbad),build(i,1,i,False,False))
  return ('cached',i,build(i+1,f,first,False if i==1 else heavybad,False if i==2 else lightbad),build(i+1,f,first,True if i==1 else heavybad,True if i==2 else lightbad))
 return build(0,0,None,False,False)
inputs=[dict(w=w,r=r) for w in [(2,4,1,1),(1,1,2,4)] for r in (0,1)]
assert not(D/'ERASED_POLICY_ROWS12.jsonl').exists()
(D/'ERASED_START12.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protocol_sha256=sha(D/'ERASED_PROTOCOL12.md'),code_sha256=sha(Path(__file__)),oracle_sha256=sha(D/'unknown02.py'),roots=inputs,planned_policy_trees=8672,cap_seconds=60),indent=2)+'\n')
roots=[];total=paths=admitted=0
with(D/'ERASED_POLICY_ROWS12.jsonl').open('x') as out:
 for rid,inp in enumerate(inputs):
  row=dict(input=inp);w=inp['w'];r=inp['r'];n=len(w);pred=[0,1,2,4]
  try:
   ts=trees(0,n,r);assert len(ts)==(16 if r==0 else 4320);valid=[]
   for j,t in enumerate(ts):
    got=interpret(t,w,r);total+=1;paths+=got['paths'];status='ADMISSIBLE' if got['first_violation'] is None else 'INADMISSIBLE_PROTECTION'
    if status=='ADMISSIBLE':valid.append((got['W'],t));admitted+=1
    out.write(json.dumps(dict(root=rid,index=j,status=status,tree=t,result=got),separators=(',',':'))+'\n')
   frontier=[]
   for c,t in valid:
    if any(all(x<=y for x,y in zip(old[0],c)) for old in frontier):continue
    frontier=[old for old in frontier if not all(x<=y for x,y in zip(c,old[0]))];frontier.append((c,t))
   assert valid and frontier
   g=u.Universal(w,pred,r);vf=g.solve(15,r,0,0);vc=[]
   for c,t in vf:
    got=u.interpret(t,w,pred,r);assert got['W']==[sum(w)+x for x in c];vc.append(dict(curve=got['W'],tree=t,interpretation=got))
   if w==(2,4,1,1) and r==1:
    assert min(x[0][4] for x in frontier)==18 and min(x['curve'][4] for x in vc)==17
    ct=candidate();cg=u.interpret(ct,w,pred,r);assert cg['W'][4]==17 and cg['L']==[u.top(w,B-r) for B in range(n+r+1)];row['proposed_visible_policy']=dict(tree=ct,interpretation=cg)
   row.update(status='SUCCESS',population=len(ts),admissible=len(valid),rejected_protection=len(ts)-len(valid),erased_frontier=[dict(curve=c,tree=t) for c,t in frontier],visible_frontier=vc)
  except Exception as e:row.update(status='FAILURE',error=repr(e))
  roots.append(row)
(D/'ERASED_ROOT_ROWS12.json').write_text(json.dumps(roots,indent=2)+'\n')
ok=total==8672 and all(x['status']=='SUCCESS' for x in roots)
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if ok else 'FAILURE',roots=len(roots),policy_trees=total,admissible_policy_trees=admitted,rejected_protection=total-admitted,interpreted_paths=paths,seconds=time.monotonic()-start,hashes={f:sha(D/f) for f in ['ERASED_POLICY_ROWS12.jsonl','ERASED_ROOT_ROWS12.json']})
(D/'ERASED_SUMMARY12.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));raise SystemExit(not ok)

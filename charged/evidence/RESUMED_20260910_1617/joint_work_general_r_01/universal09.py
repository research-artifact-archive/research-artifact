from pathlib import Path
from itertools import combinations_with_replacement
from collections import Counter
import datetime,hashlib,gzip,io,importlib.util,json,time
D=Path(__file__).resolve().parent;START=time.monotonic();LIMIT=START+590
spec=importlib.util.spec_from_file_location('universal02',D/'unknown02.py');U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U);U.DEADLINE=LIMIT
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def formula(w,r):
 a=sorted(w);n=len(w);top=[0]
 for v in reversed(a):top.append(top[-1]+v)
 return [sum(a)+B*a[-1] if B<=r else sum(a)+max(r*a[n-m]+top[m] for m in range(1,min(B-r,n)+1)) for B in range(n+r+1)]
def paths(w,r,cid,out):
 n=len(w);H=n+r;Wmax=[-1]*(H+1);Lmax=[-1]*(H+1);Qmax=[-1]*(H+1);witness=[None]*(H+1);count=0
 def visit(i,f,d,Q,W,L,trace):
  nonlocal count
  if time.monotonic()>LIMIT:raise TimeoutError('590s internal cap')
  if i==n:
   assert Q<=H;count+=1;row=dict(case=cid,d=d,Q=Q,W=W,L=L,trace=trace);out.write(json.dumps(row,separators=(',',':'))+'\n')
   for B in range(d,H+1):
    if W>Wmax[B]:Wmax[B]=W;witness[B]=row
    Lmax[B]=max(Lmax[B],L);Qmax[B]=max(Qmax[B],Q)
   return
  mode='cheap' if f<r else 'cached';v=w[i];paid=W+v
  visit(i+1,f,d,Q+1,paid,L,trace+[(i,mode,'match')])
  if mode=='cheap':visit(i,f+1,d+1,Q+1,paid,L,trace+[(i,mode,'failure')])
  else:visit(i+1,f,d+1,Q+1,paid+v,L+v,trace+[(i,mode,'mismatch')])
 visit(0,0,0,0,0,0,[])
 return dict(W=Wmax,L=Lmax,Q=Qmax,paths=count,W_witnesses=witness)
def main():
 assert not(D/'UNIVERSAL_ROWS09.jsonl').exists()
 inputs=[dict(w=w,r=r,scope='n1to4') for n in range(1,5) for w in combinations_with_replacement((1,2,4,7,11),n) for r in range(4)]
 inputs += [dict(w=w,r=r,scope='n5') for w in combinations_with_replacement((1,3,9),5) for r in range(3)]
 inputs += [dict(w=w,r=r,scope='n6') for w in combinations_with_replacement((1,2,4),6) for r in range(3)]
 assert len(inputs)==647
 (D/'UNIVERSAL_INPUTS09.json').write_text(json.dumps(inputs)+'\n')
 receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned=647,cap_seconds=600,hashes={f:sha(D/f) for f in ['UNIVERSAL_PROTOCOL09.md','UNIVERSAL_INDEPENDENT_DRAFT09.md','UNIVERSAL_INPUTS09.json','universal09.py','unknown02.py','UNKNOWN_ROWS02.jsonl']})
 (D/'UNIVERSAL_START09.json').write_text(json.dumps(receipt,indent=2)+'\n')
 retrospective=[];r0=[]
 for line in(D/'UNKNOWN_ROWS02.jsonl').open():
  row=json.loads(line);inp=row['input'];w=inp['w'];r=inp['r'];expected=formula(w,r);found=[x['curve'] for x in row['frontier']]
  if not inp['edges']:retrospective.append(dict(index=row['index'],input=inp,expected=expected,found=found,status='SUCCESS' if found==[expected] else 'FAILURE'))
  if r==0:r0.append(dict(index=row['index'],input=inp,expected=expected,found=found,status='SUCCESS' if found==[expected] else 'FAILURE'))
 assert len(retrospective)==117 and len(r0)==237
 (D/'UNIVERSAL_RETROSPECTIVE09.json').write_text(json.dumps(dict(independent=retrospective,r0_DAG=r0,overlap=39),indent=2)+'\n')
 stats=Counter();failed=[];totalpaths=states=0
 raw=(D/'UNIVERSAL_PATHS09.jsonl.gz').open('xb');z=gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0);out=io.TextIOWrapper(z,encoding='utf-8',newline='\n')
 with(D/'UNIVERSAL_ROWS09.jsonl').open('x') as rows:
  for idx,inp in enumerate(inputs):
   row=dict(index=idx,input=inp)
   try:
    if time.monotonic()>LIMIT:row.update(status='NOT_EXECUTED')
    else:
     w=inp['w'];r=inp['r'];n=len(w);game=U.Universal(w,[0]*n,r);front=game.solve((1<<n)-1,r,0,0);states+=game.visits
     assert front,('empty',inp);curves=[[sum(w)+v for v in c] for c,t in front];expected=formula(w,r);got=paths(w,r,idx,out);totalpaths+=got['paths'];Lexpected=[U.top(w,B-r) for B in range(n+r+1)]
     row.update(formula=expected,oracle_curves=curves,policy=got,Lexpected=Lexpected)
     assert got['W']==expected and got['L']==Lexpected and max(got['Q'])<=n+r,('policy',row)
     assert expected in curves and all(all(a<=b for a,b in zip(expected,c)) for c in curves),('oracle_domination',row)
     row.update(status='SUCCESS',oracle_front_width=len(front))
   except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
   except Exception as e:row.update(status='FAILURE',error=repr(e));failed.append(row.copy())
   stats[row['status']]+=1;rows.write(json.dumps(row,separators=(',',':'))+'\n');rows.flush()
 out.close();raw.close()
 (D/'UNIVERSAL_ERRORS09.json').write_text(json.dumps(failed,indent=2)+'\n')
 good=stats=={'SUCCESS':647} and all(x['status']=='SUCCESS' for x in retrospective+r0)
 summary=dict(receipt,status='SUCCESS' if good else 'FAILURE',counts=dict(stats),retrospective_independent_cases=117,r0_DAG_cases=237,retrospective_overlap=39,retrospective_statuses=dict(Counter(x['status'] for x in retrospective)),r0_statuses=dict(Counter(x['status'] for x in r0)),policy_paths=totalpaths,oracle_states=states,seconds=time.monotonic()-START,outputs={f:sha(D/f) for f in ['UNIVERSAL_ROWS09.jsonl','UNIVERSAL_RETROSPECTIVE09.json','UNIVERSAL_PATHS09.jsonl.gz','UNIVERSAL_ERRORS09.json']})
 (D/'UNIVERSAL_SUMMARY09.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return good
if __name__=='__main__':raise SystemExit(not main())

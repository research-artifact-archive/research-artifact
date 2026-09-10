from pathlib import Path
from itertools import product
import datetime,hashlib,importlib.util,json,time
D=Path(__file__).resolve().parent;start=time.monotonic()
spec=importlib.util.spec_from_file_location('u',D/'unknown02.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u);u.DEADLINE=start+55
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def expected(w,r):
 a=sorted(w);n=len(a);return [sum(a)+B*a[-1] if B<=r else sum(a)+max(r*a[-m]+sum(a[-m:]) for m in range(1,min(B-r,n)+1)) for B in range(n+r+1)]
inputs=[dict(w=w,r=r,shape=shape) for w,r,shape in product([(10,1,1),(1,10,1),(1,1,10),(10,1),(1,10),(10,2,1,1)],range(3),['independent','chain'])]
assert len(inputs)==36 and not(D/'SCOPE_ROWS11.jsonl').exists()
(D/'SCOPE_START11.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned=36,cap_seconds=60,protocol=sha(D/'UNIVERSAL_SCOPE_PROTOCOL11.md'),source=sha(Path(__file__)),oracle=sha(D/'unknown02.py'),inputs=inputs),indent=2)+'\n')
rows=[]
with(D/'SCOPE_ROWS11.jsonl').open('x') as out:
 for inp in inputs:
  row=dict(input=inp)
  try:
   u.bounded();w=inp['w'];r=inp['r'];n=len(w);pred=[0]*n
   if inp['shape']=='chain':
    for i in range(1,n):pred[i]=1<<(i-1)
   game=u.Universal(w,pred,r);front=game.solve((1<<n)-1,r,0,0);assert front
   checks=[]
   for c,t in front:
    got=u.interpret(t,w,pred,r);curve=[sum(w)+e for e in c]
    assert got['W']==curve and got['L']==[u.top(w,B-r) for B in range(n+r+1)]
    assert curve[:r+2]==[sum(w)+B*max(w) for B in range(r+2)]
    checks.append(dict(curve=curve,tree=t,interpretation=got))
   ind=expected(w,r)
   if inp['shape']=='independent' or r==0:assert [c['curve'] for c in checks]==[ind]
   if w==(10,1,1) and r==1 and inp['shape']=='chain':assert min(c['curve'][3] for c in checks)==33 and ind[3]==32
   row.update(status='SUCCESS',states=game.visits,independent_formula=ind,frontier=checks)
  except Exception as e:row.update(status='FAILURE',error=repr(e))
  rows.append(row);out.write(json.dumps(row,separators=(',',':'))+'\n');out.flush()
counts={s:sum(x['status']==s for x in rows) for s in sorted(set(x['status'] for x in rows))}
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if counts=={'SUCCESS':36} else 'FAILURE',counts=counts,seconds=time.monotonic()-start,rows_sha256=sha(D/'SCOPE_ROWS11.jsonl'),root_frontier_widths=sorted(set(len(x.get('frontier',[])) for x in rows)))
(D/'SCOPE_SUMMARY11.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));raise SystemExit(summary['status']!='SUCCESS')

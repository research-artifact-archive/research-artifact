from pathlib import Path
from datetime import datetime,timezone
import importlib.util,gzip,json,time,hashlib
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard01',D/'check01.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def greedy(w,g,T):
 k=mask=saved=0
 for i in sorted(range(len(w)),key=lambda i:(-w[i],i)):
  if (k+1)*g+w[i]<=T:k+=1;mask|=1<<i;saved+=w[i]
 return saved,mask

def main():
 start=time.monotonic();fixed=json.loads((D/'GREEDY_FIX_RECEIPT02.json').read_text())
 for r in fixed['files']:assert m.sha(D/r['path'])==r['sha256'],r['path']
 O=D/'greedy02';O.mkdir();I=json.loads((D/'INPUTS01.json').read_text());inputs={x['id']:x for x in I['uniform']}
 expected={}
 with gzip.open(D/'run01/ROWS.jsonl.gz','rt') as f:
  for line in f:
   x=json.loads(line)
   if x['id'] in inputs:expected[x['id']]=tuple(map(tuple,x['frontier']))
 fail=[];count={'inputs':0,'thresholds':0,'cap_queries':0}
 with m.open_gz(O/'ROWS.jsonl.gz') as rows,m.open_gz(O/'CAPS.jsonl.gz') as caprows:
  for id,x in inputs.items():
   w,g=x['w'],x['guard'];G=len(w)*g;thresholds=sorted({G}|{v+j*g for v in w for j in range(1,len(w)+1) if v+j*g>G});points=[];tr=[]
   for T in thresholds:
    saved,mask=greedy(w,g,T);dp,dm=m.profit_count(w,g,T);point,K=m.subset_point(w,[g]*len(w),mask)
    if saved!=dp or K>T or saved!=sum(v for i,v in enumerate(w) if mask>>i&1):fail.append(dict(id=id,T=T,saved=saved,dp=dp,mask=mask,K=K))
    points.append(point);tr.append(dict(T=T,saved=saved,mask=mask,K=K,point=point));count['thresholds']+=1
   front=m.prune(points)
   if front!=expected[id]:fail.append(dict(id=id,actual=front,expected=expected[id]))
   m.emit(rows,dict(id=id,frontier=front,thresholds=tr));count['inputs']+=1
  with gzip.open(D/'run01/CAPS.jsonl.gz','rt') as f:
   for line in f:
    row=json.loads(line);id=row[0]
    if id not in inputs:continue
    _,KW,KP,exp,*_=row;x=inputs[id];w,g=x['w'],x['guard'];G=g*len(w);M=KW-sum(w);T=min(M,KP);saved,mask=greedy(w,g,T);actual=G<=M and G<=KP and saved>=G+sum(w)-KP
    if actual!=exp:fail.append(dict(id=id,caps=[KW,KP],actual=actual,expected=exp,mask=mask))
    if actual and not all(a<=b for a,b in zip(m.subset_point(w,[g]*len(w),mask)[0],[KW,KP])):fail.append(dict(id=id,kind='infeasible_witness',mask=mask,caps=[KW,KP]))
    m.emit(caprows,[id,KW,KP,exp,actual,mask]);count['cap_queries']+=1
 allthreshold=[0,1];correct=m.prune(m.subset_point([1],[0],greedy([1],0,T)[1])[0] for T in allthreshold);bad=m.prune(m.subset_point([1],[0],greedy([1],0,T)[1])[0] for T in [1]);control=dict(id='omit_baseline_threshold',correct=correct,altered=bad,detected=correct==((1,1),) and bad==((2,1),),prior01_had_baseline=True);m.put(O/'CONTROL.json',control)
 r=dict(utc=datetime.now(timezone.utc).isoformat(),status='SUCCESS' if not fail and control['detected'] and count['inputs']==836 and count['cap_queries']==43565 else 'FAILED',counts=count,failures=fail,seconds=time.monotonic()-start,files=[dict(path=p.name,bytes=p.stat().st_size,sha256=m.sha(p)) for p in sorted(O.glob('*.gz'))]);m.put(O/'RESULT.json',r);print(json.dumps(r),flush=True);return int(r['status']!='SUCCESS')
if __name__=='__main__':raise SystemExit(main())

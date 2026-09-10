from pathlib import Path
import collections,datetime,gzip,hashlib,importlib.util,io,itertools,json,time
D=Path(__file__).resolve().parent;START=time.monotonic();LIMIT=START+175
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def imported(name,file):
 spec=importlib.util.spec_from_file_location(name,D/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
F=imported('formula05','independent05.py')
def interpret(w,B,r,k,case,out):
 count=0;maximum=[-1,-1,-1];witness=[None,None,None]
 def walk(i,s,f,d,Q,W,L,trace):
  nonlocal count
  if time.monotonic()>LIMIT:raise TimeoutError('175s internal cap')
  if i==len(w):
   assert Q<=len(w)+r;count+=1;row={'case':case,'k':k,'d':d,'Q':Q,'W':W,'L':L,'trace':trace};out.write(json.dumps(row,separators=(',',':'))+'\n')
   for j,v in enumerate((W,L,Q)):
    if v>maximum[j]:maximum[j]=v;witness[j]=row
   return
  v=w[i]
  # Selector: no B or d branch. The interpreter's mismatch branching is the adversary.
  if k==0 or s==k:walk(i+1,s,f,d,Q+1,W+v,L+v,trace+[(i,'fresh','complete')]);return
  mode='cheap' if f<r else 'cached';prepared=W+v
  walk(i+1,s+1,f,d,Q+1,prepared,L,trace+[(i,mode,'match')])
  if d<B:
   if mode=='cheap':walk(i,s,f+1,d+1,Q+1,prepared,L,trace+[(i,mode,'failure')])
   else:walk(i+1,s,f,d+1,Q+1,prepared+v,L+v,trace+[(i,mode,'mismatch')])
 walk(0,0,0,0,0,0,0,[])
 return dict(W=maximum[0],L=maximum[1],Q=maximum[2],paths=count,W_witness=witness[0],L_witness=witness[1],Q_witness=witness[2])
def main():
 assert not(D/'SIMPLIFIED_ROWS08.jsonl').exists()
 inputs=json.loads((D/'INDEPENDENT_INPUTS06.json').read_text());assert len(inputs)==13850
 references=[json.loads(line) for line in (D/'INDEPENDENT_ROWS06.jsonl').open()];assert len(references)==len(inputs)
 starts={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hashes':{f:sha(D/f) for f in ['SIMPLIFIED_PROTOCOL08.md','simplified08.py','independent05.py','INDEPENDENT_INPUTS06.json','INDEPENDENT_ROWS06.jsonl']},'cap_seconds':180}
 (D/'SIMPLIFIED_START08.json').write_text(json.dumps(starts,indent=2)+'\n')
 counts=collections.Counter();boundcounts=collections.Counter();fails=[];paths=0;bpaths=0
 raw=(D/'SIMPLIFIED_PATHS08.jsonl.gz').open('xb');compressed=gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0);out=io.TextIOWrapper(compressed,encoding='utf-8',newline='\n')
 with (D/'SIMPLIFIED_ROWS08.jsonl').open('x') as rows:
  for idx,inp in enumerate(inputs):
   row={'index':idx,'input':inp}
   try:
    w=inp['w'];B=inp['B'];r=inp['r'];candidates,front=F.formula(w,B,r);actual=[];policies=[]
    for k,expect in enumerate(candidates):
     got=interpret(w,B,r,k,idx,out);paths+=got['paths'];actual.append([got['W'],got['L']]);policies.append({'k':k,'expected':expect,'actual':got})
     assert [got['W'],got['L']]==expect,('exact',k,expect,got)
     assert got['Q']<=len(w)+min(r,B)
    observed=F.nd(actual);assert observed==front==references[idx]['oracle']
    row.update(status='SUCCESS',frontier=observed,policies=policies)
   except TimeoutError as e:row.update(status='TIMEOUT',error=str(e));fails.append(row.copy())
   except Exception as e:row.update(status='FAILURE',error=repr(e));fails.append(row.copy())
   counts[row['status']]+=1;rows.write(json.dumps(row,separators=(',',':'))+'\n')
 with (D/'SIMPLIFIED_BOUNDARIES08.jsonl').open('x') as rows:
  idx=0
  for n in range(1,7):
   for w in itertools.combinations_with_replacement((1,2,4,7,11),n):
    for r in range(4):
     for k in range(1,n+1):
      B=r+n-k+1;row={'index':idx,'input':{'w':w,'r':r,'B':B,'k':k}}
      try:
       got=interpret(w,B,r,k,'boundary'+str(idx),out);bpaths+=got['paths'];limit=sum(w[k:]);assert got['L']>limit and got['Q']<=n+r
       row.update(status='SUCCESS',constant_L_bound=limit,actual=got)
      except TimeoutError as e:row.update(status='TIMEOUT',error=str(e));fails.append(row.copy())
      except Exception as e:row.update(status='FAILURE',error=repr(e));fails.append(row.copy())
      boundcounts[row['status']]+=1;rows.write(json.dumps(row,separators=(',',':'))+'\n');idx+=1
 outside=interpret((1,),2,2,1,'outside_promise_n1',out);assert outside['Q']==3
 out.close();raw.close()
 (D/'SIMPLIFIED_ERRORS08.json').write_text(json.dumps(fails,indent=2)+'\n')
 files=['SIMPLIFIED_ROWS08.jsonl','SIMPLIFIED_BOUNDARIES08.jsonl','SIMPLIFIED_PATHS08.jsonl.gz','SIMPLIFIED_ERRORS08.json']
 ok=counts=={'SUCCESS':13850} and set(boundcounts)=={'SUCCESS'} and not fails
 summary=dict(starts,status='SUCCESS' if ok else 'FAILURE',counts=dict(counts),boundary_counts=dict(boundcounts),paths=paths,boundary_paths=bpaths,outside_promise_fixture=outside,seconds=time.monotonic()-START,outputs={f:sha(D/f) for f in files})
 (D/'SIMPLIFIED_SUMMARY08.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return ok
if __name__=='__main__':raise SystemExit(not main())

from pathlib import Path
from itertools import product
from functools import lru_cache
from datetime import datetime,timezone
import importlib.util,json,gzip,io,hashlib,time
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('old',D.parent/'joint_work_general_r_01/check01.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def solve(w,pred):
 @lru_cache(None)
 def rec(S,b,a):
  if not S or not b:return ((0,0),)
  out=[]
  for i,v in enumerate(w):
   if not(S>>i&1) or pred[i]&S:continue
   R=S^(1<<i);same=rec(R,b,a);out.extend((e,v+l) for e,l in same)
   if a:
    bad=rec(R,b-1,a-1);failed=rec(S,b-1,a-1)
    out.extend((max(e0,v+e1),max(l0,v+l1)) for e0,l0 in same for e1,l1 in bad)
    out.extend((max(e0,v+e1),max(l0,l1)) for e0,l0 in same for e1,l1 in failed)
  return old.nd(out)
 return rec

def ndcurves(rows):
 out=[]
 for p in sorted(set(rows)):
  if not any(all(a<=b for a,b in zip(q,p)) for q in out):out.append(p)
 return tuple(out)

def universal(w,pred,width):
 @lru_cache(None)
 def rec(S,a):
  if not S:return ((0,)*width,)
  out=[]
  for i,v in enumerate(w):
   if not(S>>i&1) or pred[i]&S:continue
   R=S^(1<<i);same=rec(R,a);out.extend(tuple(v+x for x in t) for t in same)
   if a:
    for match in same:
     for bad in rec(R,a-1):out.append(tuple(match[b] if b==0 else max(match[b],v+bad[b-1]) for b in range(width)))
     for fail in rec(S,a-1):out.append(tuple(match[b] if b==0 else max(match[b],fail[b-1]) for b in range(width)))
  return ndcurves(out)
 return rec

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(f,x):f.write(json.dumps(x,separators=(',',':'))+'\n')
def gz(p):return io.TextIOWrapper(gzip.GzipFile(filename='',mode='wb',fileobj=p.open('xb'),mtime=0),encoding='utf-8',newline='\n')
def main():
 fixed=json.loads((D/'INPUT_FIX_RECEIPT01.json').read_text())
 for x in fixed['files']:assert sha(D/x['path'])==x['sha256']
 assert sha(D.parent/'joint_work_general_r_01/check01.py')==fixed['inherited_sha256']
 O=D/'run01';O.mkdir();start=time.monotonic();counts=dict(inputs=0,supplied_roots=0,changed_original_frontiers=0,universal_inputs=0,universal_roots=0);fail=[]
 with gz(O/'SUPPLIED.jsonl.gz') as sf,gz(O/'UNIVERSAL.jsonl.gz') as uf:
  for n in range(1,5):
   pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
   for mask in range(1<<len(pairs)):
    edges=[p for k,p in enumerate(pairs) if mask>>k&1];pred=[0]*n
    for i,j in edges:pred[j]|=1<<i
    for w in product([1,2],repeat=n):
     id=counts['inputs'];G=solve(w,pred);C=old.Canonical(w,pred);S=(1<<n)-1;Omega=sum(w)
     for r in range(3):
      for B in range(r+3):
       got=tuple((Omega+e,l) for e,l in G(S,B,r));orig=tuple((Omega+e,l) for e,l in C.solve(S,B,r))
       if B==0:exp=((Omega,0),)
       elif B>r:exp=((Omega,Omega),)
       else:exp=old.nd([(Omega,Omega)]+[(Omega+B*t,Omega-sum(v for v in w if v<=t)) for t in sorted(set(w))])
       if got!=exp:fail.append(dict(id=id,w=w,edges=edges,B=B,r=r,expected=exp,actual=got))
       changed=got!=orig;counts['changed_original_frontiers']+=changed;counts['supplied_roots']+=1
       emit(sf,dict(id=id,w=w,edges=edges,B=B,r=r,split=got,original=orig,changed=changed))
     counts['inputs']+=1
     if n<=3:
      for r in range(3):
       width=r+2;curves=universal(w,pred,width)(S,r);exp=(tuple(0 if b<r else Omega for b in range(width)),)
       if curves!=exp:fail.append(dict(id=id,kind='universal',r=r,actual=curves,expected=exp))
       emit(uf,dict(id=id,w=w,edges=edges,r=r,curves=curves,expected=exp));counts['universal_roots']+=1
      counts['universal_inputs']+=1
 r=dict(utc=datetime.now(timezone.utc).isoformat(),status='SUCCESS' if not fail and counts['inputs']==1098 and counts['supplied_roots']==13176 and counts['universal_inputs']==74 and counts['universal_roots']==222 else 'FAILED',counts=counts,failures=fail,seconds=time.monotonic()-start,files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(O.glob('*.gz'))])
 (O/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return int(r['status']!='SUCCESS')
if __name__=='__main__':raise SystemExit(main())

from pathlib import Path
from itertools import permutations
from functools import lru_cache
from datetime import datetime,timezone
from collections import Counter
import json,gzip,io,hashlib,time,traceback,importlib.util
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prior_charged',D.parent/'charged_comparison_01/check04.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
prune=prior.prune

def order_for(w,mask,ascending=False):
 return tuple(sorted((i for i in range(len(w)) if mask>>i&1),key=lambda i:(w[i] if ascending else -w[i],i)))+tuple(i for i in range(len(w)) if not mask>>i&1)
def subset_point(w,g,mask,ascending=False):
 p=0;K=0
 for i in order_for(w,mask,ascending):
  if mask>>i&1:p+=g[i];K=max(K,p+w[i])
 return (sum(w)+max(sum(g),K),max(sum(g)+sum(w[i] for i in range(len(w)) if not mask>>i&1),K)),K

def subset_front(w,g,ascending=False):
 vals={}
 for mask in range(1<<len(w)):
  point,K=subset_point(w,g,mask,ascending);vals.setdefault(point,mask)
 return prune(vals),vals

def profit_dp(w,g,T,ignore_deadline=False):
 # exact selected guard sum -> (largest saved work, selected mask)
 states={0:(0,0)}
 for i in sorted(range(len(w)),key=lambda i:(-w[i],i)):
  nxt=dict(states)
  for p,(v,mask) in states.items():
   q=p+g[i]
   if (ignore_deadline or q+w[i]<=T) and (q not in nxt or nxt[q][0]<v+w[i]):nxt[q]=(v+w[i],mask|(1<<i))
  states=nxt
 return max(states.values())

def profit_count(w,g,T,reuse=False):
 n=len(w);vals=[None]*(n+1);vals[0]=(0,0)
 for i in sorted(range(n),key=lambda i:(-w[i],i)):
  old=vals if reuse else list(vals)
  for j in range(n):
   if old[j] is None:continue
   v,mask=old[j]
   if (j+1)*g+w[i]<=T and (vals[j+1] is None or vals[j+1][0]<v+w[i]):vals[j+1]=(v+w[i],mask|(1<<i))
 return max(x for x in vals if x is not None)

def decision(w,g,KW,KP,cache=None,variant='normal'):
 O=sum(w);G=sum(g);M=KW-O;T=min(M,KP)
 if variant!='ignore_Gamma' and (G>M or G>KP):return False,0
 key=(T,variant)
 if cache is not None and key in cache:v,mask=cache[key]
 else:
  if variant=='uniform_assumption':v,mask=profit_count(w,g[0],T)
  elif variant=='count_reuse':v,mask=profit_count(w,g[0],T,True)
  else:v,mask=profit_dp(w,g,T,variant=='ignore_deadline')
  if cache is not None:cache[key]=(v,mask)
 return v>=G+O-KP,mask

def uniform_front(w,g):
 points={};rows=[]
 for T in sorted({0}|{v+j*g for v in w for j in range(1,len(w)+1)}):
  v,mask=profit_count(w,g,T);point,K=subset_point(w,[g]*len(w),mask)
  points.setdefault(point,mask);rows.append(dict(T=T,saved=v,mask=mask,K=K,point=point))
 return prune(points),points,rows

def caps(front,O):
 xs={0,max(0,O-1)};ys={0}
 for a,b in front:
  xs.update(max(0,a+d) for d in [-1,0,1]);ys.update(max(0,b+d) for d in [-1,0,1])
 return [(x,y) for x in sorted(xs) for y in sorted(ys)]
def has(front,a,b):return any(x<=a and y<=b for x,y in front)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def emit(f,x):f.write(json.dumps(x,separators=(',',':'))+'\n')
def open_gz(p):return io.TextIOWrapper(gzip.GzipFile(filename='',mode='wb',fileobj=p.open('xb'),mtime=0),encoding='utf-8',newline='\n')

def main():
 fixed=json.loads((D/'INPUT_FIX_RECEIPT01.json').read_text())
 for r in fixed['files']:assert sha(D/r['path'])==r['sha256'],r['path']
 assert sha(D.parent/'charged_comparison_01/check04.py')==fixed['inherited_checker_sha256']
 I=json.loads((D/'INPUTS01.json').read_text());O=D/'run01';O.mkdir();start=time.monotonic();counts=Counter();fail=[];controls={};error=None
 put(O/'START.json',dict(utc=datetime.now(timezone.utc).isoformat(),input_fix=fixed))
 def req(ok,kind,id,detail):
  if not ok:fail.append(dict(kind=kind,id=id,detail=detail))
 def ctl(name,id,correct,altered,detail):
  if name not in controls and correct!=altered:controls[name]=dict(id=name,input=id,correct=correct,altered=altered,detail=detail,detected=True)
 try:
  with open_gz(O/'ROWS.jsonl.gz') as rows,open_gz(O/'POLICIES.jsonl.gz') as pol,open_gz(O/'CAPS.jsonl.gz') as caplog,open_gz(O/'PATHS.jsonl.gz') as paths:
   for x in I['general']:
    w,g,id=x['w'],x['g'],x['id'];n=len(w);front,states=prior.dp(w,g,[0]*n,[]);direct=[]
    for order in permutations(range(n)):
     for mask in range(1<<n):
      point=prior.formula(w,g,[0]*n,order,mask);direct.append(point);emit(pol,[id,order,mask,point]);counts['order_mask_pairs']+=1
    ff=prune(direct);ss,witness=subset_front(w,g)
    req(front==ff==ss,'general_frontiers',id,dict(dp=front,all_order=ff,subset=ss));counts['direct_dp_states']+=states
    ctl('ascending_work_sort',id,ss,subset_front(w,g,True)[0],dict(w=w,g=g))
    muttotal=[];mutprotect=[]
    for mask in range(1<<n):
     pt,K=subset_point(w,g,mask)
     muttotal.append((sum(w)+max([w[i] for i in range(n) if mask>>i&1],default=0),pt[1]))
     mutprotect.append((pt[0],sum(g)+sum(w[i] for i in range(n) if not mask>>i&1)))
    ctl('ignore_entry_in_total',id,ss,prune(muttotal),dict(w=w,g=g));ctl('ignore_K_in_protection',id,ss,prune(mutprotect),dict(w=w,g=g))
    cache={}
    for KW,KP in caps(front,sum(w)):
     expected=has(front,KW,KP);got,mask=decision(w,g,KW,KP,cache)
     req(got==expected,'guard_DP_cap',id,dict(caps=[KW,KP],expected=expected,actual=got,mask=mask))
     if got:req(all(a<=b for a,b in zip(subset_point(w,g,mask)[0],[KW,KP])),'guard_DP_witness',id,dict(mask=mask,caps=[KW,KP]))
     for name,variant in [('ignore_Gamma_cap','ignore_Gamma'),('count_DP_on_heterogeneous_guards','uniform_assumption'),('allow_late_selected_job','ignore_deadline')]:
      if name not in controls:
       bad,bm=decision(w,g,KW,KP,cache,variant);ctl(name,id,expected,bad,dict(w=w,g=g,caps=[KW,KP],mask=bm))
     emit(caplog,[id,KW,KP,expected,got,mask]);counts['general_cap_queries']+=1
    emit(rows,dict(id=id,frontier=front,subsets=ss,states=states));counts['general_inputs']+=1
   print('general',dict(counts),flush=True)
   for x in I['uniform']:
    w,g,id=x['w'],x['guard'],x['id'];gs=[g]*len(w);front,states=prior.dp(w,gs,[0]*len(w),[]);ss,_=subset_front(w,gs);uf,wit,thresholds=uniform_front(w,g)
    req(front==ss==uf,'uniform_frontier',id,dict(dp=front,subset=ss,count=uf));req(len(uf)<=len(w)**2+1,'uniform_size',id,dict(size=len(uf)))
    cache={}
    for KW,KP in caps(front,sum(w)):
     exp=has(front,KW,KP);got,mask=decision(w,gs,KW,KP,cache)
     M=KW-sum(w);T=min(M,KP);saved,bmask=profit_count(w,g,T);countgot=sum(gs)<=M and sum(gs)<=KP and saved>=sum(gs)+sum(w)-KP
     req(got==exp==countgot,'uniform_cap',id,dict(caps=[KW,KP],expected=exp,guard=got,count=countgot))
     if 'reuse_zero_guard_item' not in controls and g==0:
      bad,bm=decision(w,gs,KW,KP,cache,'count_reuse');ctl('reuse_zero_guard_item',id,exp,bad,dict(w=w,g=gs,caps=[KW,KP],mask=bm))
     emit(caplog,[id,KW,KP,exp,got,countgot]);counts['uniform_cap_queries']+=1
    emit(rows,dict(id=id,frontier=front,thresholds=thresholds));counts['uniform_thresholds']+=len(thresholds);counts['uniform_inputs']+=1
   print('uniform',dict(counts),flush=True)
   for x in I['subset']:
    a,id=x['items'],x['id'];m=len(a);S=sum(a);d=q=S+1;b=list(a)+[0]*m;g=[q*(d+v) for v in b];G=sum(g);k=G+S+1;w=[k+v for v in b];ss,wit=subset_front(w,g)
    direct=None
    if m<=3:
     direct,states=prior.dp(w,g,[0]*len(w),[]);req(direct==ss,'embedding_mode_frontier',id,dict(dp=direct,subsets=ss));counts['embedding_direct_inputs']+=1
    truths={sum(a[i] for i in range(m) if mask>>i&1) for mask in range(1<<m)};cache={}
    for A in x['targets']:
     M=k+q*(m*d+A)+S;KW=sum(w)+M;KP=G+m*k+S-A;expected=A in truths;enumerated=has(ss,KW,KP);got,mask=decision(w,g,KW,KP,cache)
     req(got==enumerated==expected,'subset_embedding_target',id,dict(target=A,expected=expected,enumerated=enumerated,dp=got,caps=[KW,KP]))
     req(G<=M<=KP,'subset_embedding_cap_order',id,dict(target=A,Gamma=G,M=M,KP=KP))
     if got:req(mask.bit_count()==m and sum(b[i] for i in range(2*m) if mask>>i&1)==A,'embedding_witness',id,dict(target=A,mask=mask))
     emit(caplog,[id,A,KW,KP,expected,enumerated,got,mask]);counts['embedding_target_queries']+=1;counts['embedding_yes' if expected else 'embedding_no']+=1
    emit(rows,dict(id=id,w=w,g=g,frontier=ss,mode_frontier=direct));counts['embedding_inputs']+=1;counts['embedding_subsets']+=1<<len(w)
   print('embedding',dict(counts),flush=True)
   for n in I['output_family']:
    id=f'p{n}';b=[0]+[1<<i for i in range(n-1)];S=sum(b);d=q=S+1;g=[q*(d+v) for v in b];G=sum(g);k=G+S+1;w=[k+v for v in b];front,states=prior.dp(w,g,[0]*n,[]);ss,wit=subset_front(w,g)
    req(front==ss,'output_family_frontier',id,dict(dp=front,subset=ss));req(len(front)==(1<<n)-1,'output_family_size',id,dict(expected=(1<<n)-1,actual=len(front)))
    for mask in range(1<<n):
     order=order_for(w,mask);point,K=subset_point(w,g,mask);h=mask.bit_count();s=sum(b[i] for i in range(n) if mask>>i&1)
     if mask and mask!=(1<<n)-1:
      predicted=(sum(w)+k+q*(h*d+s)+min(b[i] for i in range(n) if mask>>i&1),G+(n-h)*k+S-s)
      req(point==predicted and point in front,'output_proper_subset',id,dict(mask=mask,predicted=predicted,actual=point))
     maxW=maxP=0
     for bad in [None]+[i for i in range(n) if mask>>i&1]:
      t=prior.trace(w,g,[0]*n,order,mask,bad);maxW=max(maxW,t['Wt']);maxP=max(maxP,t['Pt']);emit(paths,dict(id=id,mask=mask,order=order,bad=bad,**t));counts['output_paths']+=1
     req((maxW,maxP)==point,'output_path_maxima',id,dict(mask=mask,actual=[maxW,maxP],formula=point))
    emit(rows,dict(id=id,w=w,g=g,frontier=front));counts['output_inputs']+=1;counts['output_frontier_points']+=len(front);counts['output_subsets']+=1<<n
   for name in I['controls']:
    req(name in controls,'control_undetected',name,{});controls.setdefault(name,dict(id=name,detected=False))
 except Exception:
  error=traceback.format_exc();(O/'EXCEPTION.txt').write_text(error)
 put(O/'CONTROLS.json',list(controls.values()))
 for key,inp in [('general_inputs','general'),('uniform_inputs','uniform'),('embedding_inputs','subset'),('output_inputs','output_family')]:req(counts[key]==len(I[inp]),'incomplete_denominator',key,dict(actual=counts[key],expected=len(I[inp])))
 r=dict(utc=datetime.now(timezone.utc).isoformat(),status='SUCCESS' if not fail and error is None else 'FAILED',counts=dict(counts),controls_detected=sum(x['detected'] for x in controls.values()),failures=fail,exception=error,seconds=time.monotonic()-start,files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(O.glob('*.gz'))])
 put(O/'RESULT.json',r);print(json.dumps(r),flush=True);return int(r['status']!='SUCCESS')
if __name__=='__main__':raise SystemExit(main())

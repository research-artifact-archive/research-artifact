from pathlib import Path
from itertools import combinations
from functools import lru_cache
from collections import Counter
from datetime import datetime,timezone
import json,hashlib,gzip,io,time,traceback,signal,importlib.util,argparse
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prior_charged',D.parent/'charged_comparison_01/check04.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def emit(f,x):f.write(json.dumps(x,separators=(',',':'))+'\n')
def gz(p):return io.TextIOWrapper(gzip.GzipFile(filename='',mode='wb',fileobj=p.open('xb'),mtime=0),encoding='utf-8',newline='\n')
def has(front,caps):return any(a<=caps[0] and b<=caps[1] for a,b in front)
def clique(v,e,k):
 es={tuple(x) for x in e}
 for c in combinations(range(v),k):
  if all(x in es for x in combinations(c,2)):return c
 return None
def reduce(x):
 v=x['v']+2;e=x['edges']+[[x['v'],x['v']+1]];m=len(e);n=v+m;H=n+1;K=x['k']*(x['k']-1)//2;D0=x['k']+K;M=D0+H
 w=[1]*v+[H]*m;dag=[[u,v+j] for j,edge in enumerate(e) for u in edge]
 return dict(v=v,m=m,n=n,H=H,K=K,D=D0,M=M,w=w,edges=dag,graph_edges=e,caps=[sum(w)+M,n+(m-K)*H])
def fee_dp(w,g,d,edges,omit_suffix=False):
 n=len(w);pred=[0]*n
 for a,b in edges:pred[b]|=1<<a
 @lru_cache(None)
 def solve(mask):
  if not mask:return ((0,0),)
  vals=[]
  for i in range(n):
   if not(mask>>i&1) or mask&pred[i]:continue
   rem=mask^(1<<i);body=sum(w[j] for j in range(n) if rem>>j&1);fees=0 if omit_suffix else sum(d[j] for j in range(n) if rem>>j&1)
   for a,b in solve(rem):
    vals.append((w[i]+g[i]+d[i]+a,w[i]+g[i]+d[i]+b))
    vals.append((max(w[i]+g[i]+d[i]+a,2*w[i]+g[i]+d[i]+body+fees),max(g[i]+d[i]+b,w[i]+g[i]+d[i]+fees)))
  return prior.prune(vals)
 return solve((1<<n)-1),solve.cache_info().currsize
def translate(front,fee):return tuple((a+fee,b+fee) for a,b in front)
def timeout(sig,frame):raise TimeoutError('fixed900s or global preparation deadline reached')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--deadline-utc');args=parser.parse_args()
 fixed=json.loads((D/'INPUT_FIX_RECEIPT02.json').read_text())
 for n,r in fixed['files'].items():assert sha(D/n)==r['sha256'],n
 assert sha(D.parent/'charged_comparison_01/check04.py')==fixed['inherited_checker_sha256']
 I=json.loads((D/'INPUTS01.json').read_text());O=D/'run02';O.mkdir();start=time.monotonic();count=Counter();fail=[];controls={};error=None;active_input=None
 put(O/'START.json',dict(utc=datetime.now(timezone.utc).isoformat(),fixed=fixed,deadline_utc=args.deadline_utc,wall_limit_seconds=900))
 signal.signal(signal.SIGALRM,timeout)
 def req(ok,kind,id,detail):
  if not ok:fail.append(dict(kind=kind,id=id,detail=detail))
 def ctl(name,id,correct,altered,detail):
  if name not in controls and correct!=altered:controls[name]=dict(id=name,input=id,correct=correct,altered=altered,detail=detail,detected=True)
 try:
  limit=900
  if args.deadline_utc:
   left=(datetime.fromisoformat(args.deadline_utc.replace('Z','+00:00'))-datetime.now(timezone.utc)).total_seconds()
   if left<=0:raise TimeoutError('research preparation deadline already reached')
   limit=min(limit,max(1,int(left)))
  signal.alarm(limit)
  with gz(O/'SOURCE_ROWS.jsonl.gz') as rows,gz(O/'PATHS.jsonl.gz') as paths,gz(O/'GENERAL_ROWS.jsonl.gz') as general:
   for x in I['sources']:
    active_input=dict(study='sources',id=x['id']);count['source_started']+=1
    witness=clique(x['v'],x['edges'],x['k']);expected=witness is not None
    if x['branch']=='trivial_no':
     req(not expected,'trivial_source',x['id'],dict(clique=witness));emit(rows,dict(source=x,clique=witness,branch='trivial_no',target=dict(w=[1,1,1],g=[1,1,1],c=[0,0,0],edges=[[0,2],[1,2]],caps=[5,6]),decision=False));count['source_cases']+=1;count['trivial_no_cases']+=1;active_input=None;continue
    count['embedding_started']+=1
    r=reduce(x);n=r['n'];w=r['w'];gs=[1]*n;e=r['edges'];front,states=prior.dp(w,gs,[0]*n,e);got=has(front,r['caps'])
    count['embedding_dp_states']+=states
    req(got==expected,'source_vs_cap',x['id'],dict(source=x,reduced=r,frontier=front,clique=witness))
    req(n>r['D'] and r['caps'][1]>r['M']>n,'padding_inequalities',x['id'],r)
    req(max(w)<=n+1 and max(r['caps'])<=2*(n+1)**2,'numerical_bounds',x['id'],r)
    req(len(front)<=n*n+1,'embedding_point_count',x['id'],dict(points=len(front),n=n))
    fee,fs=fee_dp(w,gs,[1]*n,e);count['embedding_fee_states']+=fs
    req(fee==translate(front,n),'embedding_fee_translation',x['id'],dict(frontier=front,charged=fee,n=n))
    policy=None;maxW=maxP=0
    if expected:
     inside=[j for j,(a,b) in enumerate(r['graph_edges']) if a in witness and b in witness];cached=list(witness)+[r['v']+j for j in inside]+[j for j in range(r['v']) if j not in witness]
     order=cached+[r['v']+j for j in range(r['m']) if j not in inside];mask=sum(1<<j for j in cached);pos={j:i for i,j in enumerate(order)};policy=dict(order=order,mask=mask)
     req(sorted(order)==list(range(n)) and all(pos[a]<pos[b] for a,b in e),'constructive_order',x['id'],policy)
     req(prior.formula(w,gs,[0]*n,order,mask)==tuple(r['caps']),'constructive_formula',x['id'],policy)
     for bad in [None]+cached:
      t=prior.trace(w,gs,[0]*n,order,mask,bad);maxW=max(maxW,t['Wt']);maxP=max(maxP,t['Pt']);count['constructive_paths']+=1
      req(t['Q']==n and t['Wt']<=r['caps'][0] and t['Pt']<=r['caps'][1],'constructive_path',x['id'],dict(bad=bad,trace=t,caps=r['caps']))
      emit(paths,dict(id=x['id'],bad=bad,**t))
     req([maxW,maxP]==r['caps'],'constructive_attainment',x['id'],dict(actual=[maxW,maxP],caps=r['caps']))
    if 'remove_precedence' not in controls:
     other,ss=prior.dp(w,gs,[0]*n,[]);count['control_dp_states']+=ss;ctl('remove_precedence',x['id'],got,has(other,r['caps']),dict(caps=r['caps'],frontier=front,altered_frontier=other))
    # Without the no-write protected term, all-fresh has no cached mismatch term.
    ctl('ignore_no_write_load',x['id'],got,sum(w)+n<=r['caps'][0],dict(caps=r['caps'],altered_all_fresh_point=[sum(w)+n,0]))
    if 'omit_cheap_suffix_fees' not in controls:
     other,ss=fee_dp(w,gs,[1]*n,e,True);count['control_fee_states']+=ss;ctl('omit_cheap_suffix_fees',x['id'],fee,other,dict(w=w,edges=e))
    emit(rows,dict(source=x,clique=witness,reduced=r,frontier=front,decision=got,states=states,fee_frontier=fee,fee_states=fs,policy=policy))
    count['source_cases']+=1;count['embedding_cases']+=1;count['positive_sources' if expected else 'negative_sources']+=1;active_input=None
    if count['embedding_cases']%100==0:print('embedding',dict(count),flush=True)
   for x in I['general']:
    active_input=dict(study='general',id=x['id']);count['general_started']+=1
    w=x['w'];n=len(w);g=x['g'];gs=[g]*n;e=x['edges'];front,states=prior.dp(w,gs,[0]*n,e);direct,wit,plans=prior.policies(w,gs,[0]*n,e);fee,fs=fee_dp(w,gs,x['d'],e)
    values={sum(w)+n*g}|{sum(w)+w[i]+j*g for i in range(n) for j in range(1,n+1)}
    req(front==direct,'general_full_frontier',x['id'],dict(dp=front,order=direct))
    req(len(front)<=n*n+1 and all(a in values for a,b in front),'general_output_bound',x['id'],dict(frontier=front,values=sorted(values)))
    req(fee==translate(front,sum(x['d'])),'general_fee_translation',x['id'],dict(frontier=front,fee=fee,d=x['d']))
    if 'omit_cheap_suffix_fees' not in controls:
     other,ss=fee_dp(w,gs,x['d'],e,True);count['control_fee_states']+=ss;ctl('omit_cheap_suffix_fees',x['id'],fee,other,x)
    count['general_dp_states']+=states;count['general_fee_states']+=fs;count['order_mask_policies']+=plans
    emit(general,dict(input=x,frontier=front,order_frontier=direct,fee_frontier=fee,states=states,fee_states=fs,policies=plans,coordinate_values=sorted(values)))
    count['general_cases']+=1;active_input=None
   for name in ['remove_precedence','ignore_no_write_load','omit_cheap_suffix_fees']:req(name in controls,'undetected_control',name,{})
   count['controls']=len(controls)
 except Exception:
  error=traceback.format_exc();(O/'EXCEPTION.txt').write_text(error)
 finally:signal.alarm(0)
 put(O/'CONTROLS.json',controls)
 complete=all(count[k]==v for k,v in fixed['counts'].items());result=dict(status='SUCCESS' if not fail and not error and complete else 'FAILED',counts=dict(count),fixed_counts=fixed['counts'],complete_denominator=complete,failures=fail,exception=error,seconds=time.monotonic()-start,utc=datetime.now(timezone.utc).isoformat(),inputs_sha256=sha(D/'INPUTS01.json'),checker_sha256=sha(D/'check02.py'),active_input=active_input)
 put(O/'RESULT.json',result);print(json.dumps(result));return 0 if result['status']=='SUCCESS' else 1
if __name__=='__main__':raise SystemExit(main())

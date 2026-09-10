from pathlib import Path
from functools import lru_cache
from itertools import permutations
import argparse, datetime, gzip, hashlib, io, json, time, traceback

D=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def prune(points):
 out=[]; best=None
 for a,b in sorted(set(points)):
  if best is None or b<best: out.append((a,b));best=b
 return tuple(out)
def predmask(n,edges):
 pred=[0]*n
 for a,b in edges: pred[b]|=1<<a
 return pred
def ready(S,pred): return [i for i,p in enumerate(pred) if S>>i&1 and not p&S]
def lawler(w,g,edges,M):
 n=len(w);succ=[0]*n
 for a,b in edges:succ[a]|=1<<b
 rem=(1<<n)-1;reverse=[]
 q=[0 if x>M else x for x in w]
 while rem:
  sinks=[i for i in range(n) if rem>>i&1 and not succ[i]&rem]
  j=min(sinks,key=lambda i:(q[i],i));reverse.append(j);rem^=1<<j
 order=list(reversed(reverse));cum=0;value=0
 for i in order:
  cum+=g[i]+(w[i] if w[i]>M else 0);value=max(value,cum+q[i])
 return value,order

def A_recursion(w,g,edges):
 n=len(w); pred=predmask(n,edges);calls=0
 @lru_cache(None)
 def rec(S):
  nonlocal calls;calls+=1
  if not S:return ((0,0),)
  result=[]
  for i in ready(S,pred):
   T=S^(1<<i);suffix0=sum(w[j] for j in range(n) if T>>j&1)
   for a,b in rec(T):
    result.append((w[i]+a,w[i]+g[i]+b))
    result.append((max(w[i]+a,2*w[i]+suffix0),max(g[i]+b,g[i]+w[i])))
  return prune(result)
 result=rec((1<<n)-1)
 return result,calls

def A_exhaustive(w,g,edges):
 n=len(w);S=sum(w);points=[];plans=0
 for order in permutations(range(n)):
  pos={x:k for k,x in enumerate(order)}
  if any(pos[a]>pos[b] for a,b in edges):continue
  for C in range(1<<n):
   plans+=1;spent=0;peak=0;duplicate=0
   for i in order:
    spent+=g[i]
    if C>>i&1:peak=max(peak,spent+w[i]);duplicate=max(duplicate,w[i])
    else:spent+=w[i]
   points.append((S+duplicate,max(peak,spent)))
 return prune(points),plans

def A_trace(w,g,order,M,bad,guard_suffix=False):
 W=P=Q=0;used=False;events=[]
 for i in order:
  if used:mode='cached' if guard_suffix else 'cheap'
  else:mode='fresh' if w[i]>M else 'cached'
  outside=0;inside=0;entry=0;mismatch=False
  if mode=='fresh':inside=w[i];entry=g[i]
  else:
   outside=w[i]
   if mode=='cached':
    entry=g[i]
    if i==bad and not used:inside=w[i];mismatch=True;used=True
  Q+=1;W+=outside+inside;P+=inside+entry
  events.append({'job':i,'mode':mode,'outside_body':outside,'protected_body':inside,'guard_charge':entry,'mismatch':mismatch})
 assert Q==len(w)
 return {'W':W,'Pg':P,'Q':Q,'writes':int(used),'events':events}

def subset_pairs(w,c,g):
 n=len(w);base=sum(w)+sum(g);rows=[]
 for mask in range(1<<n):
  total=base;protected=base
  for i in range(n):
   if mask>>i&1:total+=c[i];protected+=c[i]-w[i]
  rows.append((total,protected,mask))
 best={}
 for a,b,m in rows:best.setdefault((a,b),m)
 front=prune(best)
 return front,{point:best[point] for point in front}

def capacity_dp(w,c,g):
 cap=sum(c);dp=[None]*(cap+1);witness=[None]*(cap+1);dp[0]=0;witness[0]=0
 for i,(work,cost) in enumerate(zip(w,c)):
  profit=work-cost
  for j in range(cap,cost-1,-1):
   if dp[j-cost] is not None:
    v=dp[j-cost]+profit
    if dp[j] is None or v>dp[j]:dp[j]=v;witness[j]=witness[j-cost]|(1<<i)
 base=sum(w)+sum(g)
 front=prune((base+j,base-v) for j,v in enumerate(dp) if v is not None)
 return front,dp,witness

def B_mode_recursion(w,c,g,edges):
 n=len(w);pred=predmask(n,edges);states=0
 @lru_cache(None)
 def rec(S):
  nonlocal states;states+=1
  if not S:return ((0,0),)
  pts=[]
  for i in ready(S,pred):
   for a,b in rec(S^(1<<i)):
    pts.append((a+w[i]+g[i],b+w[i]+g[i]))
    pts.append((a+w[i]+g[i]+c[i],b+g[i]+c[i]))
  return prune(pts)
 f=rec((1<<n)-1);return f,states

def B_trace(w,c,g,edges,mask):
 n=len(w);pred=predmask(n,edges);S=(1<<n)-1;Wt=Pt=Q=0;events=[]
 while S:
  i=min(ready(S,pred));S^=1<<i
  if mask>>i&1:
   events.append({'opcode':'prepare','job':i,'Wt':w[i],'Pt':0});Wt+=w[i]
   events.append({'opcode':'cached_match','job':i,'Wt':g[i]+c[i],'Pt':g[i]+c[i]});Wt+=g[i]+c[i];Pt+=g[i]+c[i]
  else:
   events.append({'opcode':'fresh','job':i,'Wt':w[i]+g[i],'Pt':w[i]+g[i]});Wt+=w[i]+g[i];Pt+=w[i]+g[i]
  Q+=1
 assert Q==n
 return {'Wt':Wt,'Pt':Pt,'Q':Q,'writes':0,'mask':mask,'events':events,'universal_call_cap_reason':'only completing operations; no cheap calls'}

def uniform_frontier(w,c,g):
 assert len(set(c))==1
 base=sum(w)+sum(g);cost=c[0];profits=sorted((x-cost for x in w if x>cost),reverse=True)
 points=[(base,base)];saved=0
 for k,v in enumerate(profits,1):saved+=v;points.append((base+k*cost,base-saved))
 return tuple(points)

def gzip_text(path):
 raw=path.open('xb');z=gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0)
 return io.TextIOWrapper(z,encoding='utf-8',newline='\n')
def emit(f,obj):f.write(json.dumps(obj,separators=(',',':'))+'\n')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();O=Path(args.out);O.mkdir()
 inputs=json.loads((D/'INPUTS01.json').read_text());fixed=json.loads((D/'INPUT_FIX_RECEIPT01.json').read_text())
 assert sha(D/'INPUTS01.json')==fixed['input']['sha256']
 started=time.monotonic();counts={'A_inputs':0,'A_threshold_roots':0,'A_recursion_states':0,'A_enumerated_plans':0,'A_paths':0,'B_inputs':0,'B_recursion_states':0,'B_paths':0,'knapsack_inputs':0,'knapsack_decision_pairs':0,'controls':0};failures=[];caught=None
 start={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':fixed['input'],'fixed_counts':fixed['counts'],'files':{n:sha(D/n) for n in ['PROOF_CANDIDATE01.md','PROTOCOL01.md','CONTROL_PREDICTION_NOTE01.md','check01.py','generate_inputs01.py']}}
 (O/'START.json').write_text(json.dumps(start,indent=2)+'\n')
 def require(ok,kind,identity,payload):
  if not ok:failures.append({'kind':kind,'id':identity,'payload':payload})
 try:
  with gzip_text(O/'A_ROWS.jsonl.gz') as rows,gzip_text(O/'A_PATHS.jsonl.gz') as paths:
   for x in inputs['A']:
    w,g,edges=x['w'],x['g'],x['edges'];oracle,states=A_recursion(w,g,edges);counts['A_recursion_states']+=states
    brute=None;plans=0
    if x['n']<=4:
     brute,plans=A_exhaustive(w,g,edges);counts['A_enumerated_plans']+=plans
     require(brute==oracle,'A_exhaustive_recursion',x['id'],{'brute':brute,'recursion':oracle})
    thresholds=[]
    for M in sorted(set([0]+w)):
     val,order=lawler(w,g,edges,M);points=[b for a,b in oracle if a<=sum(w)+M];expected=min(points)
     require(val==expected,'A_Lawler',x['id'],{'M':M,'lawler':val,'oracle':expected})
     tr=[]
     for bad in [None]+[i for i in order if w[i]<=M]:
      path=A_trace(w,g,order,M,bad);counts['A_paths']+=1;emit(paths,{'input':x['id'],'M':M,'bad':bad,**path});tr.append(path)
     maxW=max(p['W'] for p in tr);maxP=max(p['Pg'] for p in tr)
     require(maxW<=sum(w)+M and maxP==val,'A_witness',x['id'],{'M':M,'maxW':maxW,'maxP':maxP,'lawler':val})
     thresholds.append({'M':M,'value':val,'order':order,'maxW':maxW,'maxPg':maxP,'path_count':len(tr)});counts['A_threshold_roots']+=1
    formula_front=prune((sum(w)+v['M'],v['value']) for v in thresholds)
    require(formula_front==oracle,'A_frontier',x['id'],{'formula':formula_front,'oracle':oracle})
    emit(rows,{'input':x['id'],'status':'PASS' if not any(f['id']==x['id'] and f['kind'].startswith('A_') for f in failures) else 'FAIL','frontier':oracle,'exhaustive_frontier':brute,'enumerated_plans':plans,'thresholds':thresholds});counts['A_inputs']+=1
  with gzip_text(O/'B_ROWS.jsonl.gz') as rows,gzip_text(O/'B_PATHS.jsonl.gz') as paths:
   for x in inputs['B']:
    w,c,g,edges=x['w'],x['c'],x['g'],x['edges'];front,masks=subset_pairs(w,c,g);dynamic,dp,_=capacity_dp(w,c,g)
    require(front==dynamic,'B_capacity_dp',x['id'],{'subsets':front,'dp':dynamic})
    rec=None
    if x['n']<=4:
     rec,states=B_mode_recursion(w,c,g,edges);counts['B_recursion_states']+=states
     require(rec==front,'B_mode_recursion',x['id'],{'recursion':rec,'subsets':front})
    for point in front:
     t=B_trace(w,c,g,edges,masks[point]);counts['B_paths']+=1;emit(paths,{'input':x['id'],**t})
     require((t['Wt'],t['Pt'])==point,'B_trace',x['id'],{'point':point,'trace':t})
    uniform=None
    if len(set(c))==1:
     uniform=uniform_frontier(w,c,g);require(uniform==front and len(front)<=x['n']+1,'B_uniform',x['id'],{'uniform':uniform,'subsets':front})
    if x['family']=='exponential_frontier':require(len(front)==1<<x['n'],'B_exponential_count',x['id'],{'actual':len(front),'expected':1<<x['n']})
    emit(rows,{'input':x['id'],'family':x['family'],'frontier':front,'capacity_profit':dp,'mode_recursion_frontier':rec,'uniform_frontier':uniform,'subset_count':1<<x['n'],'witness_count':len(front)});counts['B_inputs']+=1
  with gzip_text(O/'KNAPSACK_ROWS.jsonl.gz') as rows,gzip_text(O/'KNAPSACK_QUERIES.jsonl.gz') as queries:
   for x in inputs['knapsack']:
    a,v=x['sizes'],x['values'];n=x['n'];w=[a[i]+v[i] for i in range(n)];g=[1]*n;base=sum(w)+sum(g)
    front,masks=subset_pairs(w,a,g);_,dp,_=capacity_dp(w,a,g)
    item_sums=[(sum(a[i] for i in range(n) if mask>>i&1),sum(v[i] for i in range(n) if mask>>i&1)) for mask in range(1<<n)]
    for A in x['capacities']:
     best=max([0]+[p for weight,p in item_sums if weight<=A]);dpbest=max([0]+[p for p in dp[:A+1] if p is not None])
     for V in x['targets']:
      item=best>=V;mapped=any(Wt<=base+A and Pt<=base-V for Wt,Pt in front);dpy=dpbest>=V
      require(item==mapped==dpy,'K_decision',x['id'],{'A':A,'V':V,'item':item,'completion':mapped,'DP':dpy})
      emit(queries,{'input':x['id'],'capacity':A,'target':V,'item_feasible':item,'completion_feasible':mapped,'dp_feasible':dpy});counts['knapsack_decision_pairs']+=1
    emit(rows,{'input':x['id'],'mapped_w':w,'mapped_c':a,'mapped_g':g,'base':base,'completion_frontier':front,'item_subset_sums':item_sums});counts['knapsack_inputs']+=1
  controls=[]
  for x in inputs['controls']:
   cid=x['id'];payload={}
   if cid=='A_omit_guard':
    correct,_=lawler(x['w'],x['g'],x['edges'],x['M']);mutant,_=lawler(x['w'],[0]*len(x['w']),x['edges'],x['M']);detected=correct!=mutant;payload={'correct':correct,'mutant':mutant}
   elif cid=='A_keep_guard_after_mismatch':
    value,order=lawler(x['w'],x['g'],x['edges'],x['M']);bad=next(i for i in order if x['w'][i]<=x['M']);good=A_trace(x['w'],x['g'],order,x['M'],bad);mutant=A_trace(x['w'],x['g'],order,x['M'],bad,True);detected=good['Pg']!=mutant['Pg'];payload={'good':good,'mutant':mutant,'root_bound':value,'claim':'path-cost control; root frontier need not change'}
   else:
    w,c,g=x['w'],x['c'],x['g'];correct,masks=subset_pairs(w,c,g)
    if cid=='B_omit_total_comparison':
     base=sum(w)+sum(g);mutant=prune((base,P) for W,P in correct);detected=mutant!=correct;payload={'correct':correct,'mutant':mutant}
    elif cid=='B_informed_zero':
     informed=(sum(w),0);detected=not any(W<=informed[0] and P<=informed[1] for W,P in correct);payload={'universal_frontier':correct,'informed_zero':informed,'class_change':True}
    elif cid=='B_negative_profit_forced':
     forced=B_trace(w,c,g,[],(1<<len(w))-1);detected=any(W<=forced['Wt'] and P<=forced['Pt'] and (W,P)!=(forced['Wt'],forced['Pt']) for W,P in correct);payload={'correct':correct,'forced':forced}
    elif cid=='B_uniform_hardness_scope':
     f=uniform_frontier(w,c,g);detected=f==correct and len(f)<=len(w)+1;payload={'correct':correct,'uniform':f,'scope_exclusion':True}
    else:raise ValueError(cid)
   require(detected,'control',cid,payload);controls.append({'id':cid,'status':'DETECTED' if detected else 'MISSED','payload':payload});counts['controls']+=1
  (O/'CONTROLS.json').write_text(json.dumps(controls,indent=2)+'\n')
 except Exception as e:
  caught={'exception':repr(e),'traceback':traceback.format_exc()};(O/'EXCEPTION.json').write_text(json.dumps(caught,indent=2)+'\n')
 expected=fixed['counts'];missing={k:expected[k]-counts[k] for k in expected};status='SUCCESS' if not failures and not caught and not any(missing.values()) else 'FAILURE'
 result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'seconds':time.monotonic()-started,'counts':counts,'fixed_counts':expected,'not_executed':missing,'failures':failures,'exception':caught,'files':start['files'],'input_sha256':sha(D/'INPUTS01.json'),'new_native_runs':0,'new_timing_samples':0,'scope':'finite corroboration of two distinct charged-cost models; all-program and hardness conclusions are author proof obligations'}
 result['outputs']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(O.iterdir()) if p.is_file()]
 (O/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['files','outputs','failures']},indent=2),flush=True)
 if failures:print(json.dumps(failures[:5],indent=2),flush=True)
 raise SystemExit(0 if status=='SUCCESS' else 1)

if __name__=='__main__':main()

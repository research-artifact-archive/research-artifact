#!/usr/bin/env python3
from pathlib import Path
from functools import lru_cache
import itertools,time,json,datetime,hashlib,sys
HERE=Path(__file__).resolve().parent; START=time.monotonic()
def bounded():
 if time.monotonic()-START>300:raise TimeoutError('whole exploration cap300s')
def pareto(vs):
 out=[]
 for v in sorted(set(vs)):
  if any(all(a<=b for a,b in zip(u,v)) for u in out):continue
  out=[u for u in out if not all(a<=b for a,b in zip(v,u))];out.append(v)
 bounded();return tuple(out)
def study(obs,q,toll,direct):
 width=q*max(c for m,c,h in obs)+2
 @lru_cache(None)
 def trees(k,allow_direct):
  combined=(tuple([-1]*width),)
  for mask,c,h in obs:
   options=[tuple(-1 if b<c else toll+h for b in range(width))]
   if k>1:options += [tuple(-1 if b<c else toll+v[b-c] for b in range(width)) for v in trees(k-1,allow_direct)]
   combined=pareto(tuple(max(a,b) for a,b in zip(x,y)) for x in combined for y in options)
  if allow_direct:combined=pareto(combined+(tuple([direct]*width),))
  return combined
 plain=trees(q,False);full=trees(q,True);root_only=pareto(plain+(tuple([direct]*width),))
 old_curve=tuple(min(v[b] for v in plain) for b in range(width));new_curve=tuple(min(v[b] for v in full) for b in range(width))
 old_loss=min(max(a-b for a,b in zip(v,old_curve)) for v in plain);new_loss=min(max(a-b for a,b in zip(v,new_curve)) for v in full)
 @lru_cache(None)
 def informed(k,b):
  return min(direct,max(toll+(min(h,informed(k-1,b-c)) if k>1 else h) for m,c,h in obs if c<=b))
 scalar=tuple(informed(q,b) for b in range(width))
 root_min=tuple(min(direct,k) for k in old_curve)
 return {'observations':obs,'q':q,'T':toll,'S':direct,'old_curve':old_curve,'curve':new_curve,'old_loss':old_loss,'loss':new_loss,'vectors':full,'vector_count':len(full),'root_direct_only_frontier_equal':full==root_only,'scalar_informed_equal':new_curve==scalar,'min_comparator_equal':new_curve==root_min,'old_loss_upper_bound_claim':new_loss<=min(max(direct-toll,0),old_loss)}
def main():
 profiles=[]
 for weights in [(1,),(1,2),(1,2,3)]:profiles.append((str(weights),tuple((m,m.bit_count() if hasattr(m,'bit_count') else bin(m).count('1'),sum(w for i,w in enumerate(weights) if m>>i&1)) for m in range(1<<len(weights)))))
 profiles += [('superadditive',((0,0,0),(1,1,1),(2,1,1),(3,2,10))),('zero_singletons',((0,0,0),(1,1,0),(2,1,0),(3,2,10)))]
 inputs=[(name,obs,q,T,S) for name,obs in profiles for q,T in itertools.product([1,2,3],[1,2,4,8]) for S in range(max(h for m,c,h in obs),max(h for m,c,h in obs)+T+3)]
 (HERE/'INPUT_MANIFEST.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'conditions':len(inputs),'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_tuples':inputs},indent=2)+'\n')
 results=[];errors=[];hypothesis_gaps=[];formula_gaps=[]
 with (HERE/'ROWS.jsonl').open('x') as out:
  for name,obs,q,T,S in inputs:
   x=study(obs,q,T,S);x['profile']=name;results.append(x);out.write(json.dumps(x)+'\n')
   if not all(x[k] for k in ['root_direct_only_frontier_equal','scalar_informed_equal','min_comparator_equal']):errors.append(x)
   if not x['old_loss_upper_bound_claim']:hypothesis_gaps.append({k:v for k,v in x.items() if k!='vectors'})
   if name=='(1,)':
    W=1
    if q==1:formula=min(S-min(S,T),T+W-min(S,T+W))
    elif T<S<T+W:formula=min(S-T,T+W-min(S,2*T),q*T+W-S)
    else:formula=None
    if formula is not None and formula!=x['loss']:formula_gaps.append({'formula':formula,'result':x})
 monotonic=[]
 for name,obs in profiles:
  for q,T in itertools.product([1,2,3],[1,2,4,8]):
   group=[x for x in results if x['profile']==name and x['q']==q and x['T']==T]
   for a,b in zip(group,group[1:]):
    if a['loss']>b['loss']:monotonic.append({'profile':name,'q':q,'T':T,'S_pair':[a['S'],b['S']],'loss_pair':[a['loss'],b['loss']]})
 # A separately disclosed analytic all-or-nothing native-accounting fixture,
 # fixed before running in PLAN and described in the report.
 fixture=study(((0,0,0),(1,1,10)),2,2,11)
 fixture['formula']=min(11-2,2+10-min(11,4),4+10-11)
 assert fixture['loss']==fixture['formula']==3 and fixture['old_loss']==2
 (HERE/'NATIVE_SCALAR_FIXTURE.json').write_text(json.dumps(fixture,indent=2)+'\n')
 rec={'status':'PASS' if not errors and not formula_gaps else 'FAIL','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'conditions':len(results),'main_failures':len(errors),'formula_failures':len(formula_gaps),'old_regret_bound_counterexamples':len(hypothesis_gaps),'nondecreasing_S_counterexamples':len(monotonic),'seconds':time.monotonic()-START,'independence':'full observation-contingent policy vectors versus separate informed scalar recursion; not independent external certification'}
 for name,data in [('ERRORS.json',errors),('FORMULA_GAPS.json',formula_gaps),('OLD_REGRET_BOUND_COUNTEREXAMPLES.json',hypothesis_gaps),('S_MONOTONICITY_COUNTEREXAMPLES.json',monotonic),('RESULT.json',rec)]: (HERE/name).write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(rec));return 0 if rec['status']=='PASS' else 1
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:
  import traceback
  p=HERE/'FAILURE.json';p.write_text(json.dumps({'status':'TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE','exception':repr(e),'traceback':traceback.format_exc(),'seconds':time.monotonic()-START},indent=2)+'\n');raise

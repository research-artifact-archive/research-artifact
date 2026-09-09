from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
from math import lcm
import collections,copy,datetime,hashlib,json,sys,time,traceback
P=Path(__file__).resolve().parent;S=P.parent/'partial_repair_compact_01';sys.path.insert(0,str(S))
import compact01 as geo
from toll01 import known_curve,compile_profile,check_certificate
O=P/'run01';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):
 with (O/n).open('x') as f:json.dump(x,f,indent=2,default=str);f.write('\n')
inputs=[];seen=set()
for group,data,tolls,mus in [('main',(json.loads(s) for s in (S/'run01/outcomes.jsonl').open()),['0','1/2','1','2'],['0','2']),('extra',json.loads((S/'extra01/OUTCOMES.json').read_text()),['0','1/7','5/3'],['0','3/11'])]:
 for x in data:
  key=(tuple(x['weights']),tuple(x['footprints']),x['q'])
  if key in seen:continue
  seen.add(key)
  for toll in tolls:inputs.append(dict(group=group,weights=x['weights'],footprints=x['footprints'],q=x['q'],kappa=toll,mus=mus))
assert len(inputs)==16844
put('INPUTS.json',inputs);put('INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='FIXED_BEFORE_EXECUTION',expected_profiles=16844,expected_ratio_rows=33688,inputs_sha256=sha(O/'INPUTS.json'),source_hashes={n:sha(P/n) for n in ['PLAN.md','toll01.py','check01.py']},old_geometry_source_sha256=sha(S/'compact01.py'),known_geometry_new_cost=True))
rows=curves=[];rows=[];curves=[];failures=[];cache={};known_values=0;example=None
try:
 for index,x in enumerate(inputs,1):
  fw=tuple(map(F,x['weights']));fk=F(x['kappa']);fm=list(map(F,x['mus']));unit=lcm(*(v.denominator for v in fw+(fk,)+tuple(fm)));weights=tuple(int(v*unit) for v in fw);kap=int(fk*unit);key=(weights,tuple(x['footprints']))
  if key not in cache:cache[key]=geo.geometry(*key)
  H,G,_,cover,work=cache[key];q=x['q'];m=len(weights);K=known_curve(G,q,kap)
  @lru_cache(None)
  def kb(left,b):
   return kap+max(min(work[d],kb(left-1,b-k)) if left>1 else work[d] for d,k in cover.items() if k<=b)
  reference=[kb(q,b) for b in range(q*m+1)];good=K==reference;known_values+=len(K)
  if kap==0:good=good and K==[G[b//q] for b in range(q*m+1)]
  curve=dict(index=index,**x,scale_unit=unit,curve=[str(F(v,unit)) for v in K],reference=[str(F(v,unit)) for v in reference],status='PASS' if good else 'FAIL');curves.append(curve)
  if not good:failures.append(curve)
  for baseline in fm:
   mu=int(baseline*unit);result=compile_profile(H,G,mu,kap,q);check_certificate(H,G,mu,kap,q,result)
   @lru_cache(None)
   def blind(left,e):
    t=q-left+1;values=[]
    for d,k in cover.items():
     a=mu+t*kap+work[d];b=mu+reference[e+k];accept=F(a,b) if b else (F(1) if a==0 else float('inf'))
     values.append(min(accept,blind(left-1,e+k)) if left>1 else accept)
    return max(values)
   exact=blind(q,0);simult=(q==1 or (G[1]==G[-1] if kap==0 else kap>=G[-1]));ok=result['ratio']==exact and (exact==1)==simult
   row=dict(index=len(rows)+1,profile_index=index,mu=str(baseline),ratio=str(result['ratio']),reference=str(exact),simultaneous_predicted=simult,reference_states=blind.cache_info().currsize,status='PASS' if ok else 'FAIL',certificate=result);rows.append(row)
   if not ok:failures.append(row)
   if weights==(2,) and kap==1 and mu==0 and q==2:example=(H,G,mu,kap,q,result)
  if time.monotonic()-start>180:raise TimeoutError('180seconds')
 assert len(rows)==33688 and example
 H,G,mu,kap,q,result=example;controls=[]
 muts=[('ratio_downgrade',lambda z:z.update(ratio=F(z['ratio'])-F(1,12))),('ratio_upgrade',lambda z:z.update(ratio=F(z['ratio'])+F(1,12))),('missing_lower_step',lambda z:z['lower_path'].pop()),('wrong_prefix_cost',lambda z:z['lower_path'][1].update(e=0)),('wrong_repeated_call_charge',lambda z:z['lower_path'][-1].update(numerator=1)),('wrong_denominator',lambda z:z['lower_path'][-1].update(denominator=999)),('premature_upper_stop',lambda z:z.update(upper_path=[])),('wrong_known_budget_curve',lambda z:z['known_curve'].__setitem__(0,z['known_curve'][0]+1))]
 for name,mut in muts:
  z=copy.deepcopy(result);mut(z)
  try:check_certificate(H,G,mu,kap,q,z);detected=False
  except (AssertionError,IndexError,TypeError):detected=True
  controls.append(dict(name=name,detected=detected))
 assert len(controls)==8 and all(x['detected'] for x in controls)
 put('CURVES.json',curves);put('OUTCOMES.json',rows);put('CONTROLS.json',controls);put('FAILURES.json',failures)
 put('RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not failures else 'FAIL',profiles=len(curves),known_budget_values=known_values,ratio_rows=len(rows),controls=8,simultaneous_rows=sum(x['simultaneous_predicted'] for x in rows),nonsimultaneous_rows=sum(not x['simultaneous_predicted'] for x in rows),failures=len(failures),seconds=time.monotonic()-start,curves_sha256=sha(O/'CURVES.json'),outcomes_sha256=sha(O/'OUTCOMES.json')))
 print((O/'RECEIPT.json').read_text(),flush=True)
except BaseException as e:
 put('FAILED_CURVES.json',curves);put('FAILED_OUTCOMES.json',rows);put('FAILURE_RECEIPT.json',dict(status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',error=repr(e),traceback=traceback.format_exc(),profiles=len(curves),rows=len(rows),seconds=time.monotonic()-start));raise

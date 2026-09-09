from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import copy,datetime,hashlib,json,sys,time,traceback
P=Path(__file__).resolve().parent;S=P.parent/'partial_repair_compact_01';sys.path.insert(0,str(S))
import compact01 as geometry
import compact02 as competitive
from regret01 import compile_profile,check_certificate
O=P/'run01';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):
 with (O/n).open('x') as f:json.dump(x,f,indent=2,default=str);f.write('\n')
inputs=[];seen=set()
for group,data in [('prior',(json.loads(s) for s in (S/'run01/outcomes.jsonl').open())),('extra',json.loads((S/'extra01/OUTCOMES.json').read_text()))]:
 for x in data:
  key=(tuple(x['weights']),tuple(x['footprints']),x['q'])
  if key in seen:continue
  seen.add(key);inputs.append(dict(group=group,weights=x['weights'],footprints=x['footprints'],q=x['q']))
assert len(inputs)==4220
put('INPUTS.json',inputs);put('INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='FIXED_BEFORE_EXECUTION',inputs_sha256=sha(O/'INPUTS.json'),planned=4220,source_hashes={str(p):sha(p) for p in [P/'PLAN.md',P/'PROOF.md',P/'regret01.py',Path(__file__),S/'compact01.py',S/'compact02.py']},prior_inputs_known=True))
cache={};rows=[];failures=[];example=None
try:
 for i,x in enumerate(inputs):
  weights,_,unit=geometry.scale(x['weights'],0);key=(weights,tuple(x['footprints']))
  if key not in cache:cache[key]=geometry.geometry(*key)
  H,G,_,cover,work=cache[key];q=x['q'];W=sum(weights);result=compile_profile(H,G,q,W);check_certificate(H,G,q,W,result)
  @lru_cache(None)
  def reference(left,e):
   values=[]
   for dirty,k in cover.items():
    accept=work[dirty]-G[(e+k)//q]
    retry=reference(left-1,e+k) if left>1 and dirty else W+1
    values.append(min(accept,retry))
   return max(values)
  @lru_cache(None)
  def policy(left,e,kind):
   values=[]
   for dirty,k in cover.items():
    loss=work[dirty]-G[(e+k)//q]
    accept=loss<=result['delta'] if kind=='optimal' else dirty==0 or left==1
    if accept:values.append(loss)
    else:assert left>1;values.append(policy(left-1,e+k,kind))
   return max(values)
  ref=reference(q,0);observed=policy(q,0,'optimal');retry=policy(q,0,'retryfirst');ok=ref==observed==result['delta'];row=dict(index=i+1,**x,scale_unit=unit,delta=str(F(result['delta'],unit)),reference=str(F(ref,unit)),policy_excess=str(F(observed,unit)),retry_first_excess=str(F(retry,unit)),strict_improvement=observed<retry,reference_states=reference.cache_info().currsize,certificate=result,status='PASS' if ok else 'FAIL');rows.append(row)
  if not ok:failures.append(row)
  if weights==(1,1,1) and tuple(x['footprints'])==(1,2,4) and q==3:example=(H,G,cover,work,result)
  if time.monotonic()-start>180:raise TimeoutError('180seconds')
 assert len(rows)==4220 and example
 H,G,cover,work,delta_result=example;examples=[]
 for mu in [0,1,2]:
  cr=competitive.compile_profile(H,G,mu,3,3)
  for kind in ['retryfirst','competitive','additive']:
   @lru_cache(None)
   def values(left,e):
    ratios=[];excess=[]
    for dirty,k in cover.items():
     num=mu+work[dirty];den=mu+G[(e+k)//3];ratio=F(num,den) if den else (F(1) if num==0 else float('inf'));loss=work[dirty]-G[(e+k)//3]
     accept=(not dirty or left==1) if kind=='retryfirst' else ratio<=cr['ratio'] if kind=='competitive' else loss<=delta_result['delta']
     if accept:ratios.append(ratio);excess.append(loss)
     else:assert left>1;rr,ee=values(left-1,e+k);ratios.append(rr);excess.append(ee)
    return max(ratios),max(excess)
   rr,ee=values(3,0);examples.append(dict(weights=[1,1,1],q=3,mu=mu,policy=kind,worst_ratio=str(rr),worst_additive_excess=ee))
 controls=[]
 mutations=[('delta_downgrade',lambda z:z.update(delta=z['delta']-1)),('delta_upgrade',lambda z:z.update(delta=z['delta']+1)),('missing_lower_step',lambda z:z['lower_path'].pop()),('wrong_prefix_budget',lambda z:z['lower_path'][1].update(e=999)),('wrong_terminal_loss',lambda z:z['lower_path'][0].update(excess=999)),('premature_upper_stop',lambda z:z.update(upper_path=[]))]
 for name,mut in mutations:
  z=copy.deepcopy(delta_result);mut(z)
  try:check_certificate(H,G,3,3,z);detected=False
  except (AssertionError,IndexError,TypeError):detected=True
  controls.append(dict(name=name,detected=detected))
 bad=G[:];bad[1]+=1
 try:check_certificate(H,bad,3,3,delta_result);detected=False
 except AssertionError:detected=True
 controls.append(dict(name='wrong_profile',detected=detected));assert len(controls)==7 and all(x['detected'] for x in controls)
 put('OUTCOMES.json',rows);put('EXAMPLES.json',examples);put('CONTROLS.json',controls);put('FAILURES.json',failures);put('RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not failures else 'FAIL',planned=4220,rows=len(rows),geometry_variants=len(cache),strict_improvement_rows=sum(x['strict_improvement'] for x in rows),controls=7,examples=examples,failures=len(failures),seconds=time.monotonic()-start,outcomes_sha256=sha(O/'OUTCOMES.json')))
 print((O/'RECEIPT.json').read_text(),flush=True)
except BaseException as e:
 put('FAILED_OUTCOMES.json',rows);put('FAILURE_RECEIPT.json',dict(status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',error=repr(e),traceback=traceback.format_exc(),rows=len(rows),seconds=time.monotonic()-start));raise

from pathlib import Path
from fractions import Fraction as F
import copy,datetime,hashlib,json,time,traceback
from compact01 import scale,geometry,compile_profile,check_certificate,policy_accept,ratio
P=Path(__file__).resolve().parent;O=P/'run01';O.mkdir();start=time.monotonic()
source=P.parent/'partial_repair_baseline_01/run01/outcomes.jsonl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,value):
 with (O/name).open('x') as f:json.dump(value,f,indent=2,default=str);f.write('\n')
put('INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='FIXED_BEFORE_EXECUTION',plan_sha256=sha(P/'PLAN.md'),compiler_sha256=sha(P/'compact01.py'),checker_sha256=sha(Path(__file__)),prior_sha256=sha(source),expected_rows=20920,prior_outcomes_known=True))
cache={};failures=[];rows=trees=0;maxdecisions=0;cert_example=None
try:
 with (O/'outcomes.jsonl').open('x') as out:
  for line in source.open():
   x=json.loads(line);weights,mu,unit=scale(x['weights'],x['mu']);key=(weights,tuple(x['footprints']))
   if key not in cache:cache[key]=geometry(*key)
   H,G,witness,cover,work=cache[key];q=x['q'];r=compile_profile(H,G,mu,q,sum(weights));check_certificate(H,G,mu,q,sum(weights),r)
   good=r['ratio']==F(x['optimal_competitive_ratio']);tree_value=None;visited=0
   if len(weights)<=2:
    def tree(e,depth):
     global visited
     values=[]
     for d,k in cover.items():
      visited+=1
      if policy_accept(work[d],k,e,G,mu,q,r['ratio']):
       value=ratio(mu+work[d],mu+G[(e+k)//q]);assert value is not None;values.append(value)
      else:
       assert depth<q,(x,e,depth,d,r)
       values.append(tree(e+k,depth+1))
     return max(values)
    tree_value=tree(0,1);trees+=1;good=good and tree_value==r['ratio']
   row=dict(index=rows,weights=x['weights'],footprints=x['footprints'],q=q,mu=x['mu'],scale_unit=unit,ratio=str(r['ratio']),prior_ratio=x['optimal_competitive_ratio'],history_tree_ratio=None if tree_value is None else str(tree_value),history_tree_decisions=visited,certificate=r,status='PASS' if good else 'FAIL')
   out.write(json.dumps(row,default=str,separators=(',',':'))+'\n');rows+=1;maxdecisions=max(maxdecisions,r['decisions'])
   if not good:failures.append(row)
   if weights==(1,1,1) and mu==2 and q==3 and tuple(x['footprints'])==(1,2,4):cert_example=(H,G,mu,q,sum(weights),r)
   if time.monotonic()-start>170:raise TimeoutError('170second internal cap')
 assert rows==20920 and trees==600 and cert_example is not None
 H,G,mu,q,W,r=cert_example;controls=[]
 mutations=[('ratio_downgrade',lambda z:z.update(ratio=F(7,5))),('ratio_upgrade',lambda z:z.update(ratio=F(8,5))),('missing_lower_step',lambda z:z['lower_path'].pop()),('wrong_minimum_budget',lambda z:z['lower_path'][1].update(e=0)),('wrong_comparator_budget',lambda z:z['lower_path'][-1].update(denominator=999)),('premature_upper_stop',lambda z:z.update(upper_path=[]))]
 for name,mutate in mutations:
  z=copy.deepcopy(r);mutate(z);detected=False
  try:check_certificate(H,G,mu,q,W,z)
  except (AssertionError,IndexError,TypeError):detected=True
  controls.append(dict(name=name,detected=detected))
 # An invalid profile must be rejected independently of a genuine certificate.
 badG=G[:];badG[1]+=1
 try:check_certificate(H,badG,mu,q,W,r);detected=False
 except AssertionError:detected=True
 controls.append(dict(name='wrong_coverage_profile',detected=detected))
 assert all(c['detected'] for c in controls)
 put('EXAMPLE.json',dict(weights=[1,1,1],footprints=[1,2,4],q=q,mu=mu,H=H,G=G,certificate=r));put('FAILURES.json',failures)
 put('RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not failures else 'FAIL',rows=rows,geometry_variants_with_unit_scaling=len(cache),full_history_tree_rows=trees,all_certificates_checked=rows,max_threshold_decisions=maxdecisions,controls=controls,failures=len(failures),seconds=time.monotonic()-start,outcomes_sha256=sha(O/'outcomes.jsonl'),scope='New compact algorithm on previously observed exact-DP inputs. Finite checks do not mechanically prove the greedy dominance argument or establish novelty/native costs.'))
 print((O/'RECEIPT.json').read_text(),flush=True)
except BaseException as e:
 put('FAILURE_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',error=repr(e),traceback=traceback.format_exc(),rows=rows,failures=failures,seconds=time.monotonic()-start));raise

from pathlib import Path
from fractions import Fraction as F
import copy,datetime,hashlib,json,random,time,traceback
import compact01 as old
import compact02 as new
P=Path(__file__).resolve().parent;O=P/'monotone_check01';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):
 with (O/n).open('x') as f:json.dump(x,f,indent=2,default=str);f.write('\n')
source=P/'run01/outcomes.jsonl';extra=P/'extra01/OUTCOMES.json'
put('INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='FIXED_BEFORE_EXECUTION',sources={n:sha(P/n) for n in ['MONOTONE_PLAN.md','MONOTONE_PROOF.md','compact01.py','compact02.py','monotone_check01.py']},old_rows_sha256=sha(source),extra_sha256=sha(extra),expected_rows=21028,threshold_decisions=1600,seed=9100730,known_prior_inputs=True))
rows=0;cache={};failures=[];monotone=0;example=None
try:
 with (O/'OUTCOMES.jsonl').open('x') as out:
  data=(json.loads(s) for s in source.open())
  for group,seq in [('old20920',data),('rational108',json.loads(extra.read_text()))]:
   for x in seq:
    w,mu,unit=old.scale(x['weights'],x['mu']);key=(w,tuple(x['footprints']))
    if key not in cache:cache[key]=old.geometry(*key)
    H,G,_,_,_=cache[key];q=x['q'];r=new.compile_profile(H,G,mu,q,sum(w));old.check_certificate(H,G,mu,q,sum(w),r);new.check_certificate(H,G,mu,q,sum(w),r)
    ok=r=={k:F(v) if k in ['ratio','isolation_lower','isolation_upper'] else v for k,v in x['certificate'].items()}
    mono=new.monotone_profile(H,G);monotone+=mono
    row=dict(index=rows+1,group=group,ratio=str(r['ratio']),prior_ratio=x['ratio'],exact_certificate_equal=ok,monotone_acceleration=mono,status='PASS' if ok else 'FAIL',certificate=r)
    out.write(json.dumps(row,default=str,separators=(',',':'))+'\n');rows+=1
    if not ok:failures.append(row)
    if w==(1,1,1) and mu==2 and q==3 and tuple(x['footprints'])==(1,2,4):example=(H,G,mu,q,sum(w),r)
    if time.monotonic()-start>170:raise TimeoutError('170seconds')
 assert rows==21028 and example
 rng=random.Random(9100730);threshold_rows=[]
 for i in range(100):
  m=rng.randint(1,25);w=[rng.randint(1,100) for _ in range(m)];H,G,_=old.singleton_profile(w);mu=rng.choice([0,1,sum(w)])
  for q in [1,2,3,8]:
   for R in map(F,['1','4/3','2','7/2']):
    a=old.feasible(H,G,mu,q,R);b=new.feasible(H,G,mu,q,R);ok=a==b
    threshold_rows.append(dict(profile=i,m=m,q=q,mu=mu,R=str(R),identical=ok))
    if not ok:failures.append(threshold_rows[-1])
 assert len(threshold_rows)==1600
 H,G,mu,q,W,r=example;controls=[]
 mutations=[('ratio_downgrade',lambda z:z.update(ratio=F(7,5))),('ratio_upgrade',lambda z:z.update(ratio=F(8,5))),('missing_lower_step',lambda z:z['lower_path'].pop()),('wrong_minimum_budget',lambda z:z['lower_path'][1].update(e=0)),('wrong_comparator_budget',lambda z:z['lower_path'][-1].update(denominator=999)),('premature_upper_stop',lambda z:z.update(upper_path=[])),('bad_lower_cost',lambda z:z['lower_path'][0].update(k=0)),('out_of_range_upper_cost',lambda z:z['upper_path'][0].update(k=len(H)))]
 for name,mut in mutations:
  z=copy.deepcopy(r);mut(z);detections=[]
  for checker in [old.check_certificate,new.check_certificate]:
   try:checker(H,G,mu,q,W,z);detected=False
   except (AssertionError,IndexError,TypeError):detected=True
   detections.append(detected)
  controls.append(dict(name=name,both_detected=all(detections)))
 for name,hh,gg in [('wrong_coverage_profile',H,G[:1]+[G[1]+1]+G[2:]),('bad_monotone_endpoint',H[:-1]+[W+1],G[:-1]+[W+1])]:
  detections=[]
  for checker in [old.check_certificate,new.check_certificate]:
   try:checker(hh,gg,mu,q,W,r);detected=False
   except (AssertionError,IndexError,TypeError):detected=True
   detections.append(detected)
  controls.append(dict(name=name,both_detected=all(detections)))
 assert len(controls)==10 and all(x['both_detected'] for x in controls)
 put('THRESHOLDS.json',threshold_rows);put('CONTROLS.json',controls);put('FAILURES.json',failures)
 put('RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not failures else 'FAIL',rows=rows,monotone_rows=monotone,fallback_rows=rows-monotone,threshold_decisions=1600,controls=10,all_certificates_equal=True,failures=len(failures),seconds=time.monotonic()-start,outcomes_sha256=sha(O/'OUTCOMES.jsonl')))
 print((O/'RECEIPT.json').read_text(),flush=True)
except BaseException as e:
 put('FAILURE_RECEIPT.json',dict(status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',error=repr(e),traceback=traceback.format_exc(),rows=rows,seconds=time.monotonic()-start));raise
